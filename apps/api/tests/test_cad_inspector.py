"""Synthetic evidence only. No captured CAD, credentials or private documents."""

from copy import deepcopy
from typing import cast

import pytest
from conftest import Harness
from pydantic import JsonValue
from test_cad_read import BODIES, FEATURES, MASS, PARTS, REF, CadProvider, transport

from forge_api.integrations.onshape.contracts import Operation
from forge_api.integrations.onshape.inspector import (
    MAX_BODIES,
    MAX_FEATURES,
    MAX_PARAMETERS,
    MAX_PARTS,
    inspect,
)
from forge_api.integrations.onshape.models import SectionState, Snapshot
from forge_api.integrations.onshape.normalize import normalize

PATH = "/api/onshape/part-studio/inspector"


def snapshot(**overrides: object) -> Snapshot:
    raw = {
        "features": deepcopy(FEATURES),
        "parts": deepcopy(PARTS),
        "bodies": deepcopy(BODIES),
        "mass": deepcopy(MASS),
        **overrides,
    }
    return Snapshot(
        context=REF,
        sections={name: SectionState(status="success", code="ok") for name in raw},
        documents={
            name: normalize(Operation(name), cast(JsonValue, value))
            for name, value in raw.items()
        },
        captured_at="2026-10-13T12:00:00+00:00",
        consistency="unverified",
    )


def test_order_types_names_parts_and_topology() -> None:
    result = inspect(snapshot(), "a" * 32)
    assert [f.index for f in result.features.items] == [1, 2]
    assert [f.name for f in result.features.items] == ["Sketch 1", "Extrude 1"]
    assert [f.feature_type for f in result.features.items] == ["sketch", "extrude"]
    assert all(f.suppression == "active" for f in result.features.items)
    part = result.parts.items[0]
    assert (
        part.name,
        part.description,
        part.part_number,
        part.body_type,
        part.state,
        part.is_mesh,
        part.mass,
    ) == (
        "Part 1",
        "Synthetic part",
        "TEST",
        "SOLID",
        "IN_PROGRESS",
        False,
        "unverified",
    )
    body = result.bodies.items[0]
    assert (
        body.index,
        body.body_type,
        body.face_count,
        body.edge_count,
        body.vertex_count,
    ) == (1, "SOLID", 1, None, None)
    assert result.source.features.count == 2
    assert result.freshness == "captured_unverified"


@pytest.mark.parametrize(
    "fields,kind,name,suppression",
    [
        (
            {"featureType": "fillet", "suppressed": True},
            "fillet",
            "Example",
            "suppressed",
        ),
        ({"featureType": "chamfer"}, "chamfer", "Example", "unverified"),
        ({"featureType": "futureSecretType"}, "unknown", "Example", "unverified"),
        (
            {"featureType": "extrude", "namespace": "private-feature-studio"},
            "unknown",
            "Example",
            "unverified",
        ),
        (
            {"featureType": "extrude", "name": None},
            "extrude",
            "Unnamed feature 1",
            "unverified",
        ),
        ({"name": "x" * 257}, "unknown", "Unnamed feature 1", "unverified"),
    ],
)
def test_incomplete_features(
    fields: dict[str, object], kind: str, name: str, suppression: str
) -> None:
    data = {
        "features": [{"featureId": "private-id", "name": "Example", **fields}],
        "isComplete": True,
    }
    feature = inspect(snapshot(features=data), "a" * 32).features.items[0]
    assert (feature.feature_type, feature.name, feature.suppression) == (
        kind,
        name,
        suppression,
    )
    assert feature.completeness in ("partial", "unverified")


