"""Closed acknowledgement query-ID context, never evidence for normalization."""

from copy import deepcopy
from typing import Any

import httpx2 as httpx
import pytest
from conftest import Harness
from sqlalchemy import select
from test_modify_ack_difference import expected_feature
from test_modify_current_query_contracts import current_inventory
from test_modify_plan import PlanProvider, approve, prepare
from test_modify_semantic_nodes import nodes, operation, projection
from test_modify_ui_conformance import param
from test_safe_edit import M1, running

from forge_api.cad_edits.domain import EditError, fingerprint
from forge_api.db.models import WriteFence
from forge_api.integrations.onshape.dev import ack_difference as diagnostic
from forge_api.integrations.onshape.modify_evidence import verify_operation
from forge_api.integrations.onshape.semantic_inventory import semantic_feature

PRIVATE = "PRIVATE-QUERY-ID-DO-NOT-EMIT"


def query(feature: Any) -> Any:
    return next(p for p in feature["parameters"] if p["parameterId"] == "entities")[
        "queries"
    ][0]


def pair(kind: str = "individual") -> tuple[Any, Any]:
    expected = expected_feature()
    if kind == "region":
        query(expected).update(
            btType="BTMIndividualSketchRegionQuery-140",
            featureId=PRIVATE,
            filterInnerLoops=True,
        )
    elif kind == "fillet":
        expected = current_inventory()["features"][2]
    query(expected)["deterministicIds"] = [PRIVATE + "-before"]
    returned = deepcopy(expected)
    query(returned)["deterministicIds"] = [PRIVATE + "-after"]
    return expected, returned


@pytest.mark.parametrize(
    "kind,label",
    [
        ("individual", "extrude_entities.individual_query"),
        ("region", "extrude_entities.sketch_region_query"),
        ("fillet", "fillet_entities.individual_query"),
    ],
)
def test_valid_role_and_type_are_closed_without_claiming_equivalence(
    kind: str, label: str, caplog: pytest.LogCaptureFixture
) -> None:
    expected, returned = pair(kind)
    original = deepcopy((expected, returned))
    assert (
        diagnostic.schema_reason(expected)
        == diagnostic.schema_reason(returned)
        == "none"
    )
    context = diagnostic.query_id_context(expected, returned)
    assert context == (
        label + ".expected_ids_nonempty.returned_ids_nonempty"
        ".expected_string_nonempty.returned_string_nonempty"
        ".ids_change_values_or_order.remaining_query_exact.filter_exact"
    )
    assert fingerprint(semantic_feature(expected)) != fingerprint(
        semantic_feature(returned)
    )
    diagnostic.emit_ack_difference(True, expected, returned)
    assert caplog.records[-2].getMessage() == "a2_ack_query_ids context=" + context
    assert caplog.records[-1].getMessage().startswith("a2_ack_difference ")
    assert PRIVATE not in caplog.text
    assert (expected, returned) == original


@pytest.mark.parametrize("before", ["absent", "empty", "nonempty"])
@pytest.mark.parametrize("after", ["absent", "empty", "nonempty"])
def test_id_presence_empty_and_nonempty_states(before: str, after: str) -> None:
    expected, returned = pair()
    for feature, state in ((expected, before), (returned, after)):
        if state == "absent":
            query(feature).pop("deterministicIds")
        elif state == "empty":
            query(feature)["deterministicIds"] = []
    context = diagnostic.query_id_context(expected, returned)
    assert ".expected_ids_" + before + ".returned_ids_" + after in context
    assert PRIVATE not in context
    assert (
        fingerprint(semantic_feature(expected))
        == fingerprint(semantic_feature(returned))
    ) == (before == after and before != "nonempty")


@pytest.mark.parametrize("state", ["absent", "blank", "nonempty"])
def test_string_identity_states_are_closed(state: str) -> None:
    expected, returned = pair()
    for feature in (expected, returned):
        if state == "absent":
            query(feature).pop("queryString")
        elif state == "blank":
            query(feature)["queryString"] = " "
    context = diagnostic.query_id_context(expected, returned)
    assert ".expected_string_" + state + ".returned_string_" + state in context
    assert PRIVATE not in context


@pytest.mark.parametrize(
    "bad", [None, 1, {}, "private", [None], [1], [""], ["x" * 257]]
)
def test_malformed_ids_fail_closed_without_echo(bad: Any) -> None:
    expected, returned = pair()
    query(returned)["deterministicIds"] = bad
    assert (
        diagnostic.query_id_context(expected, returned)
        == "unvalidated_or_unsupported_location"
    )
    assert diagnostic.schema_reason(returned) != "none"
    with pytest.raises(EditError):
        from forge_api.integrations.onshape.edit_registry import quantity_parameter

        quantity_parameter(returned, "SET_EXTRUDE_DEPTH")
    assert fingerprint(semantic_feature(expected)) != fingerprint(
        semantic_feature(returned)
    )


