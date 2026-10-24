"""Unproven filters stay rejected; bounded synthetic structure never grants writes."""

import logging
from copy import deepcopy
from typing import Any

import httpx2 as httpx
import pytest
from conftest import Harness
from pydantic import JsonValue, ValidationError
from test_cad_read import REF
from test_modify_common_metadata import OPERATIONS
from test_modify_conformance import operation_for, rejected_replacement
from test_modify_plan import OP, PlanProvider, target
from test_modify_representation import enabled_settings, metadata
from test_modify_ui_conformance import param, replacement_rejects, ui_inventory
from test_safe_edit import M0, M1, Provider, bodies, config

from forge_api.cad_edits.domain import EditError, fingerprint
from forge_api.cad_edits.plans import ResolvedOperation
from forge_api.integrations.onshape import standard_edit_shapes
from forge_api.integrations.onshape.dev import safe_edit
from forge_api.integrations.onshape.dev.standard_shape_failure import diagnose_ui_shape
from forge_api.integrations.onshape.edit_registry import change
from forge_api.integrations.onshape.modify_evidence import (
    project_modify_evidence,
    verify_operation,
)
from forge_api.integrations.onshape.query_filter_evidence import (
    MAX_DEPTH,
    MAX_NODES,
    QueryFilterSummary,
    unproven_filter_summary,
)
from forge_api.integrations.onshape.standard_edit_shapes import (
    UI_RULES,
    ui_quantity_parameter,
)
from forge_api.integrations.onshape.standard_shape_contract import ShapeValidationError

# Public SDK shapes, invented payloads. These are NOT captures of ordinary UI
# trees, nor an allowlist. Even plausible SDK/source-shaped filters must reject.
LEAF: dict[str, JsonValue] = {
    "btType": "BTEntityTypeFilter-124",
    "entityType": "private-geometry",
}
BINARY: dict[str, JsonValue] = {
    "btType": "BTAndFilter-110",
    "operand1": LEAF,
    "operand2": {"btType": "BTGeometryFilter-130", "geometryType": "private-geometry"},
}
FILTERS: list[Any] = [
    LEAF,
    BINARY,
    {"btType": "BTOrFilter-167", "operand1": LEAF, "operand2": BINARY},
    {"btType": "BTNotFilter-165", "operand": LEAF},
    {"btType": "BTBodyTypeFilter-112", "bodyType": "private-body"},
    {"btType": "BTEdgeTopologyFilter-122", "edgeTopology": "private-topology"},
    {"btType": "BTConstructionObjectFilter-113", "isConstruction": False},
    {"btType": "BTSketchObjectFilter-184", "isSketchObject": True},
    {"btType": "private-unknown", "queryString": "private-query"},
    {"btType": "BTAndFilter-110", "operand1": ["private-child"]},
    {
        "btType": "BTAndFilter-110",
        "operand1": LEAF,
        "operand2": LEAF,
        "private-field": "private-value",
    },
    {},
    None,
    [],
    "private-string",
    False,
    123.456789,
]
QUERY_ROLES = [
    (position, key)
    for position, category in ((2, "extrude"), (3, "fillet"))
    for key, rule in UI_RULES[category].items()
    if rule.bt_type == "BTMParameterQueryList-148"
]


@pytest.mark.parametrize("position,key", QUERY_ROLES)
@pytest.mark.parametrize("query_filter", FILTERS)
def test_all_present_filters_reject_for_active_and_empty_roles_without_mutation(
    position: int, key: str, query_filter: Any
) -> None:
    data = ui_inventory()
    param(data, position, key)["filter"] = deepcopy(query_filter)
    original = deepcopy(data)
    feature = data["features"][position - 1]
    with pytest.raises(ShapeValidationError) as caught:
        ui_quantity_parameter(feature, "depth" if position == 2 else "radius")
    assert str(caught.value) == "unsupported_target" and caught.value.status == 422
    assert caught.value.failure.reason == "query_filter_unproven"
    assert caught.value.failure.parameter == key
    report = diagnose_ui_shape(feature, "extrude" if position == 2 else "fillet")
    assert report.failure == caught.value.failure
    assert report.query_filter == caught.value.query_filter
    assert report.query_filter == unproven_filter_summary(query_filter)
    assert "private-" not in report.model_dump_json()
    replacement_rejects(data, position)
    assert fingerprint(data) == fingerprint(original)


