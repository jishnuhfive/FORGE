"""Bounded replacement bytes are separate from CAD/approval authority.

Synthetic definitions and in-process MockTransport only; real writes stay OFF.
"""

import json
from copy import deepcopy
from typing import Any

import httpx2 as httpx
import pytest
from conftest import Harness
from test_modify_conformance import (
    UnverifiableProvider,
    initial_provider,
    operation_for,
    plan_for,
    rejected_replacement,
)
from test_modify_filter_contracts import ordinary_inventory
from test_modify_plan import OP, PlanProvider, _no_dispatch, approve, discover, target
from test_safe_edit import running

from forge_api.cad_edits import plan_service
from forge_api.cad_edits.domain import EditError, fingerprint
from forge_api.cad_edits.plans import SemanticPlan
from forge_api.core.config import Settings
from forge_api.integrations.onshape.edit_registry import change
from forge_api.integrations.onshape.service import ReadGate
from forge_api.integrations.onshape.write_client import (
    MAX_FEATURE_REPLACEMENT_BYTES,
    MAX_REQUEST_BYTES,
    SafeEditClient,
)

REPLACEMENTS = (
    (2, "RENAME_FEATURE"),
    (3, "RENAME_FEATURE"),
    (2, "SET_EXTRUDE_DEPTH"),
    (3, "SET_FILLET_RADIUS"),
)


