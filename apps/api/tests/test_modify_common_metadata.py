"""Current public-schema placeholders, conservative linkage rejection, no CAD I/O."""

import json
import logging
from copy import deepcopy
from typing import Any

import httpx2 as httpx
import pytest
from pydantic import ValidationError
from test_cad_read import REF
from test_modify_conformance import operation_for
from test_modify_plan import OP, target
from test_modify_representation import enabled_settings, metadata
from test_modify_ui_conformance import CASES, param, replacement_rejects, ui_inventory
from test_safe_edit import M0, Provider, bodies, config

from forge_api.cad_edits.domain import EditError, fingerprint
from forge_api.cad_edits.plans import ResolvedOperation
from forge_api.integrations.onshape.dev import safe_edit
from forge_api.integrations.onshape.dev.standard_shape_failure import diagnose_ui_shape
from forge_api.integrations.onshape.edit_registry import change
from forge_api.integrations.onshape.modify_evidence import (
    project_modify_evidence,
    verify_operation,
)
from forge_api.integrations.onshape.standard_edit_shapes import ui_quantity_parameter
from forge_api.integrations.onshape.standard_shape_contract import (
    CommonMetadataFailure,
    ShapeValidationError,
)

FIELDS = ["parameterName", "valueString"]
REPRESENTATIVES = [
    (2, "domain"),
    (2, "depth"),
    (2, "hasDraft"),
    (2, "entities"),
    (3, "filletType"),
    (3, "radius"),
    (3, "tangentPropagation"),
    (3, "entities"),
    (3, "vertexSettings"),
]
WRONG_TEXT: list[tuple[Any, str]] = [
    (None, "null"),
    (False, "boolean"),
    (0, "number"),
    (0.0, "number"),
    ([], "array"),
    ({"private-metadata": "private-value"}, "object"),
    ("private-metadata\n#variable\u0000", "nonempty_string"),
    (" ", "nonempty_string"),
]
LIBRARY = [
    ("DEFAULT", "default"),
    ("IGNORE_LIBRARY_VALUES", "ignore_library_values"),
    ("UNKNOWN", "unknown_library_value"),
    ("NONE", "unrecognized_string"),
    ("private-library", "unrecognized_string"),
    ("", "empty_string"),
    *WRONG_TEXT[:6],
]
OPERATIONS = [
    (2, "RENAME_FEATURE"),
    (3, "RENAME_FEATURE"),
    (2, "SET_EXTRUDE_DEPTH"),
    (3, "SET_FILLET_RADIUS"),
]


@pytest.mark.parametrize("position,key", CASES)
def test_empty_documented_common_fields_are_supported_on_every_parameter(
    position: int, key: str
) -> None:
    data = ui_inventory()
    item = param(data, position, key)
    item.update(parameterName="", valueString="", importMicroversion="")
    original = deepcopy(data)
    feature = data["features"][position - 1]
    assert ui_quantity_parameter(feature, "depth" if position == 2 else "radius")
    report = diagnose_ui_shape(feature, "extrude" if position == 2 else "fillet")
    assert report.failure is None and report.common is None
    assert metadata(data, position)["replacement"] == "exact_match"
    assert metadata(data, position)["rename"] == "exact_match"
    assert data == original


@pytest.mark.parametrize("position,key", REPRESENTATIVES)
@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("value,state", WRONG_TEXT)
def test_nonempty_or_malformed_text_rejects_through_shared_validator(
    position: int, key: str, field: str, value: Any, state: str
) -> None:
    assert_common_rejection(position, key, field, value, state)


@pytest.mark.parametrize("position,key", REPRESENTATIVES)
@pytest.mark.parametrize("value,state", LIBRARY)
def test_every_present_library_state_remains_unsupported(
    position: int, key: str, value: Any, state: str
) -> None:
    assert_common_rejection(position, key, "libraryRelationType", value, state)


def assert_common_rejection(
    position: int, key: str, field: str, value: Any, state: str
) -> None:
    data = ui_inventory()
    param(data, position, key)[field] = value
    feature = data["features"][position - 1]
    original = deepcopy(data)
    with pytest.raises(ShapeValidationError) as caught:
        ui_quantity_parameter(feature, "depth" if position == 2 else "radius")
    error = caught.value
    assert str(error) == "unsupported_target" and error.status == 422
    report = diagnose_ui_shape(feature, "extrude" if position == 2 else "fillet")
    assert report.failure == error.failure and report.common == error.common
    assert report.failure is not None and report.common is not None
    assert report.failure.model_dump() == {
        "parameter": key,
        "reason": "unexpected_field",
    }
    assert report.common.model_dump() == {
        "field": field,
        "present": True,
        "state": state,
    }
    assert "private-" not in report.model_dump_json()
    replacement_rejects(data, position)
    assert data == original


