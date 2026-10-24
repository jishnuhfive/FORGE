"""Every closed current-UI rejection, shared predicates, private GET-only logs."""

import json
import logging
from copy import deepcopy
from typing import Any, get_args

import httpx2 as httpx
import pytest
from pydantic import ValidationError
from test_cad_read import REF
from test_modify_representation import enabled_settings, metadata
from test_modify_ui_conformance import param, ui_inventory
from test_safe_edit import M1, Provider

from forge_api.cad_edits.domain import EditError
from forge_api.integrations.onshape.dev import safe_edit
from forge_api.integrations.onshape.dev.standard_shape_failure import (
    diagnose_ui_shape,
    shape_validation_coverage,
)
from forge_api.integrations.onshape.standard_edit_shapes import ui_quantity_parameter
from forge_api.integrations.onshape.standard_shape_contract import (
    FailureReason,
    ShapeFailure,
    ShapeValidationError,
)

# Static expected cases, not a second implementation of eligibility predicates.
FAILURES = [
    ("feature_type", 2, "feature", "wrong_bt_type"),
    ("parameters_type", 2, "parameters", "missing_required"),
    ("parameters_empty", 2, "parameters", "missing_required"),
    ("parameters_count", 2, "parameters", "too_many_parameters"),
    ("parameter_type", 2, "parameters", "wrong_bt_type"),
    ("unknown_id", 2, "unknown_parameter", "unknown_parameter"),
    ("malformed_id", 2, "unknown_parameter", "unknown_parameter"),
    ("duplicate", 2, "duplicate_parameter", "duplicate_parameter"),
    ("missing_guard", 2, "defaultScope", "missing_required"),
    ("bt_type", 3, "radius", "wrong_bt_type"),
    ("node", 3, "radius", "bookkeeping_node_id"),
    ("node_empty", 3, "radius", "bookkeeping_node_id"),
    ("node_long", 3, "radius", "bookkeeping_node_id"),
    ("import", 3, "radius", "bookkeeping_import_microversion"),
    ("quantity_extra", 3, "radius", "unexpected_field"),
    ("integer", 3, "radius", "wrong_is_integer"),
    ("value", 3, "radius", "wrong_quantity_value"),
    ("value_boolean", 3, "radius", "wrong_quantity_value"),
    ("units", 3, "radius", "wrong_quantity_units"),
    ("expression_type", 3, "radius", "wrong_quantity_expression"),
    ("expression", 3, "radius", "wrong_quantity_expression"),
    ("length_bounds", 3, "radius", "wrong_quantity_expression"),
    ("offset_expression", 2, "startOffsetDistance", "wrong_quantity_expression"),
    ("angle_expression", 2, "draftAngle", "wrong_quantity_expression"),
    ("angle_bounds", 2, "draftAngle", "wrong_quantity_expression"),
    (
        "fraction_bounds",
        3,
        "partialFirstEdgeTotalParameter",
        "wrong_quantity_expression",
    ),
    ("open_fraction_bounds", 3, "rho", "wrong_quantity_expression"),
    ("boolean_extra", 2, "hasDraft", "unexpected_field"),
    ("boolean", 2, "hasDraft", "wrong_boolean"),
    ("boolean_type", 2, "hasDraft", "wrong_boolean"),
    ("enum_extra", 2, "bodyType", "unexpected_field"),
    ("enum_namespace", 2, "bodyType", "wrong_enum_namespace"),
    ("enum_name", 2, "bodyType", "wrong_enum_name"),
    ("enum_value", 2, "bodyType", "wrong_enum_value"),
    ("query_extra", 3, "entities", "unexpected_field"),
    ("query_filter", 3, "entities", "query_filter_unproven"),
    ("query_envelope", 3, "entities", "query_wrong_envelope"),
    ("query_empty", 3, "entities", "query_empty"),
    ("query_count", 3, "entities", "query_wrong_envelope"),
    ("inactive_query", 2, "extrudeDirection", "query_nonempty"),
    ("array_extra", 3, "vertexSettings", "unexpected_field"),
    ("array_type", 3, "vertexSettings", "array_not_empty"),
    ("array_nonempty", 3, "vertexSettings", "array_not_empty"),
    ("item_type", 3, "entities", "query_item_wrong_type"),
    ("item_bt", 3, "entities", "query_item_wrong_type"),
    ("item_region", 3, "entities", "query_item_wrong_type"),
    ("item_extra", 3, "entities", "query_item_unexpected_field"),
    ("item_wrapper", 3, "entities", "query_item_unexpected_field"),
    ("item_node", 3, "entities", "query_item_bookkeeping"),
    ("item_import", 3, "entities", "query_item_bookkeeping"),
    ("item_query_type", 3, "entities", "query_item_identity"),
    ("item_query_length", 3, "entities", "query_item_identity"),
    ("item_ids_type", 3, "entities", "query_item_identity"),
    ("item_ids_count", 3, "entities", "query_item_identity"),
    ("item_id_type", 3, "entities", "query_item_identity"),
    ("item_id_empty", 3, "entities", "query_item_identity"),
    ("item_id_length", 3, "entities", "query_item_identity"),
    ("item_no_identity", 3, "entities", "query_item_identity"),
    ("region_no_identity", 2, "entities", "query_item_identity"),
    ("region_filter", 2, "entities", "query_item_identity"),
]


