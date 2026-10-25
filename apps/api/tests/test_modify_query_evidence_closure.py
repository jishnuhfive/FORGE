"""Official Boolean schemas + synthetic depth stress; no guessed live topology.

Verified before implementation: Onshape OpenAPI 1.222.91980-dcee49ea4d64;
onshape-public/go-client@386ba6fdf60a7de469253857e227064c7df33273 models
BTAllowMeshGeometryFilter1026 and BTMateConnectorFilter163. Exact source URLs /
OpenAPI SHA-256 and human evidence are recorded in the Phase 16 document.
"""

import json
import logging
from collections.abc import Callable
from copy import deepcopy
from typing import Any

import httpx2 as httpx
import pytest
from conftest import Harness
from pydantic import JsonValue, ValidationError
from sqlalchemy import func, select
from test_cad_read import REF, CadProvider, set_scope
from test_modify_query_role_inventory import all_role_inventory, both
from test_modify_ui_conformance import param, replacement_rejects
from test_safe_edit import Provider

from forge_api.cad_edits.domain import fingerprint
from forge_api.db.models import WriteFence, WriteRecord
from forge_api.integrations.onshape.current_ui_filters import (
    matches_extrude_entities_filter,
    matches_fillet_entities_filter,
)
from forge_api.integrations.onshape.dev.query_roles import (
    query_role_inventory,
)
from forge_api.integrations.onshape.dev.standard_shape_failure import diagnose_ui_shape
from forge_api.integrations.onshape.query_filter_evidence import (
    MAX_DEPTH,
    MAX_DIAGNOSTIC_DEPTH,
    MAX_NODES,
    DiagnosticQueryFilterSummary,
    QueryFilterSummary,
    diagnostic_filter_summary,
    leaf_states_text,
    unproven_filter_summary,
)
from forge_api.integrations.onshape.standard_shape_contract import ShapeCategory

HOSTILE = "private-provider-value\noutcome=exact_match"
MISSING = object()
MESH = "BTAllowMeshGeometryFilter-1026"
MATE = "BTMateConnectorFilter-163"
# Independent schema-backed expectations, never derived from production rules.
FIELDS = [
    (MESH, "allowsMeshGeometry", "allow_mesh_geometry"),
    (MATE, "allowImplicitMateConnector", "allow_implicit_mate_connector"),
    (
        MATE,
        "isMateConnectorInferenceEnabledByDefault",
        "mate_connector_inference_default",
    ),
    (MATE, "requiresOccurrence", "requires_occurrence"),
]
STATES = [
    (True, "true"),
    (False, "false"),
    (MISSING, "missing"),
    (None, "null"),
    (0, "wrong_type"),
    (1, "wrong_type"),
    ("true", "wrong_type"),
    ([], "wrong_type"),
    ({HOSTILE: HOSTILE}, "wrong_type"),
    (HOSTILE, "wrong_type"),
]
Projection = Callable[[JsonValue], QueryFilterSummary | DiagnosticQueryFilterSummary]


def leaf(bt: str) -> dict[str, Any]:
    # Invented Boolean states for schema coverage; real values remain human evidence.
    return {"btType": bt, **{field: False for kind, field, _ in FIELDS if kind == bt}}


def either(left: Any, right: Any) -> dict[str, Any]:
    return {"btType": "BTOrFilter-167", "operand1": left, "operand2": right}


def entity(value: str) -> dict[str, Any]:
    return {"btType": "BTEntityTypeFilter-124", "entityType": value}


def body(value: str) -> dict[str, Any]:
    return {"btType": "BTBodyTypeFilter-112", "bodyType": value}


def sketch() -> dict[str, Any]:
    return {
        "btType": "BTSketchObjectFilter-184",
        "isSketchObject": False,
        "objectType": "NOT_SKETCH_OBJECT",
    }


def modifiable() -> dict[str, Any]:
    return {"btType": "BTModifiableEntityOnlyFilter-1593", "modifiableOnly": True}


def synthetic_deep_direction() -> Any:
    # Explicit stress fixture, NOT the unknown real extrudeDirection serialization.
    tree: Any = {"btType": "BTGeometryFilter-130", "geometryType": "LINE"}
    for geometry in ("CIRCLE", "ARC", "CYLINDER", "PLANE"):
        tree = either(
            tree, {"btType": "BTGeometryFilter-130", "geometryType": geometry}
        )
    tree = either(tree, body("MATE_CONNECTOR"))
    left = tree["operand1"]
    for _ in range(6):
        left = {"btType": "BTNotFilter-165", "operand": left}
    tree["operand1"] = left
    return tree