@pytest.mark.parametrize("position,key", REPRESENTATIVES)
@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("importMicroversion", "private-import", "bookkeeping_import_microversion"),
        ("importMicroversion", None, "bookkeeping_import_microversion"),
        ("configuration", {}, "unexpected_field"),
        ("parameter_name", "", "unexpected_field"),
        ("private-field", "private-value", "unexpected_field"),
    ],
)
def test_unknown_alias_config_and_import_do_not_gain_authority(
    position: int, key: str, field: str, value: Any, reason: str
) -> None:
    data = ui_inventory()
    param(data, position, key)[field] = value
    report = diagnose_ui_shape(
        data["features"][position - 1], "extrude" if position == 2 else "fillet"
    )
    assert report.failure is not None and report.failure.reason == reason
    assert report.common is None
    replacement_rejects(data, position)


@pytest.mark.parametrize("position,kind", OPERATIONS)
def test_metadata_and_entire_definition_preserved_with_only_authorized_delta(
    position: int, kind: str
) -> None:
    data = ui_inventory()
    original = deepcopy(data)
    operation = OP.validate_python(operation_for(kind, target(position).handle))
    updated, preview = change(data["features"], target(position), operation)
    expected = deepcopy(data["features"][position - 1])
    if kind == "RENAME_FEATURE":
        expected["name"] = "Conformance renamed"
    else:
        key = "depth" if position == 2 else "radius"
        next(p for p in expected["parameters"] if p["parameterId"] == key)[
            "expression"
        ] = "25 mm" if position == 2 else "3 mm"
    assert fingerprint(updated) == fingerprint(expected)
    # Ordered serialization includes all parameter keys, nodes, queries, metadata.
    assert json.dumps(updated) == json.dumps(expected)
    assert data == original
    before = project_modify_evidence(REF, M0, data, config(), bodies())
    marker = "e" * 24
    after_data = deepcopy(data)
    after_data["features"][position - 1] = updated
    after_data["sourceMicroversion"] = marker
    after = project_modify_evidence(
        REF, marker, after_data, config(marker), bodies(marker)
    )
    verify_operation(
        before,
        after,
        ResolvedOperation(
            operation=operation, target=target(position), preview=preview
        ),
        marker,
    )


@pytest.mark.parametrize("position,kind", OPERATIONS)
@pytest.mark.parametrize("field", FIELDS)
def test_even_eligible_metadata_omission_is_an_unrelated_postwrite_effect(
    position: int, kind: str, field: str
) -> None:
    data = ui_inventory()
    before = project_modify_evidence(REF, M0, data, config(), bodies())
    operation = OP.validate_python(operation_for(kind, target(position).handle))
    updated, preview = change(data["features"], target(position), operation)
    data["features"][position - 1] = updated
    del param(data, position, "depth" if position == 2 else "radius")[field]
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
    "field,value,state",
    [
        ("parameterName", "private-name\n#variable", "nonempty_string"),
        ("valueString", {"private-json": "private-value"}, "object"),
        ("libraryRelationType", "private-library", "unrecognized_string"),
        ("libraryRelationType", "DEFAULT", "default"),
    ],
)
def test_only_closed_common_state_escapes_all_diagnostics_without_more_gets(
    field: str, value: Any, state: str, caplog: pytest.LogCaptureFixture
) -> None:
    provider = Provider()
    provider.data = ui_inventory()
    param(provider.data, 2, "domain")[field] = value
    param(provider.data, 3, "filletType")[field] = value
    original = deepcopy(provider.data)
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
    assert (
        lines
        == [
            "safe_edit_standard_shape_failure category=extrude parameter=domain "
            f"reason=unexpected_field common_field={field} present=true state={state}",
            "safe_edit_standard_shape_failure category=fillet parameter=filletType "
            f"reason=unexpected_field common_field={field} present=true state={state}",
        ]
        * 2
    )
    assert "private-" not in caplog.text and "#variable" not in caplog.text
    assert len(provider.calls) == 4 and all(
        call.method == "GET" for call in provider.calls
    )
    assert provider.writes == 0 and provider.data == original


@pytest.mark.parametrize("field", ["field", "state", "extra"])
def test_common_diagnostic_schema_cannot_echo_unknown_labels(field: str) -> None:
    data = {
        "field": "parameterName",
        "present": True,
        "state": "nonempty_string",
        field: "private-value",
    }
    with pytest.raises(ValidationError) as caught:
        CommonMetadataFailure.model_validate(data)
    assert "private-value" not in str(caught.value)


def test_common_parameter_metadata_is_not_accepted_on_query_items() -> None:
    data = ui_inventory()
    param(data, 2, "entities")["queries"][0].update(parameterName="", valueString="")
    report = diagnose_ui_shape(data["features"][1], "extrude")
    assert report.failure and report.failure.reason == "query_item_unexpected_field"
    assert report.common is None
    replacement_rejects(data, 2)
