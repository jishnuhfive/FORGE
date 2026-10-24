"""Phase 16 UI contracts: invented identifiers/queries, mock CAD transport only."""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from conftest import Harness
from test_cad_read import REF
from test_modify_conformance import (
    EDITS,
    UnverifiableProvider,
    operation_for,
    plan_for,
    rejected_replacement,
)
from test_modify_plan import (
    OP,
    PlanProvider,
    _no_dispatch,
    approve,
    discover,
    inventory,
    target,
)
from test_modify_representation import known, metadata
from test_safe_edit import M0, bodies, config, running

from forge_api.cad_edits import plan_service
from forge_api.cad_edits.domain import EditError, fingerprint
from forge_api.cad_edits.plans import ResolvedOperation, SemanticPlan
from forge_api.integrations.onshape.dev.standard_parameters import (
    standard_parameter_coverage,
)
from forge_api.integrations.onshape.edit_registry import change, quantity_parameter
from forge_api.integrations.onshape.modify_evidence import (
    project_modify_evidence,
    verify_operation,
)
from forge_api.integrations.onshape.service import ReadGate

PARAMETERS = json.loads(
    (Path(__file__).parent / "fixtures/modify_ui_parameters.json").read_text()
)
CASES = [
    (position, p["parameterId"])
    for position, category in ((2, "extrude"), (3, "fillet"))
    for p in PARAMETERS[category]
]
REQUIRED = {
    2: {
        "bodyType",
        "operationType",
        "entities",
        "endBound",
        "depth",
        "domain",
        "oppositeDirection",
        "symmetric",
        "hasDraft",
        "hasSecondDirection",
        "hasSecondDirectionDraft",
        "hasOffset",
        "hasSecondDirectionOffset",
        "hasExtrudeDirection",
        "startOffset",
        "defaultScope",
        "defaultSurfaceScope",
    },
    3: {
        "entities",
        "radius",
        "tangentPropagation",
        "filletType",
        "blendControlType",
        "crossSection",
        "isAsymmetric",
        "isPartial",
        "isVariable",
        "smoothTransition",
        "allowEdgeOverflow",
        "keepEdges",
        "smoothCorners",
        "smoothCornerExceptions",
        "vertexSettings",
        "pointOnEdgeSettings",
    },
}
QUANTITIES = [
    (position, key)
    for position, key in CASES
    if next(
        p
        for p in PARAMETERS["extrude" if position == 2 else "fillet"]
        if p["parameterId"] == key
    )["btType"]
    == "BTMParameterQuantity-147"
]


def ui_inventory() -> dict[str, Any]:
    data = inventory()
    for feature in data["features"]:
        if feature["featureType"] in PARAMETERS:
            feature["parameters"] = deepcopy(PARAMETERS[feature["featureType"]])
    return data


def param(data: dict[str, Any], position: int, key: str) -> dict[str, Any]:
    return next(
        p
        for p in data["features"][position - 1]["parameters"]
        if p["parameterId"] == key
    )


def parameters(feature: dict[str, Any]) -> list[dict[str, Any]]:
    values = feature["parameters"]
    assert isinstance(values, list) and all(isinstance(p, dict) for p in values)
    return values


def replacement_rejects(data: dict[str, Any], position: int) -> None:
    for kind in (
        "RENAME_FEATURE",
        "SET_EXTRUDE_DEPTH" if position == 2 else "SET_FILLET_RADIUS",
    ):
        operation = OP.validate_python(operation_for(kind, target(position).handle))
        with pytest.raises(EditError, match="unsupported_target"):
            change(data["features"], target(position), operation)
    result = metadata(data, position)
    assert result["replacement"] == result["rename"] == "unsupported_shape"


@pytest.mark.parametrize("position,kind", EDITS)
def test_ui_operations_copy_complete_definition_and_change_only_authorized_field(
    position: int, kind: str
) -> None:
    data = ui_inventory()
    if kind == "SET_UNSUPPRESSED":
        data["features"][-1]["suppressed"] = True
    original = deepcopy(data)
    operation = OP.validate_python(operation_for(kind, target(position).handle))
    updated, _ = change(data["features"], target(position), operation)
    expected = deepcopy(original["features"][position - 1])
    if kind == "RENAME_FEATURE":
        expected["name"] = "Conformance renamed"
    elif kind in ("SET_SUPPRESSED", "SET_UNSUPPRESSED"):
        expected["suppressed"] = kind == "SET_SUPPRESSED"
    else:
        key = "depth" if position == 2 else "radius"
        next(p for p in expected["parameters"] if p["parameterId"] == key)[
            "expression"
        ] = "25 mm" if position == 2 else "3 mm"
    assert fingerprint(updated) == fingerprint(expected)
    assert data == original
    assert [p["parameterId"] for p in parameters(updated)] == [
        p["parameterId"] for p in expected["parameters"]
    ]


