"""Invented body structure only; no captured private CAD or geometry."""

import json
import logging
from typing import cast

import httpx2 as httpx
import pytest
from conftest import Harness
from pydantic import JsonValue, ValidationError
from test_cad_inspector import PATH, snapshot
from test_cad_read import REF, CadProvider, transport

from forge_api.db.models import OnshapeAuthorization
from forge_api.integrations.onshape.client import (
    MAX_BYTES,
    OnshapeReadClient,
    ReadError,
)
from forge_api.integrations.onshape.contracts import Operation, endpoint
from forge_api.integrations.onshape.dev.body_structure import describe_body
from forge_api.integrations.onshape.inspector import inspect
from forge_api.integrations.onshape.models import Bodies, BodySummary
from forge_api.integrations.onshape.normalize import normalize


@pytest.mark.parametrize("field", ["faces", "edges", "vertices"])
@pytest.mark.parametrize("mode", ["missing", "null", "empty", "present"])
def test_topology_evidence_survives_every_projection(field: str, mode: str) -> None:
    body: dict[str, JsonValue] = {"id": "private-body", "type": "SOLID"}
    if mode != "missing":
        body[field] = (
            None
            if mode == "null"
            else []
            if mode == "empty"
            else [{"id": "private-topology", "geometry": {"x": 12345.678}}] * 6
        )
    raw: JsonValue = {"bodies": [body]}
    parsed = Bodies.model_validate(raw).bodies[0]
    assert getattr(parsed, field) == body.get(field)
    normalized = cast(list[BodySummary], normalize(Operation.BODIES, raw).normalized)[0]
    result = inspect(snapshot(bodies=raw), "a" * 32)
    key = {"faces": "face_count", "edges": "edge_count", "vertices": "vertex_count"}[
        field
    ]
    expected = 6 if mode == "present" else None
    assert getattr(normalized, key) == expected
    assert result.model_dump()["bodies"]["items"][0][key] == expected
    assert result.bodies.completeness == "partial"
    public = result.model_dump_json()
    assert all(marker not in public for marker in ("private-", "geometry", "12345.678"))


@pytest.mark.parametrize("field", ["faces", "edges", "vertices"])
def test_topology_collection_bounds_and_types_remain_strict(field: str) -> None:
    invalid_values: list[JsonValue] = [[{}] * 20001, {}, ["private-id"], 0]
    for invalid in invalid_values:
        with pytest.raises(ValidationError):
            normalize(
                Operation.BODIES, {"bodies": [{"id": "private-body", field: invalid}]}
            )


def test_structure_projection_is_exact_and_preserves_empty_vs_absent() -> None:
    raw: JsonValue = {
        "bodies": [
            {
                "id": "private-body",
                "faces": [{}] * 6,
                "edges": [],
                "unknown-private-key": "private-value",
            }
        ]
    }
    text = describe_body(raw)
    assert text and len(text) <= 512
    assert json.loads(text) == {
        "bodyDetails": {
            "faces": {"present": True, "type": "array", "length": 6},
            "edges": {"present": True, "type": "array", "length": 0},
            "vertices": {"present": False, "type": "missing", "length": None},
        }
    }
    assert "private" not in text
    null_text = describe_body({"bodies": [{"vertices": None}]})
    assert null_text
    assert json.loads(null_text)["bodyDetails"]["vertices"] == {
        "present": True,
        "type": "missing",
        "length": None,
    }


@pytest.mark.parametrize(
    "raw",
    [
        None,
        {},
        {"bodies": []},
        {"bodies": [None]},
        {"bodies": [{"faces": {}}]},
        {"bodies": [{"faces": [{}] * 20001}]},
        {"bodies": [{}] * 2001},
    ],
)
def test_structure_projection_fails_closed(raw: JsonValue) -> None:
    assert describe_body(raw) is None


