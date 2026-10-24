"""Public-source vocabulary is diagnostic evidence, never adapter permission.

Invented inputs below are not captures or claims of current UI serialization.
Existing registry assertions and representation reports must remain unchanged.
"""

import json
import logging
from copy import deepcopy
from typing import Any

import httpx2 as httpx
import pytest
from pydantic import ValidationError
from test_cad_read import REF
from test_modify_plan import inventory
from test_modify_representation import enabled_settings, metadata
from test_safe_edit import Provider

from forge_api.cad_edits.domain import EditError
from forge_api.integrations.onshape.dev import safe_edit
from forge_api.integrations.onshape.dev.standard_parameters import (
    ENUMS,
    EXTRUDE,
    FILLET,
    StandardCoverage,
    standard_parameter_coverage,
)
from forge_api.integrations.onshape.edit_registry import quantity_parameter
from forge_api.integrations.onshape.eligibility import MISSING

CATALOG = [(2, key, kind) for key, kind in EXTRUDE.items()] + [
    (3, key, kind) for key, kind in FILLET.items()
]
EXTRAS = [
    (position, key, kind)
    for position, key, kind in CATALOG
    if key
    not in {
        p["parameterId"] for p in inventory()["features"][position - 1]["parameters"]
    }
]


def report(data: Any, position: int = 2) -> dict[str, Any]:
    return (
        standard_parameter_coverage(data, source_matches=True)
        .positions[position - 1]
        .model_dump(mode="json")
    )


def item(data: Any, key: str) -> dict[str, Any]:
    return next(p for p in data["parameters"] if p["parameter_id"] == key)


def source_input(key: str, kind: str) -> dict[str, Any]:
    # This is only a schema-classification input. It is not a UI-shape fixture.
    value: dict[str, Any] = {"parameterId": key, "nodeId": "private-node"}
    if kind == "enum":
        enum_name, enum_value = next(
            enum for name, enum in ENUMS.items() if name == key
        )
        value.update(
            btType="BTMParameterEnum-145", enumName=enum_name, value=enum_value
        )
    elif kind == "boolean":
        value.update(btType="BTMParameterBoolean-144", value=False)
    elif kind == "query":
        value.update(btType="BTMParameterQueryList-148", queries=[])
    elif kind == "array":
        value.update(btType="BTMParameterArray-2025", items=[])
    else:
        value.update(
            btType="BTMParameterQuantity-147",
            expression="private-expression",
            value=0,
            units="",
        )
    return value


@pytest.mark.parametrize("position,key,kind", CATALOG)
def test_each_source_input_is_recognized_without_emitting_provider_text(
    position: int, key: str, kind: str
) -> None:
    data = inventory()
    data["features"][position - 1]["parameters"] = [source_input(key, kind)]
    original = deepcopy(data)
    result = report(data, position)
    assert item(result, key)["source_kind"] == kind
    assert not result["unrecognized_present"]
    assert not result["duplicate_present"] and not result["malformed_present"]
    assert "private-" not in json.dumps(result)
    assert data == original


@pytest.mark.parametrize("position,key,kind", EXTRAS)
def test_recognition_of_an_extra_parameter_never_makes_it_writable(
    position: int, key: str, kind: str
) -> None:
    data = inventory()
    params = data["features"][position - 1]["parameters"]
    params.append(source_input(key, kind))
    assert item(report(data, position), key)["occurrences"] == 1
    assert metadata(data, position)["replacement"] == "unsupported_shape"
    assert metadata(data, position)["rename"] == "unsupported_shape"
    with pytest.raises(EditError, match="unsupported_target"):
        quantity_parameter(
            data["features"][position - 1],
            "SET_EXTRUDE_DEPTH" if position == 2 else "SET_FILLET_RADIUS",
        )


@pytest.mark.parametrize("position,key,kind", CATALOG)
def test_wrong_types_and_missing_values_are_reported_without_authority(
    position: int, key: str, kind: str
) -> None:
    data = inventory()
    param = {"parameterId": key, "btType": "private-provider-type"}
    data["features"][position - 1]["parameters"] = [param, deepcopy(param)]
    result = report(data, position)
    observed = item(result, key)
    assert observed["bt_type"] == "other"
    assert observed["duplicate"] and result["duplicate_present"]
    assert observed["occurrences"] == 2
    assert metadata(data, position)["replacement"] == "unsupported_shape"
    assert "private-" not in json.dumps(result)


@pytest.mark.parametrize("position,catalog", [(2, EXTRUDE), (3, FILLET)])
def test_complete_source_catalog_is_bounded_and_still_rejected(
    position: int, catalog: Any
) -> None:
    data = inventory()
    data["features"][position - 1]["parameters"] = [
        source_input(key, kind) for key, kind in catalog.items()
    ]
    result = report(data, position)
    assert len(result["parameters"]) == len(catalog) <= 50
    assert not result["unrecognized_present"]
    old = metadata(data, position)
    assert old["parameter_count"] == 20 and old["parameter_count_capped"]
    assert old["unknown_present"] and old["replacement"] == "unsupported_shape"


@pytest.mark.parametrize("key", ["units", "importMicroversion"])
@pytest.mark.parametrize(
    "value,expected",
    [
        (MISSING, "missing"),
        (None, "null"),
        ("", "empty"),
        ("private-value", "nonempty"),
        ([], "wrong_type"),
    ],
)
def test_quantity_string_fields_are_presence_classes_only(
    key: str, value: Any, expected: str
) -> None:
    data = inventory()
    quantity = data["features"][1]["parameters"][-1]
    assert quantity["parameterId"] == "depth"
    if value is not MISSING:
        quantity[key] = value
    result = report(data)
    field = "units" if key == "units" else "import_microversion"
    assert item(result, "depth")["quantity_fields"][field] == expected
    assert "private-" not in json.dumps(result)
    if value is not MISSING:
        assert metadata(data)["replacement"] == "unsupported_shape"