@pytest.mark.parametrize("position", [2, 3])
def test_full_ui_contract_is_exact_in_both_sanitized_reports(position: int) -> None:
    data = ui_inventory()
    original = deepcopy(data)
    result = metadata(data, position)
    assert result["parameter_shape_matches_registry"]
    assert result["replacement"] == result["rename"] == "exact_match"
    assert not result["unknown_present"] and result["unknown_count"] == 0
    assert not result["unknown_count_capped"]
    assert (
        not result["malformed_parameter_present"]
        and not result["duplicate_known_present"]
    )
    # Diagnostic clipping is informative; actual validation checks every input.
    assert result["parameter_count"] == 20 and result["parameter_count_capped"]
    assert known(result, "depth" if position == 2 else "radius")["quantity"][
        "supported_fields_only"
    ]
    source = standard_parameter_coverage(data, source_matches=True).positions[
        position - 1
    ]
    assert (
        not source.unrecognized_present
        and not source.malformed_present
        and not source.duplicate_present
    )
    assert len(source.parameters) == (50 if position == 2 else 38)
    assert data == original


@pytest.mark.parametrize("position,key", CASES)
@pytest.mark.parametrize(
    "case", ["wrong_bt", "missing_value", "duplicate", "configured", "unknown_field"]
)
def test_every_ui_parameter_is_typed_explicit_unique_and_closed(
    position: int, key: str, case: str
) -> None:
    data = ui_inventory()
    item = param(data, position, key)
    if case == "wrong_bt":
        item["btType"] = "BTMParameterString-149"
    elif case == "missing_value":
        field = (
            "expression"
            if "expression" in item
            else "queries"
            if "queries" in item
            else "items"
            if "items" in item
            else "value"
        )
        del item[field]
    elif case == "duplicate":
        data["features"][position - 1]["parameters"].append(deepcopy(item))
    elif case == "configured":
        item["configuration"] = {"synthetic": True}
    else:
        item["unprovenOption"] = False
    replacement_rejects(data, position)


@pytest.mark.parametrize(
    "position,key", [(p, key) for p in REQUIRED for key in sorted(REQUIRED[p])]
)
def test_missing_mode_guard_never_infers_its_source_default(
    position: int, key: str
) -> None:
    data = ui_inventory()
    data["features"][position - 1]["parameters"].remove(param(data, position, key))
    replacement_rejects(data, position)


@pytest.mark.parametrize(
    "position,key", [(p, key) for p, key in CASES if key not in REQUIRED[p]]
)
def test_absent_inactive_input_requires_all_explicit_mode_guards(
    position: int, key: str
) -> None:
    data = ui_inventory()
    data["features"][position - 1]["parameters"].remove(param(data, position, key))
    operation = OP.validate_python(
        operation_for("RENAME_FEATURE", target(position).handle)
    )
    updated, _ = change(data["features"], target(position), operation)
    expected = deepcopy(data["features"][position - 1])
    expected["name"] = "Conformance renamed"
    assert updated == expected


@pytest.mark.parametrize(
    "position,key",
    [
        (p, key)
        for p, key in CASES
        if next(
            i
            for i in PARAMETERS["extrude" if p == 2 else "fillet"]
            if i["parameterId"] == key
        )["btType"]
        in ("BTMParameterBoolean-144", "BTMParameterEnum-145")
        and key not in ("defaultsChanged", "tangentPropagation")
    ],
)
def test_one_mode_value_change_cannot_enable_a_richer_shape(
    position: int, key: str
) -> None:
    data = ui_inventory()
    item = param(data, position, key)
    item["value"] = not item["value"] if type(item["value"]) is bool else "UNSUPPORTED"
    replacement_rejects(data, position)


