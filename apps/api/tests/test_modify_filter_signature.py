"""Finite evidence only: source-derived synthetic trees are never write proof."""

import json
import logging
from copy import deepcopy
from pathlib import Path
from typing import Any, get_args

import httpx2 as httpx
import pytest
from pydantic import ValidationError
from test_cad_read import REF
from test_modify_common_metadata import OPERATIONS
from test_modify_conformance import operation_for
from test_modify_plan import OP, inventory, target
from test_modify_query_filter_evidence import QUERY_ROLES
from test_modify_representation import enabled_settings, metadata
from test_modify_ui_conformance import param, replacement_rejects, ui_inventory
from test_safe_edit import M0, M1, Provider, bodies, config

from forge_api.cad_edits.domain import EditError, fingerprint
from forge_api.cad_edits.plans import ResolvedOperation
from forge_api.integrations.onshape.dev import safe_edit
from forge_api.integrations.onshape.edit_registry import change
from forge_api.integrations.onshape.modify_evidence import (
    project_modify_evidence,
    verify_operation,
)
from forge_api.integrations.onshape.query_filter_evidence import (
    CATEGORIES,
    KINDS,
    LEAF_RULES,
    MAX_DEPTH,
    MAX_FILTER_LOG_CHARS,
    MAX_NODES,
    MAX_SIGNATURE_CHARS,
    FilterCategory,
    LeafEvidence,
    LeafField,
    LeafFieldState,
    LeafState,
    QueryFilterSummary,
    leaf_states_text,
    unproven_filter_summary,
)
from forge_api.integrations.onshape.standard_edit_shapes import ui_quantity_parameter
from forge_api.integrations.onshape.standard_shape_contract import ShapeValidationError

FIXTURES = json.loads(
    (Path(__file__).parent / "fixtures/modify_source_filters.json").read_text()
)
SOURCE_TREES = [FIXTURES[k]["filter"] for k in ("extrude", "fillet")]
# Independent published discriminator-to-label expectations; no prefix matches.
SUBTYPES = (
    ("BTActiveSheetMetalFilter-2944", "active_sheet_metal"),
    ("BTAllowEdgePointFilter-2371", "allow_edge_point"),
    ("BTAllowFlattenedGeometryFilter-2140", "allow_flattened_geometry"),
    ("BTAllowMeshGeometryFilter-1026", "allow_mesh_geometry"),
    ("BTAnnotationFilter-4841", "annotation"),
    ("BTCenterOfMassFilter-5569", "center_of_mass"),
    ("BTClosedCompositeConstituentFilter-2804", "closed_composite_constituent"),
    ("BTClosedCurveFilter-1206", "closed_curve"),
    ("BTCurvedTextObjectFilter-5114", "curved_text"),
    ("BTFeatureFilter-127", "feature"),
    ("BTFeatureTypeFilter-962", "feature_type"),
    ("BTFlatSheetMetalFilter-3018", "flat_sheet_metal"),
    ("BTImageFilter-853", "image"),
    ("BTInContextObjectFilter-3810", "in_context_object"),
    ("BTMateConnectorFilter-163", "mate_connector"),
    ("BTMateFilter-162", "mate"),
    ("BTModifiableEntityOnlyFilter-1593", "modifiable_entity_only"),
    ("BTOccurrenceFilter-166", "occurrence"),
    ("BTPlaneOrientationFilter-1700", "plane_orientation"),
    ("BTSMApplicationTypeFilter-4430", "sheet_metal_application_type"),
    ("BTSMDefinitionEntityTypeFilter-1651", "sheet_metal_definition_entity_type"),
    ("BTSectionGeometryFilter-4161", "section_geometry"),
    ("BTSketchObjectFilter-184", "sketch_object"),
    ("BTSketchSolveStatusFilter-3657", "sketch_solve_status"),
    ("BTSplineControlPolygonFilter-1130", "spline_control_polygon"),
    ("BTSplineHandleFilter-2971", "spline_handle"),
    ("BTSplineInternalPointFilter-4101", "spline_internal_point"),
    ("BTTextObjectFilter-1515", "text_object"),
    ("BTTextStrokeFilter-461", "text_stroke"),
)
LEAF_FIELDS = [
    (bt, rule)
    for bt, category in KINDS.items()
    for rule in LEAF_RULES.get(category, ())
]