@pytest.mark.parametrize(
    "change",
    [
        "string",
        "feature",
        "inner_loops",
        "filter",
        "unknown",
        "count",
        "order",
        "type",
        "dormant",
        "nested_ids",
        "profile",
    ],
)
def test_meaningful_or_unknown_changes_remain_exact(change: str) -> None:
    expected, returned = pair("region")
    # Keep IDs identical to isolate the unrelated change.
    query(returned)["deterministicIds"] = deepcopy(query(expected)["deterministicIds"])
    entity = next(p for p in returned["parameters"] if p["parameterId"] == "entities")
    if change == "string":
        query(returned)["queryString"] = PRIVATE
    elif change == "feature":
        query(returned)["featureId"] = PRIVATE + "-other"
    elif change == "inner_loops":
        query(returned)["filterInnerLoops"] = False
    elif change == "filter":
        entity["filter"][PRIVATE] = PRIVATE
    elif change == "unknown":
        query(returned)[PRIVATE] = PRIVATE
    elif change == "count":
        entity["queries"].append(deepcopy(query(returned)))
    elif change == "order":
        # Unproven multi-query locations remain raw exact, including order.
        for feature in (expected, returned):
            p = next(p for p in feature["parameters"] if p["parameterId"] == "entities")
            other = deepcopy(p["queries"][0])
            other["deterministicIds"] = [PRIVATE + "-different-selection"]
            p["queries"].append(other)
        entity["queries"].reverse()
    elif change == "type":
        query(returned)["btType"] = "BTMIndividualQuery-138"
    elif change == "dormant":
        other = next(
            p for p in returned["parameters"] if p["parameterId"] == "booleanScope"
        )
        other["queries"] = [deepcopy(query(returned))]
    elif change == "nested_ids":
        query(returned)[PRIVATE] = {"deterministicIds": [PRIVATE]}
    else:
        returned["parameters"].append(deepcopy(returned["parameters"][0]))
    assert fingerprint(semantic_feature(expected)) != fingerprint(
        semantic_feature(returned)
    )
    assert PRIVATE not in diagnostic.query_id_context(expected, returned)


@pytest.mark.parametrize("stage", ["ack", "post", "unchanged"])
@pytest.mark.parametrize("development", [False, True])
def test_raw_payload_preserved_and_ack_post_read_have_independent_authority(
    harness: Harness, caplog: pytest.LogCaptureFixture, stage: str, development: bool
) -> None:
    class Provider(PlanProvider):
        def handle(self, request: httpx.Request) -> httpx.Response:
            response = super().handle(request)
            if request.method == "POST" and stage != "unchanged":
                if stage == "ack":
                    data = response.json()
                    query(data["feature"])["deterministicIds"] = [PRIVATE + "-returned"]
                    return httpx.Response(200, json=data)
                query(self.data["features"][1])["deterministicIds"] = [
                    PRIVATE + "-post"
                ]
            return response

    provider = Provider()
    provider.data = current_inventory()
    nodes(provider.data, "original")
    param(provider.data, 2, "entities")["queries"][0]["deterministicIds"] = [PRIVATE]
    with running(harness, provider):
        req, preview = prepare(harness, ("SET_EXTRUDE_DEPTH",))
        harness.runtime.settings.environment = "development" if development else "test"
        result = approve(harness, req, preview)
        assert result.state == (
            "verified_success" if stage == "unchanged" else "execution_uncertain"
        )
        assert provider.writes == 1
        assert query(provider.payloads[0]["feature"])["deterministicIds"] == [PRIVATE]
        assert (
            query(provider.payloads[0]["feature"])["queryString"]
            == "synthetic-profile-query"
        )
        with harness.runtime.sessions() as db:
            assert (db.scalar(select(WriteFence)) is not None) == (stage != "unchanged")
        if stage == "ack":
            assert provider.calls[-1].method == "POST"
            assert not any(
                "a2_verify" in record.getMessage() for record in caplog.records
            )
        messages = [record.getMessage() for record in caplog.records]
        assert any(m.startswith("a2_ack_query_ids ") for m in messages) == (
            development and stage == "ack"
        )
        assert PRIVATE not in str(messages)


def test_fresh_exact_verification_rejects_id_only_selection_change() -> None:
    data = current_inventory()
    param(data, 2, "entities")["queries"][0]["deterministicIds"] = [PRIVATE]
    op, changed = operation(data)
    query(changed["features"][1])["deterministicIds"] = [
        PRIVATE + "-different-selection"
    ]
    with pytest.raises(EditError, match="verification_failed"):
        verify_operation(projection(data), projection(changed, M1), op, M1)


@pytest.mark.parametrize("development", [False, True])
def test_classifier_failure_is_private_and_cannot_affect_rejection(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, development: bool
) -> None:
    def fail(*args: Any) -> Any:
        raise RuntimeError(PRIVATE)

    monkeypatch.setattr(diagnostic, "query_id_context", fail)
    expected, returned = pair()
    diagnostic.emit_ack_difference(development, expected, returned)
    assert PRIVATE not in caplog.text
    assert (
        any(
            m.getMessage() == "a2_ack_query_ids context=diagnostic_unavailable"
            for m in caplog.records
        )
        == development
    )
    if development:
        assert (
            "categories=query_deterministic_ids_changed"
            in caplog.records[-1].getMessage()
        )
        assert (
            "returned_schema=none expected_schema=none"
            in caplog.records[-1].getMessage()
        )
    assert fingerprint(semantic_feature(expected)) != fingerprint(
        semantic_feature(returned)
    )
    assert bool(caplog.records) == development