@pytest.mark.parametrize("key", ["defaultsChanged", "tangentPropagation"])
@pytest.mark.parametrize("value", [False, True])
def test_two_explicit_boolean_states_are_preserved_for_documented_fillet_options(
    key: str, value: bool
) -> None:
    data = ui_inventory()
    param(data, 3, key)["value"] = value
    quantity_parameter(data["features"][2], "SET_FILLET_RADIUS")
    operation = OP.validate_python(operation_for("RENAME_FEATURE", target().handle))
    updated, _ = change(data["features"], target(), operation)
    assert (
        next(p for p in parameters(updated) if p["parameterId"] == key)["value"]
        is value
    )


@pytest.mark.parametrize("position,key", QUANTITIES)
@pytest.mark.parametrize(
    "field,value",
    [
        ("value", 1),
        ("value", False),
        ("units", "m"),
        ("isInteger", True),
        ("importMicroversion", "synthetic-reference"),
        ("tolerance", {}),
        ("expression", "#configured"),
        ("expression", "1e2 mm"),
        ("expression", None),
    ],
)
def test_every_quantity_rejects_cached_values_units_tolerance_and_expressions(
    position: int, key: str, field: str, value: Any
) -> None:
    data = ui_inventory()
    param(data, position, key)[field] = value
    replacement_rejects(data, position)


@pytest.mark.parametrize(
    "position,key",
    [
        (p, key)
        for p, key in CASES
        if next(
            i
            for i in PARAMETERS["extrude" if p == 2 else "fillet"]
            if i["parameterId"] == key
        )["btType"]
        in ("BTMParameterQueryList-148", "BTMParameterArray-2025")
        and key != "entities"
    ],
)
@pytest.mark.parametrize("value", [None, {}, ["synthetic-active-input"]])
def test_inactive_queries_and_variable_arrays_must_be_explicitly_empty(
    position: int, key: str, value: Any
) -> None:
    data = ui_inventory()
    item = param(data, position, key)
    item["items" if "items" in item else "queries"] = value
    replacement_rejects(data, position)


@pytest.mark.parametrize("position", [2, 3])
@pytest.mark.parametrize(
    "queries",
    [
        [],
        [None],
        [{}],
        [{"btType": "BTMOtherQuery-999"}],
        [{"btType": "BTMIndividualQuery-138", "queryString": 1}],
        [{"btType": "BTMIndividualQuery-138", "deterministicIds": [None]}],
        [
            {
                "btType": "BTMIndividualQuery-138",
                "queryString": "q",
                "persistentQuery": {},
            }
        ],
    ],
)
def test_ordinary_entity_query_envelope_and_items_fail_closed(
    position: int, queries: Any
) -> None:
    data = ui_inventory()
    param(data, position, "entities")["queries"] = deepcopy(queries)
    replacement_rejects(data, position)


@pytest.mark.parametrize("position", [2, 3])
@pytest.mark.parametrize(
    "key", ["unknownParameter", "createDetachedSurface", None, 1, [], {}]
)
def test_unknown_or_malformed_parameter_identity_fails_closed(
    position: int, key: Any
) -> None:
    data = ui_inventory()
    # Keep the original count below the finite limit so rejection must inspect
    # the unknown/malformed identity, rather than relying on a length check.
    param(data, position, "wallShape" if position == 2 else "side1Face")[
        "parameterId"
    ] = key
    replacement_rejects(data, position)


@pytest.mark.parametrize("position", [2, 3])
def test_sketch_region_queries_are_only_a_supported_extrude_selection(
    position: int,
) -> None:
    data = ui_inventory()
    param(data, position, "entities")["queries"] = [
        {
            "btType": "BTMIndividualSketchRegionQuery-140",
            "featureId": "synthetic-sketch",
            "filterInnerLoops": False,
            "nodeId": "synthetic-query-node",
        }
    ]
    if position == 3:
        replacement_rejects(data, position)
    else:
        operation = OP.validate_python(
            operation_for("RENAME_FEATURE", target(position).handle)
        )
        updated, _ = change(data["features"], target(position), operation)
        assert next(
            p for p in parameters(updated) if p["parameterId"] == "entities"
        ) == param(data, position, "entities")


