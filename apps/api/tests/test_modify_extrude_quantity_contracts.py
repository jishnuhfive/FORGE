"""Exact current ordinary Extrude quantity contracts; synthetic CAD only."""

from copy import deepcopy
from typing import Any

import pytest
from test_modify_current_query_contracts import current_inventory
from test_modify_representation import metadata
from test_modify_ui_conformance import param, replacement_rejects

from forge_api.integrations.onshape.dev.query_roles import query_role_inventory
from forge_api.integrations.onshape.dev.standard_shape_failure import diagnose_ui_shape
from forge_api.integrations.onshape.standard_edit_shapes import ui_quantity_parameter
from forge_api.integrations.onshape.standard_shape_contract import ShapeValidationError

ROLES = (
    "depth",
    "thickness",
    "thickness1",
    "thickness2",
    "draftAngle",
    "secondDirectionDepth",
    "secondDirectionDraftAngle",
    "offsetDistance",
    "secondDirectionOffsetDistance",
    "startOffsetDistance",
)
FIELDS = {
    "btType",
    "parameterId",
    "expression",
    "nodeId",
    "isInteger",
    "value",
    "units",
    "parameterName",
    "libraryRelationType",
}
EXPRESSIONS = {
    "depth": "20 mm",
    "thickness": "0.25 in",
    "thickness1": "0.25 in",
    "thickness2": "0 in",
    "draftAngle": "3 deg",
    "secondDirectionDepth": "1 in",
    "secondDirectionDraftAngle": "3 deg",
    "offsetDistance": "1 in",
    "secondDirectionOffsetDistance": "1 in",
    "startOffsetDistance": "1 in",
}


def rejects(
    data: dict[str, Any], parameter: str, reason: str = "wrong_quantity_expression"
) -> None:
    feature = data["features"][1]
    with pytest.raises(ShapeValidationError) as caught:
        ui_quantity_parameter(feature, "depth")
    assert caught.value.failure.model_dump() == {
        "parameter": parameter,
        "reason": reason,
    }
    report = diagnose_ui_shape(feature, "extrude")
    assert report.failure == caught.value.failure
    replacement_rejects(data, 2)


def test_complete_current_quantity_profile_is_exact_and_fillet_stays_exact() -> None:
    data = current_inventory()
    original = deepcopy(data)
    for role in ROLES:
        item = param(data, 2, role)
        assert set(item) == FIELDS
        assert item["expression"] == EXPRESSIONS[role]
        assert item["nodeId"]
        assert item["isInteger"] is False
        assert item["value"] == 0 and type(item["value"]) is int
        assert item["units"] == "" and item["parameterName"] == ""
        assert item["libraryRelationType"] == "DEFAULT"
    assert ui_quantity_parameter(data["features"][1], "depth")["parameterId"] == (
        "depth"
    )
    for position in (2, 3):
        report = metadata(data, position)
        assert report["parameter_shape_matches_registry"]
        assert report["replacement"] == report["rename"] == "exact_match"
    summaries = [report.summary for report in query_role_inventory(data)]
    assert [
        (summary.total_query_roles_discovered, summary.total_query_roles_inspected)
        for summary in summaries
    ] == [(13, 13), (8, 8)]
    assert all(
        summary.all_roles_inspected
        and not summary.any_malformed
        and not summary.any_unexpected_fields
        and not summary.any_uninspected
        and not summary.any_truncated
        for summary in summaries
    )
    assert data == original


@pytest.mark.parametrize(
    "expression",
    [
        "1 in",  # positive instead of zero
        "0.0 in",  # decimal instead of integer
        "0 mm",  # wrong units
        "+0 in",  # signed instead of unsigned
        "-0 in",
        "0 deg",  # wrong dimension
        "0e0 in",  # nonliteral/scientific
        "#configured",  # nonliteral/configured
        "0 in * 1",  # nonliteral/arithmetic
    ],
)
def test_thickness2_accepts_only_its_exact_zero_integer_unsigned_inch_literal(
    expression: str,
) -> None:
    data = current_inventory()
    param(data, 2, "thickness2")["expression"] = expression
    rejects(data, "thickness2")