def broken(case: str, position: int, parameter: str) -> dict[str, Any]:
    data = ui_inventory()
    feature = data["features"][position - 1]
    parameters = feature["parameters"]
    if case == "feature_type":
        feature["featureType"] = "private-type"
    elif case == "parameters_type":
        feature["parameters"] = None
    elif case == "parameters_empty":
        feature["parameters"] = []
    elif case == "parameters_count":
        parameters.append({"parameterId": "private-extra"})
    elif case == "parameter_type":
        parameters[0] = "private-object"
    elif case in ("unknown_id", "malformed_id"):
        param(data, position, "wallShape")["parameterId"] = (
            "private-id" if case == "unknown_id" else ["private-id"]
        )
    elif case == "duplicate":
        parameters[-1] = deepcopy(parameters[0])
    elif case == "missing_guard":
        parameters.remove(param(data, position, "defaultScope"))
    else:
        item = param(data, position, parameter)
        changes: dict[str, tuple[str, Any]] = {
            "bt_type": ("btType", "private-provider-type"),
            "node": ("nodeId", ["private-node"]),
            "node_empty": ("nodeId", ""),
            "node_long": ("nodeId", "private-" * 100),
            "import": ("importMicroversion", "private-microversion"),
            "quantity_extra": ("private-field", "private-value"),
            "integer": ("isInteger", True),
            "value": ("value", 123.456789),
            "value_boolean": ("value", False),
            "units": ("units", "private-units"),
            "expression_type": ("expression", ["private-expression"]),
            "expression": ("expression", "#private-expression"),
            "length_bounds": ("expression", "10001 mm"),
            "offset_expression": ("expression", "-1 mm"),
            "angle_expression": ("expression", "3 rad"),
            "angle_bounds": ("expression", "90 deg"),
            "fraction_bounds": ("expression", "2"),
            "open_fraction_bounds": ("expression", "0"),
            "boolean_extra": ("private-field", "private-value"),
            "boolean": ("value", True),
            "boolean_type": ("value", 0),
            "enum_extra": ("private-field", "private-value"),
            "enum_namespace": ("namespace", "private-namespace"),
            "enum_name": ("enumName", "private-enum"),
            "enum_value": ("value", "private-enum-value"),
            "query_extra": ("private-field", "private-value"),
            "query_filter": (
                "filter",
                {"btType": "BTEntityTypeFilter-124", "entityType": "private-value"},
            ),
            "query_envelope": ("queries", None),
            "query_empty": ("queries", []),
            "query_count": ("queries", [{}] * 2001),
            "inactive_query": ("queries", ["private-query"]),
            "array_extra": ("private-field", "private-value"),
            "array_type": ("items", None),
            "array_nonempty": ("items", ["private-setting"]),
        }
        if case in changes:
            field, value = changes[case]
            item[field] = value
        else:
            query = item["queries"][0]
            if case == "item_type":
                item["queries"] = ["private-query"]
            elif case == "item_bt":
                query["btType"] = "private-type"
            elif case in ("item_region", "region_no_identity", "region_filter"):
                query["btType"] = "BTMIndividualSketchRegionQuery-140"
                if case == "region_filter":
                    query.update(
                        featureId="private-feature", filterInnerLoops="private-filter"
                    )
            elif case == "item_extra":
                query["private-field"] = "private-value"
            elif case == "item_wrapper":
                query["persistentQuery"] = {"private-field": "private-value"}
            elif case == "item_node":
                query["nodeId"] = ["private-node"]
            elif case == "item_import":
                query["importMicroversion"] = "private-microversion"
            elif case == "item_query_type":
                query["queryString"] = ["private-query"]
            elif case == "item_query_length":
                query["queryString"] = "private-query" * 1000
            elif case.startswith("item_id"):
                query["deterministicIds"] = {
                    "item_ids_type": "private-id",
                    "item_ids_count": ["private-id"] * 2001,
                    "item_id_type": [None],
                    "item_id_empty": [""],
                    "item_id_length": ["private-id" * 100],
                }[case]
            elif case == "item_no_identity":
                query["queryString"] = ""
            else:
                raise AssertionError("unhandled synthetic case")
    return data