@pytest.mark.parametrize(
    "bt,category",
    [
        ("BTEntityTypeFilter-124", "entity_type"),
        ("BTGeometryFilter-130", "geometry"),
        ("BTBodyTypeFilter-112", "body_type"),
        ("BTEdgeTopologyFilter-122", "edge_topology"),
        ("BTConstructionObjectFilter-113", "construction"),
        ("BTAndFilter-110", "and"),
        ("BTOrFilter-167", "or"),
        ("BTNotFilter-165", "not"),
        ("BTSketchObjectFilter-184", "sketch_object"),
        ("BTQueryFilter-183", "query_filter"),
        ("BTEntityTypeFilter-124-private", "unknown"),
        (None, "unknown"),
    ],
)
def test_only_exact_documented_type_categories_escape(bt: Any, category: str) -> None:
    summary = unproven_filter_summary({"btType": bt, "private-field": "private-value"})
    assert summary.root == category
    assert "private-" not in summary.model_dump_json()


def test_binary_and_unary_structure_uses_only_documented_operand_slots() -> None:
    summary = unproven_filter_summary(BINARY)
    assert summary.model_dump() == {
        "root": "and",
        "root_state": "object",
        "root_child_count": 2,
        "max_depth": 2,
        "node_count": 3,
        "categories": ("entity_type", "geometry", "and"),
        "signature": ("and", "(", "entity_type", ",", "geometry", ")"),
        "signature_truncated": False,
        "leaf_states": (
            {
                "visit": 2,
                "fields": ({"field": "entity_type", "state": "unknown_value"},),
            },
            {"visit": 3, "fields": ({"field": "geometry", "state": "unknown_value"},)},
        ),
        "malformed": False,
        "missing_operand": False,
        "unexpected_fields": False,
        "uninspected": False,
        "truncated": False,
    }
    missing = unproven_filter_summary({"btType": "BTAndFilter-110", "operand1": None})
    assert missing.missing_operand and missing.malformed
    assert missing.root_child_count == 1 and missing.node_count == 2
    unary = unproven_filter_summary({"btType": "BTNotFilter-165", "operand": LEAF})
    assert unary.root_child_count == 1 and unary.max_depth == 2


def test_diagnostic_depth_and_total_work_are_bounded_without_recursive_walk() -> None:
    chain: dict[str, Any] = deepcopy(LEAF)
    for _ in range(2000):
        chain = {"btType": "BTNotFilter-165", "operand": chain}
    summary = unproven_filter_summary(chain)
    assert summary.max_depth == summary.node_count == MAX_DEPTH and summary.truncated
    feature = ui_inventory()["features"][1]
    next(p for p in feature["parameters"] if p["parameterId"] == "entities")[
        "filter"
    ] = chain
    with pytest.raises(ShapeValidationError) as caught:
        ui_quantity_parameter(feature, "depth")
    assert caught.value.query_filter == summary
    tree: dict[str, Any] = deepcopy(LEAF)
    for _ in range(10):
        tree = {"btType": "BTAndFilter-110", "operand1": tree, "operand2": tree}
    summary = unproven_filter_summary(tree)
    assert summary.node_count == MAX_NODES and summary.max_depth <= MAX_DEPTH
    assert summary.truncated


def test_excess_width_unknown_fields_and_payloads_are_never_walked() -> None:
    wide: dict[str, JsonValue] = dict(BINARY)
    for i in range(20000):
        wide[f"private-{i}"] = ["private-value"]
    summary = unproven_filter_summary(wide)
    assert summary.unexpected_fields and summary.root_child_count == 2
    assert summary.node_count == 3 and "private-" not in summary.model_dump_json()
    opaque: dict[str, Any] = {"btType": "BTSketchObjectFilter-184"}
    opaque["private-payload"] = opaque
    summary = unproven_filter_summary(opaque)
    assert summary.uninspected and summary.node_count == 1


@pytest.mark.parametrize("position", [2, 3])
@pytest.mark.parametrize("query_filter", [LEAF, BINARY, None])
def test_filtered_replacements_never_reach_proposal_or_provider_dispatch(
    harness: Harness, position: int, query_filter: Any
) -> None:
    provider = PlanProvider()
    provider.data = ui_inventory()
    param(provider.data, position, "entities")["filter"] = deepcopy(query_filter)
    rejected_replacement(harness, provider, position)


