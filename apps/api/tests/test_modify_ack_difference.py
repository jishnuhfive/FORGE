"""Mock acknowledgement differences only; never a real CAD/incident replay."""

import logging
from contextlib import suppress
from copy import deepcopy
from typing import Any

import httpx2 as httpx
import pytest
from conftest import Harness
from sqlalchemy import select
from test_modify_current_query_contracts import current_inventory
from test_modify_plan import PlanProvider, approve, prepare
from test_modify_semantic_nodes import nodes, operation
from test_safe_edit import running

from forge_api.cad_edits import plan_diagnostics, plan_service
from forge_api.cad_edits.domain import EditError, fingerprint
from forge_api.db.models import WriteFence
from forge_api.integrations.onshape.dev import ack_difference as diagnostic
from forge_api.integrations.onshape.semantic_inventory import semantic_feature

SECRET = "PRIVATE-DO-NOT-EMIT"
CASES = (
    ("feature_name", "feature_name_changed"),
    ("feature_namespace", "feature_namespace_changed"),
    ("feature_missing", "feature_field_presence_changed"),
    ("feature_unknown", "feature_unknown_fields_changed"),
    ("suppression_null", "suppression_shape_changed"),
    ("suppression_type", "suppression_type_changed"),
    ("suppression_unknown", "suppression_unknown_fields_changed"),
    ("parameter_missing", "parameter_count_changed"),
    ("parameter_duplicate", "parameters_malformed"),
    ("parameter_order", "parameter_order_or_identity_changed"),
    ("parameter_type", "parameter_type_changed"),
    ("parameter_unknown", "parameter_unknown_fields_changed"),
    ("quantity_expression", "quantity_expression_changed"),
    ("quantity_cache", "quantity_cached_value_changed"),
    ("quantity_units", "quantity_units_changed"),
    ("quantity_integer", "quantity_integer_flag_changed"),
    ("parameter_name", "parameter_name_metadata_changed"),
    ("parameter_value_string", "parameter_value_string_changed"),
    ("parameter_library", "parameter_library_relation_changed"),
    ("parameter_import", "parameter_import_marker_changed"),
    ("enum_value", "enum_value_changed"),
    ("boolean_value", "boolean_value_changed"),
    ("query_string", "query_string_changed"),
    ("query_ids", "query_deterministic_ids_changed"),
    ("query_identity", "query_sketch_identity_changed"),
    ("query_filter", "query_filter_changed"),
    ("query_unknown", "query_unknown_fields_changed"),
    ("query_missing", "query_field_presence_changed"),
    ("query_count", "query_count_changed"),
    ("profile_missing_nodes", "parameter_profile_changed"),
    ("feature_bad_node", "feature_node_invalid"),
    ("parameter_bad_node", "parameter_node_invalid"),
    ("query_bad_node", "query_node_invalid"),
    ("suppression_bad_node", "suppression_node_invalid"),
)