@pytest.mark.parametrize(
    "raw,kind,state,value",
    [
        (
            {"btType": "BTMParameterBoolean-144", "value": False},
            "boolean",
            "available",
            False,
        ),
        (
            {"btType": "BTMParameterBoolean-144", "value": "false"},
            "boolean",
            "unavailable",
            None,
        ),
        ({"btType": "BTMParameterBoolean-144"}, "boolean", "unavailable", None),
        (
            {"btType": "BTMParameterString-149", "value": "literal <script>"},
            "string",
            "available",
            "literal <script>",
        ),
        ({"btType": "BTMParameterString-149", "value": ""}, "string", "available", ""),
        (
            {"btType": "BTMParameterEnum-145", "value": "BLIND"},
            "enum",
            "available",
            "BLIND",
        ),
        (
            {"btType": "BTMParameterQuantity-147", "expression": "#depth + 2 mm"},
            "expression",
            "available",
            "#depth + 2 mm",
        ),
        (
            {"btType": "BTMParameterQuantity-147", "expression": "9" * 257},
            "expression",
            "omitted",
            None,
        ),
        (
            {"btType": "BTMParameterQuantity-147", "expression": "abc\u202edef"},
            "expression",
            "omitted",
            None,
        ),
        (
            {"btType": "BTMParameterQuantity-147", "expression": "😀" * 100},
            "expression",
            "omitted",
            None,
        ),
        (
            {"btType": "BTMParameterQuantity-147", "expression": {}},
            "expression",
            "unavailable",
            None,
        ),
        (
            {
                "btType": "BTMParameterQueryList-148",
                "queries": [
                    {
                        "queryString": "do not execute",
                        "deterministicIds": ["private-reference"],
                    }
                ],
            },
            "query_count",
            "available",
            1,
        ),
        (
            {"btType": "BTMParameterQueryList-148", "queries": []},
            "query_count",
            "available",
            0,
        ),
        (
            {"btType": "BTMParameterQueryList-148", "queries": ["private-reference"]},
            "query_count",
            "unavailable",
            None,
        ),
        (
            {"btType": "BTMParameterTolerantQuantity-2579", "expression": "secret"},
            "unsupported",
            "unsupported",
            None,
        ),
        (
            {
                "btType": "FutureType",
                "summary": {"kind": "string", "state": "available", "text": "injected"},
            },
            "unsupported",
            "unsupported",
            None,
        ),
    ],
)
def test_parameter_adapters(
    raw: dict[str, object], kind: str, state: str, value: object
) -> None:
    data = {
        "features": [
            {
                "featureId": "private-id",
                "name": "Example",
                "featureType": "extrude",
                "suppressed": False,
                "parameters": [{"parameterId": "endDepth", **raw}],
            }
        ],
        "isComplete": True,
    }
    result = inspect(snapshot(features=data), "a" * 32)
    parameter = result.features.items[0].parameters[0]
    assert (parameter.kind, parameter.state, parameter.label) == (
        kind,
        state,
        "end Depth",
    )
    assert (
        parameter.boolean
        if kind == "boolean"
        else parameter.count
        if kind == "query_count"
        else parameter.text
    ) == value
    assert (result.features.items[0].completeness == "complete") == (
        state == "available"
    )
    for private in ("private-reference", "do not execute", "injected", "FutureType"):
        assert private not in result.model_dump_json()


def test_bounds_omit_whole_values_and_keep_order_and_total() -> None:
    item = {
        "featureId": "private-id",
        "featureType": "extrude",
        "name": "E",
        "suppressed": False,
        "parameters": [
            {
                "parameterId": "option",
                "btType": "BTMParameterBoolean-144",
                "value": True,
            }
        ]
        * (MAX_PARAMETERS + 3),
    }
    result = inspect(
        snapshot(
            features={"features": [item] * (MAX_FEATURES + 1), "isComplete": True},
            parts=PARTS * (MAX_PARTS + 1),
            bodies={"bodies": cast(list[object], BODIES["bodies"]) * (MAX_BODIES + 1)},
        ),
        "a" * 32,
    )
    assert len(result.features.items) == MAX_FEATURES
    assert result.features.omitted_count == 1
    assert result.source.features.count == MAX_FEATURES + 1
    assert result.features.items[-1].index == MAX_FEATURES
    assert result.features.items[0].omitted_parameters == 3
    assert len(result.features.items[0].parameters) == MAX_PARAMETERS
    assert result.parts.omitted_count == result.bodies.omitted_count == 1
    assert (
        result.features.completeness
        == result.parts.completeness
        == result.bodies.completeness
        == "partial"
    )


@pytest.mark.parametrize("complete", [None, False, True])
def test_empty_and_provider_completeness(complete: bool | None) -> None:
    result = inspect(
        snapshot(
            features={"features": [], "isComplete": complete},
            parts=[],
            bodies={"bodies": []},
            mass={"bodies": {}},
        ),
        "a" * 32,
    )
    assert (
        not result.features.items and not result.parts.items and not result.bodies.items
    )
    assert result.source.features.count == (0 if complete else None)
    assert result.features.completeness == (
        "complete" if complete else "partial" if complete is False else "unverified"
    )
    assert result.physical.mass == result.physical.volume == "unavailable"


def test_missing_topology_and_metadata_not_zero() -> None:
    result = inspect(
        snapshot(
            parts=[{"partId": "private-part"}],
            bodies={"bodies": [{"id": "private-body"}]},
        ),
        "a" * 32,
    )
    body = result.bodies.items[0]
    assert body.face_count is body.edge_count is body.vertex_count is None
    assert result.bodies.completeness == result.parts.completeness == "partial"
    assert result.parts.items[0].name == "Unnamed part 1"


@pytest.mark.parametrize(
    "fields,expected",
    [
        ({"hasMass": True, "mass": [1, 0.9, 1.1], "massMissingCount": 0}, "available"),
        ({"hasMass": False, "mass": [0, -1, 1], "massMissingCount": 1}, "unavailable"),
        ({"hasMass": True, "mass": [1, 0.9, 1.1], "massMissingCount": 1}, "partial"),
        ({"hasMass": True}, "unverified"),
        ({}, "unverified"),
    ],
)
def test_physical_evidence_no_units_or_estimates_invented(
    fields: dict[str, object], expected: str
) -> None:
    result = inspect(
        snapshot(mass={"bodies": {"-all-": {**fields, "volume": [2, 1.9, 2.1]}}}),
        "a" * 32,
    )
    assert result.physical.mass == expected
    assert result.physical.volume == "reported"
    assert result.physical.units == "provider_native_unverified"
    assert "nominal" not in result.model_dump_json()