@pytest.mark.parametrize("position", [2, 3])
def test_known_empty_metadata_and_zero_bookkeeping_are_preserved_exactly(
    position: int,
) -> None:
    data = ui_inventory()
    for item in data["features"][position - 1]["parameters"]:
        item["importMicroversion"] = ""
        if item["btType"] == "BTMParameterEnum-145":
            item["namespace"] = ""
        if item["btType"] == "BTMParameterQuantity-147":
            item["value"] = 0.0
    expected = deepcopy(data["features"][position - 1])
    expected["name"] = "Conformance renamed"
    operation = OP.validate_python(
        operation_for("RENAME_FEATURE", target(position).handle)
    )
    updated, _ = change(data["features"], target(position), operation)
    assert fingerprint(updated) == fingerprint(expected)


@pytest.mark.parametrize("position,key", CASES)
def test_fresh_post_read_rejects_node_change_on_every_parameter(
    position: int, key: str
) -> None:
    data = ui_inventory()
    before = project_modify_evidence(REF, M0, data, config(), bodies())
    operation = OP.validate_python(
        operation_for("RENAME_FEATURE", target(position).handle)
    )
    updated, preview = change(data["features"], target(position), operation)
    resolved = ResolvedOperation(
        operation=operation, target=target(position), preview=preview
    )
    data["features"][position - 1] = updated
    marker = "e" * 24
    data["sourceMicroversion"] = marker
    param(data, position, key)["nodeId"] = "synthetic-other-node"
    after = project_modify_evidence(REF, marker, data, config(marker), bodies(marker))
    with pytest.raises(EditError, match="verification_failed"):
        verify_operation(before, after, resolved, marker)


@pytest.mark.parametrize("position", [2, 3])
@pytest.mark.parametrize(
    "case", ["dormant_value", "parameter_order", "query_content", "metadata"]
)
def test_other_structurally_valid_provider_changes_cannot_verify(
    position: int, case: str
) -> None:
    data = ui_inventory()
    before = project_modify_evidence(REF, M0, data, config(), bodies())
    operation = OP.validate_python(
        operation_for("RENAME_FEATURE", target(position).handle)
    )
    updated, preview = change(data["features"], target(position), operation)
    data["features"][position - 1] = updated
    if case == "dormant_value":
        param(data, position, "thickness" if position == 2 else "otherRadius")[
            "expression"
        ] = "7 mm"
    elif case == "parameter_order":
        data["features"][position - 1]["parameters"].reverse()
    elif case == "query_content":
        param(data, position, "entities")["queries"][0]["queryString"] = (
            "synthetic-other-query"
        )
    else:
        updated["extraMetadata"] = {"synthetic": True}
    assert metadata(data, position)["replacement"] == "exact_match"
    marker = "e" * 24
    data["sourceMicroversion"] = marker
    after = project_modify_evidence(REF, marker, data, config(marker), bodies(marker))
    with pytest.raises(EditError, match="verification_failed"):
        verify_operation(
            before,
            after,
            ResolvedOperation(
                operation=operation, target=target(position), preview=preview
            ),
            marker,
        )


@pytest.mark.parametrize(
    "position,key,expression",
    [
        (2, "draftAngle", "0 deg"),
        (2, "draftAngle", "90 deg"),
        (2, "draftAngle", "3 rad"),
        (2, "startOffsetDistance", "-1 mm"),
        (3, "rho", "0"),
        (3, "magnitude", "1"),
        (3, "partialFirstEdgeTotalParameter", "2"),
        (3, "partialSecondEdgeTotalParameter", "0.5 mm"),
    ],
)
def test_inactive_quantity_dimensions_and_ranges_are_still_closed(
    position: int, key: str, expression: str
) -> None:
    data = ui_inventory()
    param(data, position, key)["expression"] = expression
    replacement_rejects(data, position)


@pytest.mark.parametrize("position", [2, 3])
@pytest.mark.parametrize("value", [None, 0, "false"])
def test_boolean_mode_cannot_use_coercion(position: int, value: Any) -> None:
    data = ui_inventory()
    param(data, position, "hasDraft" if position == 2 else "isVariable")["value"] = (
        value
    )
    replacement_rejects(data, position)


@pytest.mark.parametrize("position", [2, 3])
def test_full_ui_feature_still_obeys_original_payload_cap(
    harness: Harness, position: int
) -> None:
    provider = PlanProvider()
    provider.data = ui_inventory()
    provider.data["features"][position - 1]["syntheticMetadata"] = "x" * 8192
    with running(harness, provider):
        req, preview = plan_for(harness, position, "RENAME_FEATURE")
        result = approve(harness, req, preview)
        assert result.state == "write_failed" and result.operations == ("write_failed",)
        _no_dispatch(harness, provider)