def mutate(feature: dict[str, Any], mode: str) -> None:
    parameters = feature["parameters"]
    by_id = {p["parameterId"]: p for p in parameters}
    depth, entities = by_id["depth"], by_id["entities"]
    query = entities["queries"][0]
    if mode == "feature_name":
        feature["name"] = SECRET
    elif mode == "feature_namespace":
        feature["namespace"] = SECRET
    elif mode == "feature_missing":
        feature.pop("namespace")
    elif mode == "feature_unknown":
        feature[SECRET] = {SECRET: SECRET}
    elif mode == "suppression_null":
        feature["suppressionState"] = None
    elif mode == "suppression_type":
        feature["suppressionState"]["btType"] = SECRET
    elif mode == "suppression_unknown":
        feature["suppressionState"][SECRET] = SECRET
    elif mode == "parameter_missing":
        parameters.pop()
    elif mode == "parameter_duplicate":
        parameters.append(deepcopy(parameters[0]))
    elif mode == "parameter_order":
        parameters.reverse()
    elif mode == "parameter_type":
        depth["btType"] = SECRET
    elif mode == "parameter_unknown":
        depth[SECRET] = {SECRET: SECRET}
    elif mode == "quantity_expression":
        depth["expression"] = SECRET
    elif mode == "quantity_cache":
        depth["value"] = 1
    elif mode == "quantity_units":
        depth["units"] = SECRET
    elif mode == "quantity_integer":
        depth["isInteger"] = True
    elif mode == "parameter_name":
        depth["parameterName"] = SECRET
    elif mode == "parameter_value_string":
        depth["valueString"] = SECRET
    elif mode == "parameter_library":
        depth["libraryRelationType"] = SECRET
    elif mode == "parameter_import":
        depth["importMicroversion"] = SECRET
    elif mode == "enum_value":
        by_id["endBound"]["value"] = SECRET
    elif mode == "boolean_value":
        by_id["hasDraft"]["value"] = True
    elif mode == "query_string":
        query["queryString"] = SECRET
    elif mode == "query_ids":
        query["deterministicIds"] = [SECRET]
    elif mode == "query_identity":
        query["featureId"] = SECRET
    elif mode == "query_filter":
        entities["filter"][SECRET] = {SECRET: SECRET}
    elif mode == "query_unknown":
        query[SECRET] = SECRET
    elif mode == "query_missing":
        query.pop("queryString")
    elif mode == "query_count":
        entities["queries"].append(deepcopy(query))
    elif mode == "profile_missing_nodes":
        for p in parameters:
            p.pop("nodeId", None)
    elif mode == "feature_bad_node":
        feature["nodeId"] = None
    elif mode == "parameter_bad_node":
        depth["nodeId"] = SECRET * 30
    elif mode == "query_bad_node":
        query["nodeId"] = 1
    elif mode == "suppression_bad_node":
        feature["suppressionState"]["nodeId"] = {}
    else:
        raise AssertionError("unknown synthetic mode")


def expected_feature() -> Any:
    data = current_inventory()
    nodes(data, "expected")
    _, after = operation(data)
    return after["features"][1]