@pytest.mark.parametrize("case,position,parameter,reason", FAILURES)
def test_every_failure_uses_the_production_predicate_and_one_closed_reason(
    case: str,
    position: int,
    parameter: str,
    reason: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    data = broken(case, position, parameter)
    feature = data["features"][position - 1]
    original = deepcopy(feature)
    with pytest.raises(EditError) as caught:
        ui_quantity_parameter(feature, "depth" if position == 2 else "radius")
    assert isinstance(caught.value, ShapeValidationError)
    assert caught.value.code == "unsupported_target" and caught.value.status == 422
    assert str(caught.value) == "unsupported_target"
    report = diagnose_ui_shape(feature, "extrude" if position == 2 else "fillet")
    assert report.failure == caught.value.failure
    assert report.failure is not None
    assert report.failure.model_dump() == {"parameter": parameter, "reason": reason}
    assert "private-" not in report.model_dump_json()
    assert feature == original
    provider = Provider()
    provider.data = data
    with (
        httpx.Client(transport=httpx.MockTransport(provider.handle)) as transport,
        caplog.at_level(logging.WARNING),
    ):
        safe_edit.CoverageClient(
            enabled_settings(), transport, "private-token"
        ).compare(REF)
    assert "private-" not in caplog.text and "123.456789" not in caplog.text
    assert len(provider.calls) == 4 and all(c.method == "GET" for c in provider.calls)
    assert provider.writes == 0


def test_reason_matrix_covers_the_entire_closed_vocabulary() -> None:
    assert {case[3] for case in FAILURES} == set(get_args(FailureReason))


def test_unknown_requested_parameter_is_never_reflected_in_failure() -> None:
    with pytest.raises(ShapeValidationError) as caught:
        ui_quantity_parameter(ui_inventory()["features"][1], "private-request")
    assert caught.value.failure.model_dump() == {
        "parameter": "required_parameter",
        "reason": "missing_required",
    }


@pytest.mark.parametrize("position", [2, 3])
def test_valid_current_ui_shape_has_identical_success_without_modifying_input(
    position: int,
) -> None:
    feature = ui_inventory()["features"][position - 1]
    original = deepcopy(feature)
    key = "depth" if position == 2 else "radius"
    assert ui_quantity_parameter(feature, key)["parameterId"] == key
    assert (
        diagnose_ui_shape(feature, "extrude" if position == 2 else "fillet").failure
        is None
    )
    assert feature == original


def test_observed_false_scope_is_closed_and_still_requires_new_solid_empty_scope() -> (
    None
):
    data = ui_inventory()
    assert param(data, 2, "defaultScope")["value"] is False
    assert metadata(data, 2)["replacement"] == "exact_match"
    for key, field, value in [
        ("defaultScope", "value", True),
        ("operationType", "value", "ADD"),
        ("bodyType", "value", "SURFACE"),
        ("booleanScope", "queries", [{}]),
    ]:
        bad = deepcopy(data)
        param(bad, 2, key)[field] = value
        assert diagnose_ui_shape(bad["features"][1], "extrude").failure is not None
        assert metadata(bad, 2)["replacement"] == "unsupported_shape"


def test_first_failure_is_deterministic_in_parameter_and_predicate_order() -> None:
    data = broken("expression", 2, "depth")
    param(data, 2, "hasDraft")["value"] = True
    failure = diagnose_ui_shape(data["features"][1], "extrude").failure
    assert (
        failure
        and failure.parameter == "depth"
        and failure.reason == "wrong_quantity_expression"
    )
    data["features"][1]["parameters"].reverse()
    failure = diagnose_ui_shape(data["features"][1], "extrude").failure
    assert (
        failure
        and failure.parameter == "hasDraft"
        and failure.reason == "wrong_boolean"
    )
    param(data, 2, "hasDraft").update(btType="private-type", nodeId=None)
    failure = diagnose_ui_shape(data["features"][1], "extrude").failure
    assert failure and failure.reason == "wrong_bt_type"


def shape_lines(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [
        r.message
        for r in caplog.records
        if r.message.startswith("safe_edit_standard_shape_")
    ]


def test_only_closed_failure_or_success_lines_escape_without_extra_reads(
    caplog: pytest.LogCaptureFixture,
) -> None:
    provider = Provider()
    provider.data = broken("units", 3, "radius")
    for feature in provider.data["features"]:
        feature.update(
            name="private-name",
            featureId="private-feature",
            raw={"token": "private-token", "coordinate": 123.456789},
        )
    original = deepcopy(provider.data)
    with (
        httpx.Client(transport=httpx.MockTransport(provider.handle)) as transport,
        caplog.at_level(logging.WARNING),
    ):
        safe_edit.CoverageClient(
            enabled_settings(), transport, "private-token"
        ).compare(REF)
    assert (
        shape_lines(caplog)
        == [
            "safe_edit_standard_shape_validation category=extrude outcome=exact_match",
            "safe_edit_standard_shape_failure category=fillet "
            "parameter=radius reason=wrong_quantity_units",
        ]
        * 2
    )
    for private in (
        "private-",
        "123.456789",
        REF.documentId,
        REF.workspaceId,
        REF.elementId,
        provider.marker,
        "https://",
    ):
        assert private not in caplog.text
    assert len(provider.calls) == 4 and all(c.method == "GET" for c in provider.calls)
    assert provider.writes == 0 and provider.data == original


@pytest.mark.parametrize(
    "enabled,environment,writes",
    [
        (False, "development", False),
        (True, "production", False),
        (True, "test", False),
        (True, "development", True),
    ],
)
def test_guards_block_projection_before_any_work(
    enabled: bool, environment: Any, writes: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = enabled_settings()
    settings.forge_safe_edit_diagnostics_enabled = enabled
    settings.environment = environment
    settings.forge_cad_writes_enabled = writes

    def forbidden(*_: Any, **__: Any) -> Any:
        raise AssertionError("disabled shape diagnostic executed")

    monkeypatch.setattr(safe_edit, "shape_validation_coverage", forbidden)
    with httpx.Client(transport=httpx.MockTransport(forbidden)) as transport:
        assert (
            safe_edit.CoverageClient(
                settings, transport, "private-token"
            )._shape_validation(ui_inventory(), source_matches=True)
            is None
        )


@pytest.mark.parametrize(
    "fault",
    ["changed_head", "writes", "environment", "diagnostics", "source", "incomplete"],
)
def test_no_failure_log_after_flag_head_or_evidence_change(
    fault: str, caplog: pytest.LogCaptureFixture
) -> None:
    provider = Provider()
    provider.data = ui_inventory()
    settings = enabled_settings()
    if fault == "source":
        provider.data["sourceMicroversion"] = M1
    elif fault == "incomplete":
        provider.data["isComplete"] = False
    heads = 0

    def read(request: httpx.Request) -> httpx.Response:
        nonlocal heads
        response = provider.handle(request)
        if request.url.path.endswith("currentmicroversion"):
            heads += 1
            if heads == 2:
                if fault == "changed_head":
                    return httpx.Response(200, json={"microversion": M1})
                if fault == "writes":
                    settings.forge_cad_writes_enabled = True
                elif fault == "environment":
                    settings.environment = "production"
                elif fault == "diagnostics":
                    settings.forge_safe_edit_diagnostics_enabled = False
        return response

    with (
        httpx.Client(transport=httpx.MockTransport(read)) as transport,
        caplog.at_level(logging.WARNING),
    ):
        client = safe_edit.CoverageClient(settings, transport, "private-token")
        if fault == "changed_head":
            with pytest.raises(EditError, match="model_changed"):
                client.compare(REF)
        else:
            client.compare(REF)
    assert not shape_lines(caplog) and provider.writes == 0


def test_guard_is_rechecked_before_each_feature_log(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    provider = Provider()
    provider.data = ui_inventory()
    settings = enabled_settings()
    original = safe_edit.logger.warning

    def log(message: str, *args: Any, **kwargs: Any) -> None:
        original(message, *args, **kwargs)
        if message.startswith("safe_edit_standard_shape_"):
            settings.forge_safe_edit_diagnostics_enabled = False

    monkeypatch.setattr(safe_edit.logger, "warning", log)
    with (
        httpx.Client(transport=httpx.MockTransport(provider.handle)) as transport,
        caplog.at_level(logging.WARNING),
    ):
        safe_edit.CoverageClient(settings, transport, "private-token").compare(REF)
    assert len(shape_lines(caplog)) == 1 and provider.writes == 0


@pytest.mark.parametrize(
    "data", [None, {}, {"features": None}, {"features": [{}] * 21}]
)
def test_projection_container_bound_remains_closed(data: Any) -> None:
    with pytest.raises(EditError, match="invalid_provider_response"):
        shape_validation_coverage(data)


def test_projection_ignores_unsupported_categories_and_contains_no_raw_data() -> None:
    data = ui_inventory()
    data["features"][0].update(featureType="private-feature-type", raw="private-value")
    result = shape_validation_coverage(data)
    assert [r.category for r in result] == ["extrude", "fillet"]
    assert "private-" not in json.dumps([r.model_dump() for r in result])


@pytest.mark.parametrize("field", ["parameter", "reason"])
def test_failure_schema_rejects_untrusted_strings_without_echo(field: str) -> None:
    data = {"parameter": "radius", "reason": "wrong_bt_type", field: "private-string"}
    with pytest.raises(ValidationError) as caught:
        ShapeFailure.model_validate_json(json.dumps(data))
    assert "private-string" not in str(caught.value)