@pytest.mark.parametrize("position,kind", EDITS)
def test_real_ui_shapes_cancel_then_approve_once_and_verify_exactly(
    harness: Harness, position: int, kind: str
) -> None:
    provider = PlanProvider()
    provider.data = ui_inventory()
    if kind == "SET_UNSUPPRESSED":
        provider.data["features"][-1]["suppressed"] = True
        provider.data["featureStates"]["synthetic-feature-2"]["inactive"] = True
    original = deepcopy(provider.data)
    with running(harness, provider):
        req, preview = plan_for(harness, position, kind)
        assert (
            plan_service.cancel(req, harness.runtime, preview.proposal_id).state
            == "cancelled"
        )
        _no_dispatch(harness, provider)
        assert provider.data == original
        req, preview = plan_for(harness, position, kind)
        operation = OP.validate_python(operation_for(kind, target(position).handle))
        expected, _ = change(original["features"], target(position), operation)
        result = approve(harness, req, preview)
        assert result.state == "verified_success" and provider.writes == 1
        assert fingerprint(provider.data["features"][position - 1]) == fingerprint(
            expected
        )
        if kind not in ("SET_SUPPRESSED", "SET_UNSUPPRESSED"):
            assert provider.payloads[0]["feature"] == expected
        with pytest.raises(EditError, match="proposal_used"):
            approve(harness, req, preview)
        assert provider.writes == 1


@pytest.mark.parametrize("position", [2, 3])
def test_ui_stale_optional_value_rejects_before_dispatch(
    harness: Harness, position: int
) -> None:
    provider = PlanProvider()
    provider.data = ui_inventory()
    with running(harness, provider):
        req, preview = plan_for(harness, position, "RENAME_FEATURE")
        key = "thickness" if position == 2 else "otherRadius"
        param(provider.data, position, key)["expression"] = "7 mm"
        result = approve(harness, req, preview)
        assert result.state == "rejected_stale"
        assert result.operations == ("rejected_stale",)
        assert provider.writes == 0


@pytest.mark.parametrize(
    "position,key",
    [
        (2, "hasExtrudeDirection"),
        (2, "hasSecondDirection"),
        (2, "startOffset"),
        (3, "isVariable"),
        (3, "smoothCorners"),
        (3, "allowEdgeOverflow"),
    ],
)
def test_richer_ui_shapes_are_not_discovered_as_replacement_targets(
    harness: Harness, position: int, key: str
) -> None:
    provider = PlanProvider()
    provider.data = ui_inventory()
    item = param(provider.data, position, key)
    item["value"] = not item["value"]
    rejected_replacement(harness, provider, position)


@pytest.mark.parametrize("position,kind", EDITS)
@pytest.mark.parametrize(
    "fault",
    [
        "ack_missing_revision",
        "ack_unchanged_revision",
        "ack_missing_skew",
        "ack_wrong_identity",
        "post_read_incomplete",
        "post_read_unrelated_change",
        "post_read_missing",
    ],
)
def test_ui_dispatch_uncertainty_stops_suffix_and_retry(
    harness: Harness, position: int, kind: str, fault: str
) -> None:
    provider = UnverifiableProvider(kind, fault)
    saved_state = provider.data["features"][-1]["suppressed"]
    provider.data = ui_inventory()
    provider.data["features"][-1]["suppressed"] = saved_state
    provider.data["featureStates"]["synthetic-feature-2"]["inactive"] = saved_state
    with running(harness, provider):
        req, catalog = discover(harness)
        option = next(t for t in catalog.targets if t.position == position)
        other = next(t for t in catalog.targets if t.position != position)
        req.app.state.cad_gate = ReadGate()
        preview = plan_service.prepare(
            req,
            harness.runtime,
            SemanticPlan.model_validate_json(
                json.dumps(
                    {
                        "target_catalog": catalog.target_catalog,
                        "operations": [
                            operation_for(kind, option.handle),
                            operation_for("RENAME_FEATURE", other.handle),
                        ],
                    }
                )
            ),
        )
        result = approve(harness, req, preview)
        assert result.state == "execution_uncertain"
        assert result.operations == ("execution_uncertain", "skipped")
        assert provider.writes == 1
        with pytest.raises(EditError, match="proposal_used"):
            approve(harness, req, preview)
        with pytest.raises(EditError, match="workspace_fenced"):
            discover(harness)
        assert provider.writes == 1