def closure_inventory() -> dict[str, Any]:
    data = all_role_inventory()
    # Reported shallow topologies with synthetic optional Boolean leaf values.
    for prefix in ("", "secondDirection"):
        names = (
            ("endBoundEntityFace", "endBoundEntityBody", "endBoundEntityVertex")
            if not prefix
            else (
                "secondDirectionBoundEntityFace",
                "secondDirectionBoundEntityBody",
                "secondDirectionBoundEntityVertex",
            )
        )
        param(data, 2, names[0])["filter"] = either(
            both(both(entity("FACE"), sketch()), leaf(MESH)), body("MATE_CONNECTOR")
        )
        param(data, 2, names[1])["filter"] = both(
            both(both(entity("BODY"), either(body("SOLID"), body("SHEET"))), sketch()),
            leaf(MESH),
        )
        param(data, 2, names[2])["filter"] = either(entity("VERTEX"), leaf(MATE))
    param(data, 2, "booleanScope")["filter"] = both(
        both(both(entity("BODY"), body("SOLID")), modifiable()), leaf(MESH)
    )
    param(data, 2, "booleanSurfaceScope")["filter"] = both(
        both(both(both(entity("BODY"), body("SHEET")), modifiable()), leaf(MESH)),
        sketch(),
    )
    param(data, 2, "extrudeDirection")["filter"] = synthetic_deep_direction()
    for key in ("startPartialEntity", "endPartialEntity"):
        param(data, 3, key)["filter"] = either(
            both(entity("FACE"), leaf(MESH)), either(entity("VERTEX"), leaf(MATE))
        )
    return data


@pytest.mark.parametrize(
    "project", [unproven_filter_summary, diagnostic_filter_summary]
)
@pytest.mark.parametrize("bt,field,label", FIELDS)
@pytest.mark.parametrize("value,expected", STATES)
def test_every_official_boolean_field_has_only_explicit_closed_states(
    project: Projection, bt: str, field: str, label: str, value: Any, expected: str
) -> None:
    raw = leaf(bt)
    if value is MISSING:
        del raw[field]
    else:
        raw[field] = value
    summary = project(raw)
    assert summary.signature == (
        ("allow_mesh_geometry" if bt == MESH else "mate_connector"),
    )
    assert summary.node_count == summary.max_depth == 1
    states = summary.leaf_states[0].fields
    assert len(states) == (1 if bt == MESH else 3)
    assert next(s.state for s in states if s.field == label) == expected
    assert summary.malformed is (expected in ("null", "wrong_type"))
    assert not summary.uninspected and not summary.unexpected_fields
    assert (
        HOSTILE not in summary.model_dump_json()
        and "BT" not in summary.model_dump_json()
    )
    assert field not in leaf_states_text(summary)


@pytest.mark.parametrize("bt", [MESH, MATE])
@pytest.mark.parametrize("extra", ["nodeId", "queryString", "featureId", HOSTILE])
def test_new_leaf_envelopes_flag_unknown_fields_without_walking_values(
    bt: str, extra: str
) -> None:
    raw = leaf(bt)
    raw[extra] = raw
    summary = diagnostic_filter_summary(raw)
    assert summary.unexpected_fields and summary.uninspected
    assert summary.node_count == 1 and not summary.signature_truncated
    assert extra not in summary.model_dump_json()


@pytest.mark.parametrize("bt", [MESH, MATE])
def test_unknown_schema_variant_stays_opaque(bt: str) -> None:
    raw = leaf(bt)
    raw["btType"] += "-private-unsupported"
    summary = diagnostic_filter_summary(raw)
    assert summary.root == "unknown" and summary.uninspected
    assert not summary.leaf_states and "private-" not in summary.model_dump_json()