@pytest.mark.parametrize("target", ["thickness", "thickness1"])
def test_thickness2_cannot_substitute_for_positive_decimal_thickness_roles(
    target: str,
) -> None:
    data = current_inventory()
    source = deepcopy(param(data, 2, "thickness2"))
    destination = param(data, 2, target)
    source["parameterId"] = target
    data["features"][1]["parameters"] = [
        source if item is destination else item
        for item in data["features"][1]["parameters"]
    ]
    rejects(data, target)


@pytest.mark.parametrize("source", ["thickness", "thickness1"])
def test_positive_decimal_thickness_roles_cannot_substitute_for_thickness2(
    source: str,
) -> None:
    data = current_inventory()
    replacement = deepcopy(param(data, 2, source))
    destination = param(data, 2, "thickness2")
    replacement["parameterId"] = "thickness2"
    data["features"][1]["parameters"] = [
        replacement if item is destination else item
        for item in data["features"][1]["parameters"]
    ]
    rejects(data, "thickness2")


def test_angle_role_cannot_substitute_for_length_role() -> None:
    data = current_inventory()
    replacement = deepcopy(param(data, 2, "draftAngle"))
    destination = param(data, 2, "secondDirectionDepth")
    replacement["parameterId"] = "secondDirectionDepth"
    data["features"][1]["parameters"] = [
        replacement if item is destination else item
        for item in data["features"][1]["parameters"]
    ]
    rejects(data, "secondDirectionDepth")


@pytest.mark.parametrize(
    "role,expression",
    [
        ("thickness", "1 in"),
        ("thickness1", "0.25 mm"),
        ("draftAngle", "3.0 deg"),
        ("draftAngle", "3 in"),
        ("secondDirectionDepth", "1.0 in"),
        ("secondDirectionDepth", "1 deg"),
        ("secondDirectionDraftAngle", "+3 deg"),
        ("offsetDistance", "0 in"),
        ("secondDirectionOffsetDistance", "1 mm"),
        ("startOffsetDistance", "#configured"),
    ],
)
def test_each_dormant_role_keeps_its_proven_expression_class(
    role: str, expression: str
) -> None:
    data = current_inventory()
    param(data, 2, role)["expression"] = expression
    rejects(data, role)


@pytest.mark.parametrize("expression", ["30 mm", "0.25 in", "393 in"])
def test_active_depth_keeps_the_existing_positive_length_authority(
    expression: str,
) -> None:
    data = current_inventory()
    param(data, 2, "depth")["expression"] = expression
    assert ui_quantity_parameter(data["features"][1], "depth")["expression"] == (
        expression
    )


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("btType", "BTMParameterString-149", "wrong_bt_type"),
        ("value", 1, "wrong_quantity_value"),
        ("value", False, "wrong_quantity_value"),
        ("units", "in", "wrong_quantity_units"),
        ("isInteger", True, "wrong_is_integer"),
        ("privateField", False, "unexpected_field"),
        ("valueString", "", "unexpected_field"),
        ("importMicroversion", "", "unexpected_field"),
    ],
)
@pytest.mark.parametrize("role", ROLES)
def test_current_quantity_envelope_rejects_wrong_type_state_or_extra_field(
    role: str, field: str, value: Any, reason: str
) -> None:
    data = current_inventory()
    param(data, 2, role)[field] = value
    rejects(data, role, reason)


@pytest.mark.parametrize(
    "field",
    ["nodeId", "isInteger", "value", "units", "parameterName", "libraryRelationType"],
)
@pytest.mark.parametrize("role", ROLES)
def test_current_quantity_envelope_requires_every_observed_field(
    role: str, field: str
) -> None:
    data = current_inventory()
    del param(data, 2, role)[field]
    rejects(data, role, "missing_required")


def test_duplicate_and_malformed_quantity_parameters_fail_closed() -> None:
    data = current_inventory()
    data["features"][1]["parameters"][-1] = deepcopy(param(data, 2, "thickness2"))
    rejects(data, "duplicate_parameter", "duplicate_parameter")

    data = current_inventory()
    parameters = data["features"][1]["parameters"]
    index = parameters.index(param(data, 2, "thickness2"))
    parameters[index] = "malformed-quantity"
    rejects(data, "parameters", "wrong_bt_type")