@pytest.mark.parametrize("bt,category", SUBTYPES)
def test_each_previously_collapsed_subtype_has_exact_closed_label(
    bt: str, category: str
) -> None:
    summary = unproven_filter_summary({"btType": bt, "private-value": "private-id"})
    assert summary.root == category
    assert summary.signature == (category,)
    assert "private-" not in summary.model_dump_json()
    assert "BT" not in summary.model_dump_json()
    assert "other_known" not in summary.model_dump_json()
    assert KINDS[bt] in CATEGORIES


@pytest.mark.parametrize(
    "bt",
    [
        "private-bt\nsignature=and",
        "BTActiveSheetMetalFilter-2944-private",
        "",
        None,
        [],
    ],
)
def test_unknown_discriminator_is_only_unknown(bt: Any) -> None:
    summary = unproven_filter_summary({"btType": bt, "featureId": "private-id"})
    assert summary.root == "unknown" and summary.signature == ("unknown",)
    assert "private-" not in summary.model_dump_json()


@pytest.mark.parametrize("bt,rule", LEAF_FIELDS)
@pytest.mark.parametrize(
    "value,expected",
    [
        (None, "null"),
        ([], "wrong_type"),
        ({"private-key": "private-value"}, "wrong_type"),
        (1, "wrong_type"),
        ("private-enum\nsignature=face", "unknown_value"),
    ],
)
def test_leaf_values_are_closed_and_never_echoed(
    bt: str, rule: Any, value: Any, expected: str
) -> None:
    summary = unproven_filter_summary({"btType": bt, rule.provider_field: value})
    state = next(
        p.state for p in summary.leaf_states[0].fields if p.field == rule.field
    )
    assert state == (
        "wrong_type" if rule.values is None and isinstance(value, str) else expected
    )
    assert summary.malformed is (state in ("wrong_type", "null"))
    assert "private-" not in summary.model_dump_json()
    assert "signature=face" not in leaf_states_text(summary)


@pytest.mark.parametrize("bt,rule", LEAF_FIELDS)
def test_absent_leaf_fields_are_explicit_and_not_inferred(bt: str, rule: Any) -> None:
    summary = unproven_filter_summary({"btType": bt})
    assert (
        next(p.state for p in summary.leaf_states[0].fields if p.field == rule.field)
        == "missing"
    )


@pytest.mark.parametrize("bt,rule", LEAF_FIELDS)
def test_all_official_enum_and_boolean_states_use_constant_labels(
    bt: str, rule: Any
) -> None:
    cases = (
        list(rule.values.items())
        if rule.values is not None
        else [(False, "false"), (True, "true")]
    )
    for raw, expected in cases:
        summary = unproven_filter_summary({"btType": bt, rule.provider_field: raw})
        assert (
            next(
                p.state for p in summary.leaf_states[0].fields if p.field == rule.field
            )
            == expected
        )
        assert expected in get_args(LeafState)


@pytest.mark.parametrize("role", ["extrude", "fillet"])
def test_exact_source_candidate_signature_and_counts_do_not_claim_real_capture(
    role: str,
) -> None:
    fixture = FIXTURES[role]
    before = deepcopy(fixture["filter"])
    summary = unproven_filter_summary(fixture["filter"])
    assert "".join(summary.signature) == fixture["signature"]
    assert summary.node_count == fixture["nodes"]
    assert summary.max_depth == fixture["depth"]
    assert not summary.signature_truncated and not summary.truncated
    assert not summary.uninspected and not summary.unexpected_fields
    assert fixture["filter"] == before
    states = leaf_states_text(summary)
    assert states == fixture["leaf_states"]
    assert "construction=false" in states and "sketch_object=" in states
    if role == "extrude":
        assert "allow_flattened_geometry=true" in states
        assert "allow_flattened_geometry=false" in states and "geometry=plane" in states
        assert states.count("entity_type=face") == 2
    else:
        assert (
            "active_sheet_metal=false" in states and "edge_topology=two_sided" in states
        )
        assert "sheet_metal_definition_entity_type=vertex" in states
        assert (
            "modifiable_entity_only=true" in states
            and "internal_edge=missing" in states
        )
    assert "Synthetic" in FIXTURES["provenance"]


def test_operand_order_and_leaf_visit_positions_are_deterministic() -> None:
    raw = deepcopy(SOURCE_TREES[0])
    first = unproven_filter_summary(raw)
    raw = dict(reversed(tuple(raw.items())))
    assert unproven_filter_summary(raw) == first
    raw["operand1"], raw["operand2"] = raw["operand2"], raw["operand1"]
    second = unproven_filter_summary(raw)
    assert (
        second.signature != first.signature and second.leaf_states != first.leaf_states
    )
    assert second.node_count == first.node_count