def test_inventory_depth_is_separate_from_production_rejection_and_acceptance() -> None:
    tree = synthetic_deep_direction()
    original = deepcopy(tree)
    normal = unproven_filter_summary(tree)
    extended = diagnostic_filter_summary(tree)
    assert MAX_DEPTH == 8 and MAX_DIAGNOSTIC_DEPTH == 16 and MAX_NODES == 64
    assert normal.max_depth == 8 and normal.truncated and not normal.signature
    assert extended.max_depth == 12 and extended.node_count == 17
    assert extended.root == "or" and extended.root_child_count == 2
    assert not extended.truncated and not extended.signature_truncated
    left = "or(or(or(or(geometry,geometry),geometry),geometry),geometry)"
    expected = "or(" + "not(" * 6 + left + ")" * 6 + ",body_type)"
    assert "".join(extended.signature) == expected
    for value in ("line", "circle", "arc", "cylinder", "plane"):
        assert f"geometry={value}" in leaf_states_text(extended)
    assert "body_type=mate_connector" in leaf_states_text(extended)
    assert not isinstance(extended, QueryFilterSummary)
    with pytest.raises(ValidationError):
        QueryFilterSummary.model_validate(extended.model_dump())
    with pytest.raises(ValidationError):
        QueryFilterSummary.model_validate(extended)
    assert not matches_extrude_entities_filter(
        tree
    ) and not matches_fillet_entities_filter(tree)
    assert tree == original


@pytest.mark.parametrize("fault", ["boundary", "excessive", "wide", "cycle"])
def test_diagnostic_depth_and_node_limits_always_terminate_and_truncate(
    fault: str,
) -> None:
    raw: Any = leaf(MATE)
    if fault in ("boundary", "excessive"):
        for _ in range(MAX_DIAGNOSTIC_DEPTH - 1 + (fault == "excessive")):
            raw = {"btType": "BTNotFilter-165", "operand": raw}
    elif fault == "wide":
        for _ in range(6):
            raw = both(raw, raw)
    else:
        raw = {"btType": "BTNotFilter-165"}
        raw["operand"] = raw
    summary = diagnostic_filter_summary(raw)
    assert summary.max_depth <= 16 and summary.node_count <= 64
    assert summary.truncated is (fault != "boundary")
    assert summary.signature_truncated is (fault != "boundary")
    if fault == "boundary":
        assert summary.max_depth == summary.node_count == 16
    else:
        assert summary.signature == ()
    if fault == "wide":
        assert summary.node_count == 64


def test_complete_targets_preserve_old_roles_and_never_grant_eligibility() -> None:
    before = all_role_inventory()
    data = closure_inventory()
    original = fingerprint(data)
    reports = query_role_inventory(data)
    for position, report, count in ((2, reports[0], 13), (3, reports[1], 8)):
        summary = report.summary
        assert (
            summary.total_query_roles_discovered
            == summary.total_query_roles_inspected
            == count
        )
        assert summary.all_roles_inspected
        assert not any(
            (
                summary.any_malformed,
                summary.any_unexpected_fields,
                summary.any_uninspected,
                summary.any_truncated,
            )
        )
        category: ShapeCategory = "extrude" if position == 2 else "fillet"
        first = diagnose_ui_shape(data["features"][position - 1], category)
        assert (
            first.failure is not None
            and first.failure.reason == "query_filter_unproven"
        )
        assert first.failure.parameter == (
            "wallShape" if position == 2 else "startPartialEntity"
        )
        unchanged = (
            ("entities", "surfaceEntities", "wallShape", "startOffsetEntity")
            if position == 2
            else (
                "entities",
                "side1Face",
                "side2Face",
                "centerFaces",
                "keepEdges",
                "smoothCornerExceptions",
            )
        )
        for key in unchanged:
            raw = param(before, position, key)["filter"]
            old = unproven_filter_summary(raw)
            new = next(r.query_filter for r in report.roles if r.parameter == key)
            assert new is not None and new.model_dump() == old.model_dump()
        replacement_rejects(data, position)
    mesh_fields = {"allow_mesh_geometry"}
    mate_fields = {
        "allow_implicit_mate_connector",
        "mate_connector_inference_default",
        "requires_occurrence",
    }
    for feature in reports:
        for role in feature.roles:
            f = role.query_filter
            assert f is not None
            fields = {state.field for leaf in f.leaf_states for state in leaf.fields}
            if "allow_mesh_geometry" in f.categories:
                assert mesh_fields <= fields
            if "mate_connector" in f.categories:
                assert mate_fields <= fields
    direction = next(
        r.query_filter for r in reports[0].roles if r.parameter == "extrudeDirection"
    )
    assert (
        direction is not None
        and direction.max_depth == 12
        and not direction.signature_truncated
    )
    assert fingerprint(data) == original