@pytest.mark.parametrize(
    "query_filter",
    [LEAF, BINARY, {"btType": "private-type\noutcome=exact_match"}, None],
)
def test_only_closed_structure_is_logged_on_four_existing_gets(
    query_filter: Any, caplog: pytest.LogCaptureFixture
) -> None:
    provider = Provider()
    provider.data = ui_inventory()
    for position in (2, 3):
        param(provider.data, position, "entities")["filter"] = deepcopy(query_filter)
    with (
        httpx.Client(transport=httpx.MockTransport(provider.handle)) as transport,
        caplog.at_level(logging.WARNING),
    ):
        safe_edit.CoverageClient(
            enabled_settings(), transport, "private-token"
        ).compare(REF)
    lines = [
        r.message
        for r in caplog.records
        if r.message.startswith("safe_edit_standard_shape_")
    ]
    assert len(lines) == 4
    assert all("reason=query_filter_unproven filter_root=" in line for line in lines)
    assert all("outcome=exact_match" not in line for line in lines)
    for forbidden in (
        "private-",
        "BTAndFilter",
        "BTEntityTypeFilter",
        REF.documentId,
        REF.workspaceId,
        REF.elementId,
        provider.marker,
    ):
        assert forbidden not in caplog.text
    assert len(provider.calls) == 4 and all(
        call.method == "GET" for call in provider.calls
    )
    assert provider.writes == 0


@pytest.mark.parametrize(
    "fault", ["diagnostics", "environment", "writes", "source", "incomplete"]
)
def test_disabled_filter_projection_cannot_run_the_production_summary(
    fault: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = enabled_settings()
    data = ui_inventory()
    param(data, 2, "entities")["filter"] = BINARY
    if fault == "diagnostics":
        settings.forge_safe_edit_diagnostics_enabled = False
    elif fault == "environment":
        settings.environment = "production"
    elif fault == "writes":
        settings.forge_cad_writes_enabled = True
    elif fault == "incomplete":
        data["isComplete"] = False

    def forbidden(*_: Any, **__: Any) -> Any:
        raise AssertionError("guarded filter evidence executed")

    monkeypatch.setattr(standard_edit_shapes, "unproven_filter_summary", forbidden)
    with httpx.Client(transport=httpx.MockTransport(forbidden)) as transport:
        assert (
            safe_edit.CoverageClient(
                settings, transport, "private-token"
            )._shape_validation(data, source_matches=fault != "source")
            is None
        )


@pytest.mark.parametrize("position,kind", OPERATIONS)
@pytest.mark.parametrize("effect", ["preserve", "remove", "modify", "add_to_target"])
def test_full_inventory_verification_preserves_unedited_filters_and_rejects_effects(
    position: int, kind: str, effect: str
) -> None:
    data = ui_inventory()
    other = 5 - position
    param(data, other, "entities")["filter"] = deepcopy(BINARY)
    before = project_modify_evidence(REF, M0, data, config(), bodies())
    original_other = deepcopy(data["features"][other - 1])
    operation = OP.validate_python(operation_for(kind, target(position).handle))
    updated, preview = change(data["features"], target(position), operation)
    assert data["features"][other - 1] == original_other
    data["features"][position - 1] = updated
    if effect == "remove":
        del param(data, other, "entities")["filter"]
    elif effect == "modify":
        param(data, other, "entities")["filter"]["operand1"]["entityType"] = (
            "private-other-value"
        )
    elif effect == "add_to_target":
        param(data, position, "entities")["filter"] = deepcopy(LEAF)
    data["sourceMicroversion"] = M1
    after = project_modify_evidence(REF, M1, data, config(M1), bodies(M1))
    resolved = ResolvedOperation(
        operation=operation, target=target(position), preview=preview
    )
    if effect == "preserve":
        verify_operation(before, after, resolved, M1)
    else:
        with pytest.raises(EditError, match="verification_failed"):
            verify_operation(before, after, resolved, M1)


@pytest.mark.parametrize("field", ["root", "categories", "root_state", "private-field"])
def test_summary_schema_cannot_echo_provider_strings(field: str) -> None:
    data = unproven_filter_summary(LEAF).model_dump()
    data[field] = ("private-value",) if field == "categories" else "private-value"
    with pytest.raises(ValidationError) as caught:
        QueryFilterSummary.model_validate(data)
    assert "private-value" not in str(caught.value)


@pytest.mark.parametrize("role", ["unknown_sibling", "quantity", "array", "query_item"])
def test_filter_diagnostic_does_not_expand_other_envelopes(role: str) -> None:
    data = ui_inventory()
    item = param(
        data,
        3,
        "entities"
        if role in ("unknown_sibling", "query_item")
        else "radius"
        if role == "quantity"
        else "vertexSettings",
    )
    if role == "query_item":
        item = item["queries"][0]
    item["filter"] = BINARY
    if role == "unknown_sibling":
        item["private-field"] = "private-value"
    report = diagnose_ui_shape(data["features"][2], "fillet")
    assert report.failure and report.failure.reason == (
        "query_item_unexpected_field" if role == "query_item" else "unexpected_field"
    )
    assert report.query_filter is None
    assert metadata(data, 3)["replacement"] == "unsupported_shape"