@pytest.mark.parametrize("environment", ["development", "test", "production"])
def test_body_structure_header_is_dev_only_and_never_logged(
    harness: Harness,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    environment: str,
) -> None:
    harness.login()
    monkeypatch.setattr(harness.runtime.settings, "environment", environment)
    provider = CadProvider()
    provider.responses["bodies"] = {
        "bodies": [
            {
                "id": "private-body",
                "faces": [{"id": "private-face", "geometry": {"x": 98765.432}}] * 6,
                "edges": [],
                "vertices": [],
            }
        ]
    }
    with (
        caplog.at_level(logging.INFO, logger="forge.onshape.read"),
        transport(harness, provider),
    ):
        response = harness.client.get(
            PATH, params=REF.model_dump(), headers=harness.headers()
        )
    assert response.status_code == 200
    body = response.json()["bodies"]["items"][0]
    assert (body["face_count"], body["edge_count"], body["vertex_count"]) == (
        6,
        None,
        None,
    )
    header = response.headers.get("X-Forge-Body-Structure")
    if environment == "development":
        assert header and json.loads(header)["bodyDetails"]["edges"]["length"] == 0
    else:
        assert header is None
    assert "bodyDetails" not in response.text + caplog.text
    assert all(
        marker not in response.text + str(header) + caplog.text
        for marker in ("private-", "geometry", "98765.432")
    )
    assert len(provider.calls) == 4 and all(
        call.method == "GET" for call in provider.calls
    )
    body_request = next(
        call for call in provider.calls if call.url.path.endswith("bodydetails")
    )
    assert dict(body_request.url.params) == {"includeGeometricData": "false"}
    assert endpoint(Operation.BODIES, REF)[1] == {"includeGeometricData": "false"}


def test_body_diagnostic_requires_auth_and_retained_ownership(
    harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(harness.runtime.settings, "environment", "development")
    assert (
        harness.client.get(PATH, params=REF.model_dump()).headers.get(
            "X-Forge-Body-Structure"
        )
        is None
    )
    user = harness.login()
    provider = CadProvider()

    def handle(request: httpx.Request) -> httpx.Response:
        response = provider.handle(request)
        if request.url.path.endswith("massproperties"):
            with harness.runtime.sessions.begin() as db:
                grant = db.get(OnshapeAuthorization, user)
                assert grant
                grant.status = "disconnected"
                grant.encrypted_refresh_token = None
        return response

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        harness.client.app.state.cad_transport = client  # type: ignore[attr-defined]
        response = harness.client.get(
            PATH, params=REF.model_dump(), headers=harness.headers()
        )
    assert response.headers.get("X-Forge-Body-Structure") is None
    assert response.json()["source"]["bodies"]["code"] == "connection_required"


def test_no_body_diagnostic_on_failure_empty_studio_or_later_read() -> None:
    provider = CadProvider()
    with httpx.Client(
        transport=httpx.MockTransport(provider.handle)
    ) as transport_client:
        client = OnshapeReadClient(
            "https://cad.onshape.com/api",
            transport_client,
            body_diagnostic=describe_body,
        )
        client.bodies(REF, "synthetic-token", "a" * 32)
        assert client.body_structure
        provider.responses["bodies"] = {"bodies": [{"id": "private-body", "edges": {}}]}
        with pytest.raises(ReadError, match="invalid_response"):
            client.bodies(REF, "synthetic-token", "a" * 32)
        assert client.body_structure is None
        provider.responses["bodies"] = {"bodies": []}
        client.bodies(REF, "synthetic-token", "a" * 32)
        assert client.body_structure is None


def test_body_diagnostic_does_not_bypass_stream_limit() -> None:
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200,
                content=b" " * (MAX_BYTES + 1),
                headers={"content-type": "application/json"},
            )
        )
    ) as transport_client:
        client = OnshapeReadClient(
            "https://cad.onshape.com/api",
            transport_client,
            body_diagnostic=describe_body,
        )
        with pytest.raises(ReadError, match="response_too_large"):
            client.bodies(REF, "synthetic-token", "a" * 32)
        assert client.body_structure is None