@pytest.mark.parametrize(
    "fault", ["malformed", "unexpected", "uninspected", "truncated"]
)
def test_new_leaf_and_depth_faults_keep_aggregate_completeness_honest(
    fault: str,
) -> None:
    data = closure_inventory()
    item = param(data, 2, "endBoundEntityVertex")
    if fault == "malformed":
        item["filter"]["operand2"]["requiresOccurrence"] = HOSTILE
    elif fault == "unexpected":
        item["filter"]["operand2"][HOSTILE] = HOSTILE
    elif fault == "uninspected":
        item["filter"]["operand2"]["btType"] = HOSTILE
    else:
        for _ in range(20):
            item["filter"] = {"btType": "BTNotFilter-165", "operand": item["filter"]}
    report = query_role_inventory(data)[0]
    flag = "any_unexpected_fields" if fault == "unexpected" else f"any_{fault}"
    assert report.summary.model_dump()[flag]
    if fault != "malformed":
        assert not report.summary.all_roles_inspected
    assert HOSTILE not in report.model_dump_json()


@pytest.mark.parametrize("hostile", [False, True])
def test_one_writes_off_inspector_refresh_can_report_complete_targets_privately(
    hostile: bool, harness: Harness, caplog: pytest.LogCaptureFixture
) -> None:
    user = harness.login()
    set_scope(harness, user, "OAuth2ReadPII OAuth2Read")
    settings = harness.runtime.settings
    settings.environment = "development"
    settings.forge_safe_edit_diagnostics_enabled = True
    assert not settings.forge_cad_writes_enabled
    provider = Provider()
    provider.data = closure_inventory()
    if hostile:
        param(provider.data, 2, "endBoundEntityFace")["filter"]["operand1"]["operand2"][
            "allowsMeshGeometry"
        ] = HOSTILE
        param(provider.data, 3, "startPartialEntity")["filter"]["operand2"]["operand2"][
            "requiresOccurrence"
        ] = HOSTILE
    original = fingerprint(provider.data)
    normal = CadProvider()
    calls: list[httpx.Request] = []

    def read(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        calls.append(request)
        return (
            provider.handle(request)
            if "/m/" in request.url.path
            or request.url.path.endswith("currentmicroversion")
            else normal.handle(request)
        )

    with (
        httpx.Client(transport=httpx.MockTransport(read)) as transport,
        caplog.at_level(logging.WARNING),
    ):
        harness.client.app.state.cad_transport = transport  # type: ignore[attr-defined]
        response = harness.client.get(
            "/api/onshape/part-studio/inspector",
            params=REF.model_dump(),
            headers=harness.headers(),
        )
    assert response.status_code == 200 and len(calls) == 13
    summaries = [
        json.loads(r.message.split("metadata=", 1)[1])
        for r in caplog.records
        if r.message.startswith("safe_edit_query_role_summary ")
    ]
    assert len(summaries) == 4
    for summary in summaries:
        count = 13 if summary["category"] == "extrude" else 8
        assert (
            summary["total_query_roles_discovered"]
            == summary["total_query_roles_inspected"]
            == count
        )
        assert summary["all_roles_inspected"] and summary["any_malformed"] is hostile
        assert not any(
            summary[k]
            for k in ("any_unexpected_fields", "any_uninspected", "any_truncated")
        )
    rows = [
        r.message
        for r in caplog.records
        if r.message.startswith("safe_edit_query_role ")
    ]
    assert len(rows) == 42
    directions = [r for r in rows if "parameter=extrudeDirection " in r]
    assert len(directions) == 2 and all(
        "max_depth=12 node_count=17" in r and "signature_truncated=false" in r
        for r in directions
    )
    assert (
        "allow_mesh_geometry=" in caplog.text and "requires_occurrence=" in caplog.text
    )
    assert "parameter=wallShape reason=query_filter_unproven" in caplog.text
    assert "parameter=startPartialEntity reason=query_filter_unproven" in caplog.text
    assert "safe_edit_probe outcome=eligible_no_proposal_no_write" in caplog.text
    for forbidden in (
        HOSTILE,
        "BTAllowMeshGeometryFilter",
        "BTMateConnectorFilter",
        "allowsMeshGeometry",
        "allowImplicitMateConnector",
        "requiresOccurrence",
        REF.documentId,
        REF.workspaceId,
        REF.elementId,
        "synthetic-feature-",
    ):
        assert forbidden not in caplog.text
    assert "safe_edit_query_role" not in response.text
    assert provider.writes == 0 and fingerprint(provider.data) == original
    with harness.runtime.sessions() as db:
        assert db.scalar(select(func.count()).select_from(WriteRecord)) == 0
        assert db.scalar(select(func.count()).select_from(WriteFence)) == 0