@pytest.mark.parametrize("mode,category", CASES)
def test_each_acknowledgement_difference_is_fixed_private_and_still_rejected(
    mode: str,
    category: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    expected = expected_feature()
    returned = deepcopy(expected)
    mutate(returned, mode)
    preserved = deepcopy((expected, returned))
    categories = diagnostic.ack_differences(expected, returned)
    assert category in categories
    assert categories == tuple(c for c in diagnostic.ORDER if c in categories)
    # Projection rejection and unequal fingerprints both remain closed failures.
    with suppress(EditError):
        assert fingerprint(semantic_feature(expected)) != fingerprint(
            semantic_feature(returned)
        )
    diagnostic.emit_ack_difference(True, expected, returned)
    message = caplog.records[-1].getMessage()
    assert message.startswith("a2_ack_difference categories=")
    assert SECRET not in message
    assert (expected, returned) == preserved


@pytest.mark.parametrize("slot", ["feature", "parameter", "query", "suppression"])
def test_already_proven_valid_node_regeneration_has_no_semantic_diagnostic(
    slot: str,
) -> None:
    expected = expected_feature()
    data = current_inventory()
    data["features"][1] = deepcopy(expected)
    nodes(data, "regenerated", slot)
    returned = data["features"][1]
    assert semantic_feature(expected) == semantic_feature(returned)
    assert diagnostic.ack_differences(expected, returned) == ()


def test_multiple_classes_are_complete_deduplicated_deterministic() -> None:
    expected = expected_feature()
    returned = deepcopy(expected)
    for mode in ("quantity_cache", "quantity_units", "query_string", "feature_unknown"):
        mutate(returned, mode)
    codes = diagnostic.ack_differences(expected, returned)
    for code in (
        "quantity_cached_value_changed",
        "quantity_units_changed",
        "query_string_changed",
        "feature_unknown_fields_changed",
        "parameter_profile_changed",
    ):
        assert code in codes
    assert codes == diagnostic.ack_differences(
        expected, dict(reversed(list(returned.items())))
    )


@pytest.mark.parametrize("development", [True, False])
@pytest.mark.parametrize(
    "mode",
    [
        "quantity_cache",
        "profile_missing_nodes",
        "feature_unknown",
        "parameter_bad_node",
    ],
)
def test_failed_ack_preserves_uncertainty_fence_no_retry_and_no_post_read(
    harness: Harness,
    caplog: pytest.LogCaptureFixture,
    development: bool,
    mode: str,
) -> None:
    class Provider(PlanProvider):
        def handle(self, request: httpx.Request) -> httpx.Response:
            response = super().handle(request)
            if request.method == "POST":
                data = response.json()
                mutate(data["feature"], mode)
                return httpx.Response(200, json=data)
            return response

    provider = Provider()
    provider.data = current_inventory()
    nodes(provider.data, "synthetic")
    with running(harness, provider):
        req, preview = prepare(harness, ("SET_EXTRUDE_DEPTH",))
        harness.runtime.settings.environment = "development" if development else "test"
        with caplog.at_level(logging.WARNING, logger=plan_diagnostics.logger.name):
            result = approve(harness, req, preview)
        assert result.state == "execution_uncertain"
        assert result.operations == ("execution_uncertain",)
        assert provider.writes == 1 and provider.calls[-1].method == "POST"
        with harness.runtime.sessions() as db:
            assert db.scalar(select(WriteFence)) is not None
        messages = [
            r.getMessage()
            for r in caplog.records
            if r.name == plan_diagnostics.logger.name
        ]
        assert any(m.startswith("a2_ack_difference ") for m in messages) == development
        assert not any("a2_verify" in m for m in messages)
        assert SECRET not in repr(messages)
        assert plan_service.status(req, harness.runtime, preview.proposal_id) == result
        assert provider.writes == 1


def test_production_does_not_inspect_and_classifier_failure_never_leaks(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def fail(*args: Any) -> Any:
        raise RuntimeError(SECRET)

    monkeypatch.setattr(diagnostic, "ack_differences", fail)
    diagnostic.emit_ack_difference(False, {}, {})
    assert not caplog.records
    diagnostic.emit_ack_difference(True, {}, {})
    assert caplog.records[-1].getMessage() == (
        "a2_ack_difference categories=diagnostic_unavailable "
        "returned_schema=unsupported_profile expected_schema=unsupported_profile"
    )
    assert SECRET not in caplog.text


@pytest.mark.parametrize("slot", ["parameters", "queries"])
def test_uninspected_oversized_structure_is_explicit_and_bounded(slot: str) -> None:
    expected = expected_feature()
    actual = deepcopy(expected)
    if slot == "parameters":
        actual["parameters"] = [{}] * (diagnostic._MAX_PARAMETERS + 1)
    else:
        entities = next(
            p for p in actual["parameters"] if p["parameterId"] == "entities"
        )
        entities["queries"] = [{}] * (diagnostic._MAX_QUERIES + 1)
    assert "diagnostic_structure_limit" in diagnostic.ack_differences(expected, actual)


@pytest.mark.parametrize("changed", [False, True])
def test_fillet_profile_remains_closed_and_valid_nodes_remain_accepted(
    changed: bool,
) -> None:
    data = current_inventory()
    nodes(data, "before")
    expected = deepcopy(data["features"][2])
    nodes(data, "after")
    returned = data["features"][2]
    if changed:
        radius = next(p for p in returned["parameters"] if p["parameterId"] == "radius")
        radius["value"] = 1
        assert "quantity_cached_value_changed" in diagnostic.ack_differences(
            expected, returned
        )
        assert diagnostic.schema_reason(returned) == "wrong_quantity_value"
    else:
        assert diagnostic.ack_differences(expected, returned) == ()
        assert diagnostic.schema_reason(returned) == "none"