@pytest.mark.parametrize(
    "bt,slots",
    [
        ("BTAndFilter-110", ("operand1", "operand2")),
        ("BTOrFilter-167", ("operand1", "operand2")),
        ("BTNotFilter-165", ("operand",)),
    ],
)
@pytest.mark.parametrize("fault", ["missing", "extra", "null", "array", "wrong_type"])
def test_malformed_operators_cannot_look_like_complete_signatures(
    bt: str, slots: tuple[str, ...], fault: str
) -> None:
    raw = {
        "btType": bt,
        **{slot: deepcopy(SOURCE_TREES[0]["operand2"]) for slot in slots},
    }
    if fault == "missing":
        del raw[slots[-1]]
    elif fault == "extra":
        raw["operand3"] = {"private-key": "private-value"}
    else:
        raw[slots[0]] = (
            None if fault == "null" else [] if fault == "array" else "private-value"
        )
    summary = unproven_filter_summary(raw)
    if fault in ("missing", "extra"):
        assert summary.signature_truncated and summary.signature == ()
        assert summary.missing_operand or summary.unexpected_fields
    else:
        assert summary.malformed and "unknown" in summary.signature
    assert "private-" not in summary.model_dump_json()


def test_bounds_never_report_a_clipped_signature_as_complete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    leaf = SOURCE_TREES[0]["operand2"]
    raw = deepcopy(leaf)
    for _ in range(MAX_DEPTH - 1):
        raw = {"btType": "BTNotFilter-165", "operand": raw}
    assert not unproven_filter_summary(raw).signature_truncated
    raw = {"btType": "BTNotFilter-165", "operand": raw}
    summary = unproven_filter_summary(raw)
    assert summary.signature == () and summary.signature_truncated
    assert summary.max_depth == summary.node_count == 8
    tree = deepcopy(leaf)
    for _ in range(5):
        tree = {"btType": "BTAndFilter-110", "operand1": tree, "operand2": tree}
    assert unproven_filter_summary(tree).node_count == 63
    assert not unproven_filter_summary(tree).signature_truncated
    summary = unproven_filter_summary(
        {"btType": "BTAndFilter-110", "operand1": tree, "operand2": leaf}
    )
    assert summary.node_count == MAX_NODES and summary.signature_truncated
    assert summary.signature == () and summary.truncated
    from forge_api.integrations.onshape import query_filter_evidence

    monkeypatch.setattr(query_filter_evidence, "MAX_SIGNATURE_CHARS", 4)
    summary = unproven_filter_summary(leaf)
    assert summary.signature_truncated and not summary.truncated
    assert summary.signature == () and summary.node_count == 1