@pytest.mark.parametrize(
    "value,expected",
    [
        (MISSING, "missing"),
        (None, "null"),
        (0, "zero"),
        (0.0, "zero"),
        (123.456, "nonzero"),
        (False, "wrong_type"),
        ("private-value", "wrong_type"),
    ],
)
def test_quantity_value_is_classified_without_output_or_acceptance(
    value: Any, expected: str
) -> None:
    data = inventory()
    if value is not MISSING:
        data["features"][1]["parameters"][-1]["value"] = value
    result = report(data)
    assert item(result, "depth")["quantity_fields"]["value"] == expected
    assert "123.456" not in json.dumps(result) and "private-" not in json.dumps(result)
    if value is not MISSING:
        assert metadata(data)["replacement"] == "unsupported_shape"


def test_arbitrary_fields_ids_values_and_nested_cad_never_escape() -> None:
    data = inventory()
    params = data["features"][1]["parameters"]
    quantity = params[-1]
    quantity.update({f"private-field-{i}": "private-value" for i in range(21)})
    params += [source_input("hasDraft", "boolean") for _ in range(21)]
    params += [{"parameterId": f"private-id-{i}"} for i in range(21)]
    params += [{"parameterId": None}, "private-malformed"]
    result = report(data)
    assert result["unrecognized_count"] == 20 and result["unrecognized_count_capped"]
    assert result["duplicate_present"] and result["malformed_present"]
    assert item(result, "hasDraft")["occurrences"] == 20
    fields = item(result, "depth")["quantity_fields"]
    assert fields["other_fields_present"]
    assert fields["other_field_count"] == 20 and fields["other_field_count_capped"]
    assert "private-" not in json.dumps(result)
    # Source vocabulary is feature-specific; a fillet ID in an extrude is unknown.
    params.append(source_input("isVariable", "boolean"))
    assert "isVariable" not in json.dumps(report(data))


@pytest.mark.parametrize(
    "value,state",
    [
        (MISSING, "missing"),
        (None, "null"),
        ({}, "wrong_type"),
        ([], "empty"),
        (["private-item"], "nonempty"),
    ],
)
def test_array_contents_never_escape(value: Any, state: str) -> None:
    data = inventory()
    param = source_input("vertexSettings", "array")
    param.pop("items")
    if value is not MISSING:
        param["items"] = value
    data["features"][2]["parameters"].append(param)
    result = report(data, 3)
    assert item(result, "vertexSettings")["array_state"] == state
    assert "private-" not in json.dumps(result)
    assert metadata(data, 3)["replacement"] == "unsupported_shape"


@pytest.mark.parametrize(
    "data", [None, [], {}, {"features": {}}, {"features": [{}] * 21}]
)
def test_response_feature_bound_and_container_fail_closed(data: Any) -> None:
    with pytest.raises(EditError, match="invalid_provider_response"):
        standard_parameter_coverage(data, source_matches=True)


@pytest.mark.parametrize(
    "enabled,environment,writes",
    [
        (False, "development", False),
        (True, "test", False),
        (True, "production", False),
        (True, "development", True),
    ],
)
def test_projection_guards_are_rechecked_before_work(
    enabled: bool, environment: Any, writes: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = enabled_settings()
    settings.forge_safe_edit_diagnostics_enabled = enabled
    settings.environment = environment
    settings.forge_cad_writes_enabled = writes

    def forbidden(*_: Any, **__: Any) -> Any:
        raise AssertionError("disabled diagnostic executed")

    monkeypatch.setattr(safe_edit, "standard_parameter_coverage", forbidden)
    with httpx.Client(transport=httpx.MockTransport(forbidden)) as transport:
        assert (
            safe_edit.CoverageClient(
                settings, transport, "private-token"
            )._standard_parameters(inventory(), source_matches=True)
            is None
        )


def test_new_logs_reuse_reads_and_do_not_change_the_existing_report(
    caplog: pytest.LogCaptureFixture,
) -> None:
    provider = Provider()
    provider.data = inventory()
    provider.data["features"][1]["parameters"].append(
        source_input("hasDraft", "boolean")
    )
    before = metadata(provider.data)
    with (
        httpx.Client(transport=httpx.MockTransport(provider.handle)) as transport,
        caplog.at_level(logging.WARNING),
    ):
        safe_edit.CoverageClient(
            enabled_settings(), transport, "private-token"
        ).compare(REF)
    lines = [
        json.loads(record.message.split("metadata=")[1])
        for record in caplog.records
        if record.message.startswith("safe_edit_standard_parameter_coverage ")
    ]
    assert len(lines) == 2
    for line in lines:
        assert line["purpose"] == "source_vocabulary_only_no_edit_authority"
        assert item(line["positions"][1], "hasDraft")["boolean_value"] is False
        StandardCoverage.model_validate_json(json.dumps(line))
    assert metadata(provider.data) == before
    assert len(provider.calls) == 4 and all(
        call.method == "GET" for call in provider.calls
    )
    assert provider.writes == 0 and "private-" not in caplog.text


def test_metadata_schema_rejects_arbitrary_strings_without_echoing_input() -> None:
    data = standard_parameter_coverage(inventory(), source_matches=True).model_dump(
        mode="json"
    )
    data["positions"][1]["parameters"][0]["parameter_id"] = "private-id"
    with pytest.raises(ValidationError) as caught:
        StandardCoverage.model_validate_json(json.dumps(data))
    assert "private-id" not in str(caught.value)