def test_partial_sections_and_mismatch() -> None:
    data = snapshot()
    del data.documents["bodies"]
    data.sections["bodies"] = SectionState(
        status="provider_failure", code="provider_timeout"
    )
    data.consistency = "mismatch"
    result = inspect(data, "a" * 32)
    assert len(result.features.items) == 2 and len(result.parts.items) == 1
    assert result.bodies.items == [] and result.bodies.completeness == "unavailable"
    assert result.source.bodies.code == "provider_timeout"
    assert result.freshness == "stale"


def test_inspector_route_one_acquisition_privacy_and_shared_gate(
    harness: Harness,
) -> None:
    harness.login()
    provider = CadProvider()
    with transport(harness, provider):
        response = harness.client.get(
            PATH, params=REF.model_dump(), headers=harness.headers()
        )
        again = harness.client.get(
            "/api/onshape/part-studio/snapshot",
            params=REF.model_dump(),
            headers=harness.headers(),
        )
    assert response.status_code == 200
    assert response.json()["schema_version"] == "forge-cad-inspector-v1"
    assert response.headers["cache-control"] == "no-store"
    assert len(provider.calls) == 4 and all(r.method == "GET" for r in provider.calls)
    assert again.json()["features"]["code"] == "rate_limited"
    for private in [
        "synthetic-access",
        "synthetic-refresh",
        "server-only",
        "synthetic-part",
        "synthetic-sketch",
        "featureId",
        "btType",
        "customProperties",
        "microversionId",
        "https://",
        REF.documentId,
    ]:
        assert private not in response.text


@pytest.mark.parametrize(
    "failure",
    [
        "signed-out",
        "csrf",
        "origin",
        "extra-path",
        "extra-method",
        "version",
        "duplicate",
    ],
)
def test_inspector_request_boundary(harness: Harness, failure: str) -> None:
    headers: dict[str, str] = {}
    if failure != "signed-out":
        harness.login()
        headers = harness.headers()
    params = list(REF.model_dump().items())
    if failure == "csrf":
        headers.pop("X-CSRF-Token")
    if failure == "origin":
        headers["Origin"] = "https://evil.example"
    if failure == "extra-path":
        params.append(("path", "/private"))
    if failure == "extra-method":
        params.append(("method", "POST"))
    if failure == "version":
        params = [(k, "version" if k == "revisionKind" else v) for k, v in params]
    if failure == "duplicate":
        params.append(("documentId", "f" * 24))
    provider = CadProvider()
    with transport(harness, provider):
        response = harness.client.get(PATH, params=params, headers=headers)
    assert response.status_code in (400, 401, 403, 422)
    assert not provider.calls
    assert "private" not in response.text


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_no_inspector_write_route(harness: Harness, method: str) -> None:
    harness.login()
    assert (
        harness.client.request(
            method, PATH, params=REF.model_dump(), headers=harness.headers()
        ).status_code
        == 405
    )


def test_inspector_provider_error_is_fixed_and_other_sections_survive(
    harness: Harness,
) -> None:
    harness.login()
    provider = CadProvider(statuses={"bodies": 500})
    provider.responses["bodies"] = {
        "error": "https://private.example/sensitive-body",
        "access_token": "private-token",
    }
    with transport(harness, provider):
        result = harness.client.get(
            PATH, params=REF.model_dump(), headers=harness.headers()
        )
    assert result.json()["source"]["bodies"]["code"] == "provider_unavailable"
    assert len(result.json()["features"]["items"]) == 2
    assert "private" not in result.text


def test_invalid_unicode_is_omitted_instead_of_crashing() -> None:
    from forge_api.integrations.onshape.parameters import display_text

    assert display_text("\ud800") is None
    assert display_text("\udfff") is None
    assert display_text("😀" * 64) == "😀" * 64
    assert display_text("😀" * 65) is None


def test_maximum_projection_fits_browser_byte_budget() -> None:
    # Quotation marks need JSON escaping; multibyte text is bounded by UTF-8 bytes.
    text = '"' * 256
    features = [
        {
            "featureId": "synthetic-id",
            "featureType": "extrude",
            "suppressed": False,
            "name": text,
            "parameters": [
                {
                    "parameterId": "aB" * 40,
                    "btType": "BTMParameterString-149",
                    "value": text,
                }
            ]
            * MAX_PARAMETERS,
        }
    ] * MAX_FEATURES
    parts = [
        {
            "partId": "synthetic-part",
            "name": text,
            "description": text,
            "partNumber": text,
            "bodyType": text,
            "state": text,
            "isMesh": False,
        }
    ] * MAX_PARTS
    bodies = {"bodies": [{"id": "synthetic-body", "type": text}] * MAX_BODIES}
    result = inspect(
        snapshot(
            features={"features": features, "isComplete": True},
            parts=parts,
            bodies=bodies,
        ),
        "a" * 32,
    )
    assert len(result.model_dump_json().encode("utf-8")) < 2 * 1024 * 1024