def test_actual_and_schema_maximum_log_lengths_are_bounded() -> None:
    longest_category = max(get_args(FilterCategory), key=len)
    longest_field = max(get_args(LeafField), key=len)
    longest_state = max(get_args(LeafState), key=len)
    raw = unproven_filter_summary(SOURCE_TREES[0]).model_dump()
    raw.update(
        {
            "signature": (longest_category,)
            * (MAX_SIGNATURE_CHARS // len(longest_category)),
            "categories": (longest_category,) * len(CATEGORIES),
            "leaf_states": tuple(
                LeafEvidence(
                    visit=64,
                    fields=(LeafFieldState(field=longest_field, state=longest_state),)
                    * 2,
                )
                for _ in range(MAX_NODES)
            ),
        }
    )
    maximum = QueryFilterSummary.model_validate(raw)
    text = (
        "".join(maximum.signature)
        + ",".join(maximum.categories)
        + leaf_states_text(maximum)
    )
    assert len(text) + 1024 < MAX_FILTER_LOG_CHARS
    raw["signature"] = (longest_category,) * (3 * MAX_NODES)
    with pytest.raises(ValidationError, match="filter_signature_bound"):
        QueryFilterSummary.model_validate(raw)
    for tree in SOURCE_TREES:
        summary = unproven_filter_summary(tree)
        assert len("".join(summary.signature)) <= MAX_SIGNATURE_CHARS


@pytest.mark.parametrize(
    "field,value",
    [
        ("signature", ("private-string",)),
        (
            "leaf_states",
            ({"visit": 1, "fields": ({"field": "private-field", "state": "true"},)},),
        ),
        (
            "leaf_states",
            (
                {
                    "visit": 1,
                    "fields": ({"field": "construction", "state": "private-value"},),
                },
            ),
        ),
        (
            "leaf_states",
            (
                {
                    "visit": "private-id",
                    "fields": ({"field": "construction", "state": "true"},),
                },
            ),
        ),
    ],
)
def test_strict_projection_schema_cannot_contain_provider_strings(
    field: str, value: Any
) -> None:
    raw = unproven_filter_summary(SOURCE_TREES[0]).model_dump()
    raw[field] = value
    with pytest.raises(ValidationError) as caught:
        QueryFilterSummary.model_validate(raw)
    assert "private-" not in str(caught.value)


@pytest.mark.parametrize("position,key", QUERY_ROLES)
@pytest.mark.parametrize("tree", SOURCE_TREES)
def test_source_shaped_filters_never_gain_active_or_inactive_role_authority(
    position: int, key: str, tree: Any
) -> None:
    data = ui_inventory()
    param(data, position, key)["filter"] = deepcopy(tree)
    with pytest.raises(ShapeValidationError) as caught:
        ui_quantity_parameter(
            data["features"][position - 1], "depth" if position == 2 else "radius"
        )
    assert caught.value.failure.reason == "query_filter_unproven"
    assert caught.value.query_filter == unproven_filter_summary(tree)
    replacement_rejects(data, position)


@pytest.mark.parametrize("position,kind", OPERATIONS)
@pytest.mark.parametrize("tree", SOURCE_TREES)
def test_exact_historical_profile_still_rejects_every_filter(
    position: int, kind: str, tree: Any
) -> None:
    data = inventory()
    param(data, position, "entities")["filter"] = deepcopy(tree)
    operation = OP.validate_python(operation_for(kind, target(position).handle))
    with pytest.raises(EditError, match="unsupported_target"):
        change(data["features"], target(position), operation)
    assert metadata(data, position)["replacement"] == "unsupported_shape"


@pytest.mark.parametrize("position,kind", OPERATIONS)
@pytest.mark.parametrize(
    "effect", ["preserve", "remove", "subtype", "topology", "semantic", "add_to_target"]
)
def test_exact_verification_covers_every_filter_effect_without_accepting_target_filters(
    position: int, kind: str, effect: str
) -> None:
    data = ui_inventory()
    other = 5 - position
    query = param(data, other, "entities")
    query["filter"] = deepcopy(
        FIXTURES["extrude" if other == 2 else "fillet"]["filter"]
    )
    before = project_modify_evidence(REF, M0, data, config(), bodies())
    operation = OP.validate_python(operation_for(kind, target(position).handle))
    updated, preview = change(data["features"], target(position), operation)
    data["features"][position - 1] = updated
    if effect == "remove":
        del query["filter"]
    elif effect == "subtype":
        query["filter"]["btType"] = "BTOrFilter-167"
    elif effect == "topology":
        f = query["filter"]
        f["operand1"], f["operand2"] = f["operand2"], f["operand1"]
    elif effect == "semantic":
        leaf = query["filter"]
        while "operand1" in leaf:
            leaf = leaf["operand1"]
        field = "allowsFlattenedGeometry" if other == 2 else "isFromActiveSheetMetal"
        leaf[field] = not leaf[field]
    elif effect == "add_to_target":
        param(data, position, "entities")["filter"] = deepcopy(SOURCE_TREES[0])
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


def test_signature_logs_are_closed_guarded_and_add_zero_provider_reads(
    caplog: pytest.LogCaptureFixture,
) -> None:
    provider = Provider()
    provider.data = ui_inventory()
    for position in (2, 3):
        tree = deepcopy(SOURCE_TREES[position - 2])
        leaf = tree
        while "operand1" in leaf:
            leaf = leaf["operand1"]
        leaf["featureId"] = "private-feature-id"
        for key in tuple(leaf):
            if key != "btType":
                leaf[key] = "private-value\nreason=exact_match"
        param(provider.data, position, "entities")["filter"] = tree
    before = deepcopy(provider.data)
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
        if r.message.startswith("safe_edit_standard_shape_failure")
    ]
    assert len(lines) == 4
    for line in lines:
        assert "reason=query_filter_unproven" in line
        assert "signature=and(" in line and "signature_truncated=false" in line
        assert "leaf_states=" in line and len(line) < MAX_FILTER_LOG_CHARS
        assert "private-" not in line and "BT" not in line and "exact_match" not in line
    assert len(provider.calls) == 4 and all(
        call.method == "GET" for call in provider.calls
    )
    assert provider.writes == 0
    assert fingerprint(provider.data) == fingerprint(before)