def sized_inventory(
    position: int, kind: str, size: int, *, unicode: bool = False
) -> dict[str, Any]:
    data = ordinary_inventory()
    feature = data["features"][position - 1]
    feature["syntheticMetadata"] = ""
    op = OP.validate_python(operation_for(kind, target(position).handle))
    updated, _ = change(data["features"], target(position), op)
    expected = {
        "sourceMicroversion": data["sourceMicroversion"],
        "rejectMicroversionSkew": True,
        "serializationVersion": data["serializationVersion"],
        "libraryVersion": data["libraryVersion"],
        "btType": "BTFeatureDefinitionCall-1406",
        "feature": updated,
    }
    padding = size - len(json.dumps(expected, allow_nan=False).encode())
    assert padding >= 0
    feature["syntheticMetadata"] = (
        "é" * (padding // 6) + "x" * (padding % 6) if unicode else "x" * padding
    )
    return data


@pytest.mark.parametrize("position,kind", REPLACEMENTS)
@pytest.mark.parametrize("size", [8192, 8193, 14771, 32768, 32769])
def test_replacement_budget_is_exact_and_requires_cancel_then_single_approval(
    harness: Harness, position: int, kind: str, size: int
) -> None:
    provider = PlanProvider()
    provider.data = sized_inventory(position, kind, size)
    original = deepcopy(provider.data)
    with running(harness, provider):
        req, preview = plan_for(harness, position, kind)
        assert provider.writes == 0 and provider.data == original
        assert (
            plan_service.cancel(req, harness.runtime, preview.proposal_id).state
            == "cancelled"
        )
        _no_dispatch(harness, provider)
        req, preview = plan_for(harness, position, kind)
        result = approve(harness, req, preview)
        if size > MAX_FEATURE_REPLACEMENT_BYTES:
            assert result.state == "write_failed" and result.operations == (
                "write_failed",
            )
            _no_dispatch(harness, provider)
            assert provider.data == original
            return
        assert result.state == "verified_success" and result.operations == (
            "verified_success",
        )
        posts = [c for c in provider.calls if c.method == "POST"]
        assert provider.writes == len(posts) == 1 and len(posts[0].content) == size
        expected, _ = change(
            original["features"],
            target(position),
            OP.validate_python(operation_for(kind, target(position).handle)),
        )
        assert provider.payloads[0]["feature"] == expected
        assert provider.data["features"][position - 1] == expected
        assert provider.payloads[0]["rejectMicroversionSkew"] is True
        with pytest.raises(EditError, match="proposal_used"):
            approve(harness, req, preview)
        assert provider.writes == 1


@pytest.mark.parametrize("size", [32768, 32769])
def test_bound_counts_serialized_bytes_for_unicode_metadata(
    harness: Harness, size: int
) -> None:
    provider = PlanProvider()
    provider.data = sized_inventory(2, "RENAME_FEATURE", size, unicode=True)
    with running(harness, provider):
        req, preview = plan_for(harness, 2, "RENAME_FEATURE")
        result = approve(harness, req, preview)
    if size == MAX_FEATURE_REPLACEMENT_BYTES:
        assert result.state == "verified_success" and provider.writes == 1
        post = next(c for c in provider.calls if c.method == "POST")
        assert len(post.content) == size
        assert (
            provider.payloads[0]["feature"]["syntheticMetadata"]
            == provider.data["features"][1]["syntheticMetadata"]
        )
    else:
        assert result.state == "write_failed"
        _no_dispatch(harness, provider)


@pytest.mark.parametrize("method", ["GET", "POST", "PATCH"])
@pytest.mark.parametrize("size", [8192, 8193])
def test_ordinary_exchange_keeps_8k_even_with_replacement_looking_fields(
    method: str, size: int
) -> None:
    body: dict[str, object] = {
        "btType": "BTFeatureDefinitionCall-1406",
        "replacement": True,
        "feature": "",
    }
    body["feature"] = "x" * (size - len(json.dumps(body).encode()))
    calls: list[httpx.Request] = []

    def receive(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    with httpx.Client(transport=httpx.MockTransport(receive)) as transport:
        client = SafeEditClient(Settings(_env_file=None), transport, "synthetic-token")
        if size == MAX_REQUEST_BYTES:
            assert client._exchange(method, "/features/featureid/synthetic", body) == {}
            assert len(calls) == 1 and len(calls[0].content) == size
        else:
            with pytest.raises(EditError, match="invalid_request"):
                client._exchange(method, "/features/featureid/synthetic", body)
            assert not calls


@pytest.mark.parametrize("size", [32768, 32769])
def test_private_replacement_transport_has_an_independent_exact_ceiling(
    size: int,
) -> None:
    body: dict[str, object] = {"synthetic": ""}
    body["synthetic"] = "x" * (size - len(json.dumps(body).encode()))
    calls: list[httpx.Request] = []

    def receive(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    with httpx.Client(transport=httpx.MockTransport(receive)) as transport:
        client = SafeEditClient(
            Settings(_env_file=None, forge_cad_writes_enabled=True),
            transport,
            "synthetic-token",
        )
        if size == MAX_FEATURE_REPLACEMENT_BYTES:
            assert client._exchange_replacement("/synthetic", body) == {}
            assert (
                len(calls) == 1
                and len(calls[0].content) == size
                and calls[0].method == "POST"
            )
        else:
            with pytest.raises(EditError, match="invalid_request"):
                client._exchange_replacement("/synthetic", body)
            assert not calls


def test_replacement_transport_cannot_bypass_writes_off() -> None:
    def forbidden(request: httpx.Request) -> httpx.Response:
        raise AssertionError("Writes-OFF replacement reached transport")

    with httpx.Client(transport=httpx.MockTransport(forbidden)) as transport:
        client = SafeEditClient(
            Settings(_env_file=None, forge_cad_writes_enabled=False),
            transport,
            "synthetic-token",
        )
        with pytest.raises(EditError, match="write_disabled"):
            client._exchange_replacement("/synthetic", {"synthetic": "x" * 16384})


def test_final_transport_ceiling_rejects_before_opening_a_stream() -> None:
    def forbidden(request: httpx.Request) -> httpx.Response:
        raise AssertionError("Oversized bytes reached transport")

    with httpx.Client(transport=httpx.MockTransport(forbidden)) as transport:
        client = SafeEditClient(Settings(_env_file=None), transport, "synthetic-token")
        with pytest.raises(EditError, match="invalid_request"):
            client._send_measured(
                "POST", "/synthetic", b"x" * (MAX_FEATURE_REPLACEMENT_BYTES + 1)
            )


@pytest.mark.parametrize("kind", ["SET_SUPPRESSED", "SET_UNSUPPRESSED"])
def test_suppression_keeps_attribute_only_payload_despite_large_definition(
    harness: Harness, kind: str
) -> None:
    provider = initial_provider(kind)
    provider.data["features"][-1]["syntheticMetadata"] = "x" * 65536
    before = fingerprint(provider.data["features"][-1]["parameters"])
    with running(harness, provider):
        req, preview = plan_for(harness, 3, kind)
        assert approve(harness, req, preview).state == "verified_success"
    post = next(c for c in provider.calls if c.method == "POST")
    assert post.url.path.endswith("/features/updates")
    assert len(post.content) < MAX_REQUEST_BYTES
    assert provider.payloads[0]["features"] == [
        {
            "btType": "BTMFeature-134",
            "featureId": target().feature_id,
            "suppressed": kind == "SET_SUPPRESSED",
        }
    ]
    assert fingerprint(provider.data["features"][-1]["parameters"]) == before


@pytest.mark.parametrize("position", [2, 3])
def test_larger_budget_cannot_accept_an_unproven_dormant_query_role(
    harness: Harness, position: int
) -> None:
    provider = PlanProvider()
    provider.data = sized_inventory(position, "RENAME_FEATURE", 16384)
    key = "surfaceEntities" if position == 2 else "side1Face"
    param = next(
        p
        for p in provider.data["features"][position - 1]["parameters"]
        if p["parameterId"] == key
    )
    param["filter"] = {"btType": "BTQueryFilter-183"}
    rejected_replacement(harness, provider, position)


@pytest.mark.parametrize("position,kind", REPLACEMENTS)
def test_large_payload_staleness_still_rejects_before_dispatch(
    harness: Harness, position: int, kind: str
) -> None:
    provider = PlanProvider()
    provider.data = sized_inventory(position, kind, 16384)
    with running(harness, provider):
        req, preview = plan_for(harness, position, kind)
        provider.data["features"][position - 1]["syntheticMetadata"] += "stale"
        assert approve(harness, req, preview).state == "rejected_stale"
        _no_dispatch(harness, provider)


@pytest.mark.parametrize(
    "fault", ["ack_missing_revision", "post_read_missing", "post_read_unrelated_change"]
)
def test_large_payload_uncertainty_does_not_retry_or_execute_suffix(
    harness: Harness, fault: str
) -> None:
    provider = UnverifiableProvider("RENAME_FEATURE", fault)
    provider.data = sized_inventory(2, "RENAME_FEATURE", 16384)
    with running(harness, provider):
        req, catalog = discover(harness)
        first = next(t for t in catalog.targets if t.position == 2)
        second = next(t for t in catalog.targets if t.position == 3)
        req.app.state.cad_gate = ReadGate()
        preview = plan_service.prepare(
            req,
            harness.runtime,
            SemanticPlan.model_validate_json(
                json.dumps(
                    {
                        "target_catalog": catalog.target_catalog,
                        "operations": [
                            operation_for("RENAME_FEATURE", first.handle),
                            operation_for("RENAME_FEATURE", second.handle),
                        ],
                    }
                )
            ),
        )
        result = approve(harness, req, preview)
        assert result.state == "execution_uncertain"
        assert result.operations == ("execution_uncertain", "skipped")
        assert provider.writes == 1
        assert plan_service.status(req, harness.runtime, preview.proposal_id) == result
        with pytest.raises(EditError, match="proposal_used"):
            approve(harness, req, preview)
        with pytest.raises(EditError, match="workspace_fenced"):
            discover(harness)
        assert provider.writes == 1
