"""Complete closed Extrude quantity evidence; diagnostics never authorize edits."""

import json
import logging
from copy import deepcopy
from typing import Any

import httpx2 as httpx
import pytest
from conftest import Harness
from pydantic import ValidationError
from sqlalchemy import func, select
from test_cad_read import REF, CadProvider, set_scope
from test_modify_current_query_contracts import current_inventory
from test_modify_representation import enabled_settings
from test_modify_ui_conformance import param, replacement_rejects, ui_inventory
from test_safe_edit import Provider

from forge_api.cad_edits.domain import EditError, fingerprint
from forge_api.db.models import WriteFence, WriteRecord
from forge_api.integrations.onshape.dev import safe_edit
from forge_api.integrations.onshape.dev.extrude_quantities import (
    EXTRUDE_QUANTITY_ROLES,
    MAX_LOG_CHARS,
    ExtrudeQuantityInventory,
    extrude_quantity_inventory,
    extrude_quantity_text,
)
from forge_api.integrations.onshape.dev.standard_parameters import EXTRUDE

EXPECTED = (
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
HOSTILE = "private-provider-value\nrole=depth outcome=exact_match"


def report(data: dict[str, Any]) -> ExtrudeQuantityInventory:
    reports = extrude_quantity_inventory(data)
    assert len(reports) == 1
    return reports[0]


def role(data: dict[str, Any], key: str) -> Any:
    return next(item for item in report(data).roles if item.role == key)


def test_roles_are_derived_from_the_complete_source_vocabulary_in_source_order() -> (
    None
):
    assert EXTRUDE_QUANTITY_ROLES == EXPECTED
    assert (
        tuple(
            key for key, kind in EXTRUDE.items() if kind in {"length", "angle", "real"}
        )
        == EXTRUDE_QUANTITY_ROLES
    )


def test_current_fixture_reports_every_role_without_stopping_at_thickness2() -> None:
    data = ui_inventory()
    original = deepcopy(data)
    inventory = report(data)
    assert tuple(item.role for item in inventory.roles) == EXPECTED
    assert [item.source_kind for item in inventory.roles] == [
        "length",
        "length",
        "length",
        "length",
        "angle",
        "length",
        "angle",
        "length",
        "length",
        "length",
    ]
    assert inventory.roles[0].activity == "active"
    assert all(item.activity == "dormant" for item in inventory.roles[1:])
    assert inventory.summary.model_dump() == {
        "position": 2,
        "expected_roles": 10,
        "roles_present": 10,
        "roles_inspected": 10,
        "all_roles_inspected": True,
        "unrecognized_quantity_parameters": 0,
        "parameter_count_capped": False,
        "any_missing": False,
        "any_duplicate": False,
        "any_malformed": False,
        "any_unexpected_fields": False,
        "any_uninspected": False,
    }
    for item in inventory.roles:
        evidence = item.evidence
        assert evidence is not None
        assert evidence.provider_type == "quantity"
        assert evidence.expression.expression_class == "literal"
        assert item.expression_dimension_matches_source
        assert evidence.value == "zero" and evidence.cached_units == "empty"
        assert evidence.node_id == "string_present"
        assert evidence.is_integer == "false"
        assert evidence.required_fields_present and evidence.allowed_fields_only
    assert data == original
    assert len(extrude_quantity_text(inventory)) < MAX_LOG_CHARS


@pytest.mark.parametrize(
    "expression,expected",
    [
        (
            "-2.5 mm",
            ("literal", "negative", "decimal", "minus", "mm", True),
        ),
        ("0 mm", ("literal", "zero", "integer", "unsigned", "mm", True)),
        ("+5 in", ("literal", "positive", "integer", "plus", "in", True)),
        ("3 deg", ("literal", "positive", "integer", "unsigned", "deg", False)),
        (
            "1e2 mm",
            (
                "scientific_literal",
                "unavailable",
                "scientific",
                "unsigned",
                "unavailable",
                None,
            ),
        ),
        (
            "#configured",
            (
                "configuration_reference",
                "unavailable",
                "unavailable",
                "unavailable",
                "unavailable",
                None,
            ),
        ),
        (
            "5 mm * 2",
            (
                "arithmetic_expression",
                "unavailable",
                "unavailable",
                "unavailable",
                "unavailable",
                None,
            ),
        ),
        (
            HOSTILE,
            (
                "arithmetic_expression",
                "unavailable",
                "unavailable",
                "unavailable",
                "unavailable",
                None,
            ),
        ),
    ],
)
def test_expression_shapes_are_closed_and_never_emit_expression_text(
    expression: str, expected: tuple[Any, ...]
) -> None:
    data = ui_inventory()
    param(data, 2, "thickness2")["expression"] = expression
    item = role(data, "thickness2")
    evidence = item.evidence
    assert evidence is not None
    actual = evidence.expression
    assert (
        actual.expression_class,
        actual.number_class,
        actual.number_format,
        actual.sign,
        actual.units,
        item.expression_dimension_matches_source,
    ) == expected
    assert expression not in item.model_dump_json()


@pytest.mark.parametrize(
    "value,classification",
    [
        (None, "null"),
        (False, "wrong_type"),
        (-2.5, "negative"),
        (0, "zero"),
        (2.5, "positive"),
        (float("inf"), "nonfinite"),
        (float("nan"), "nonfinite"),
    ],
)
def test_cached_numeric_value_is_classified_without_emitting_it(
    value: Any, classification: str
) -> None:
    data = ui_inventory()
    param(data, 2, "thickness2")["value"] = value
    evidence = role(data, "thickness2").evidence
    assert evidence is not None and evidence.value == classification
    if value == -2.5 or value == 2.5:
        assert str(value) not in evidence.model_dump_json()


@pytest.mark.parametrize(
    "field,value,classification",
    [
        ("units", None, "null"),
        ("units", 1, "wrong_type"),
        ("units", "", "empty"),
        ("units", HOSTILE, "nonempty"),
        ("nodeId", None, "null"),
        ("nodeId", 1, "wrong_type"),
        ("nodeId", "", "empty"),
        ("nodeId", HOSTILE, "string_present"),
        ("isInteger", None, "null"),
        ("isInteger", 0, "wrong_type"),
        ("isInteger", False, "false"),
        ("isInteger", True, "true"),
    ],
)
def test_units_node_and_integer_states_are_closed(
    field: str, value: Any, classification: str
) -> None:
    data = ui_inventory()
    param(data, 2, "thickness2")[field] = value
    evidence = role(data, "thickness2").evidence
    assert evidence is not None
    actual = {
        "units": evidence.cached_units,
        "nodeId": evidence.node_id,
        "isInteger": evidence.is_integer,
    }[field]
    assert actual == classification and HOSTILE not in evidence.model_dump_json()


def test_exact_allowed_field_envelope_is_reported_without_unknown_names() -> None:
    data = ui_inventory()
    item = param(data, 2, "thickness2")
    del item["value"]
    item["parameterName"] = ""
    item["libraryRelationType"] = "DEFAULT"
    item[HOSTILE] = {HOSTILE: HOSTILE}
    evidence = role(data, "thickness2").evidence
    assert evidence is not None
    assert evidence.present_allowed_fields == (
        "btType",
        "parameterId",
        "expression",
        "nodeId",
        "isInteger",
        "units",
        "parameterName",
        "libraryRelationType",
    )
    assert evidence.required_fields_present
    assert not evidence.allowed_fields_only
    assert evidence.unexpected_field_count == 1
    assert not evidence.unexpected_field_count_capped
    assert evidence.parameter_name == "empty"
    assert evidence.library_relation_type == "default"
    assert HOSTILE not in evidence.model_dump_json()


@pytest.mark.parametrize(
    "field,value,expected",
    [
        ("btType", None, "null"),
        ("btType", 1, "wrong_type"),
        ("btType", "BTMParameterString-149", "other_provider_type"),
        ("expression", None, "null"),
        ("expression", [], "wrong_type"),
        ("expression", "", "empty"),
    ],
)
def test_wrong_types_and_missing_required_fields_are_marked_malformed(
    field: str, value: Any, expected: str
) -> None:
    data = ui_inventory()
    item = param(data, 2, "thickness2")
    item[field] = value
    quantity = role(data, "thickness2")
    assert quantity.malformed and report(data).summary.all_roles_inspected
    evidence = quantity.evidence
    assert evidence is not None
    actual = (
        evidence.provider_type
        if field == "btType"
        else evidence.expression.expression_class
    )
    assert actual == expected
    del item[field]
    quantity = role(data, "thickness2")
    assert quantity.malformed
    assert quantity.evidence is not None
    assert not quantity.evidence.required_fields_present


def test_role_substitution_and_zero_reuse_remain_role_specific_and_unauthorized() -> (
    None
):
    data = ui_inventory()
    draft = deepcopy(param(data, 2, "draftAngle"))
    thickness = param(data, 2, "thickness2")
    draft["parameterId"] = "thickness2"
    data["features"][1]["parameters"] = [
        draft if item is thickness else item
        for item in data["features"][1]["parameters"]
    ]
    substituted = role(data, "thickness2")
    assert substituted.source_kind == "length"
    assert substituted.evidence is not None
    assert substituted.evidence.expression.units == "deg"
    assert substituted.expression_dimension_matches_source is False
    replacement_rejects(data, 2)

    data = ui_inventory()
    param(data, 2, "thickness2")["expression"] = "0 mm"
    zero = role(data, "thickness2")
    assert zero.evidence is not None
    assert zero.evidence.expression.number_class == "zero"
    assert zero.role == "thickness2" and zero.activity == "dormant"
    replacement_rejects(data, 2)


def test_missing_duplicate_unknown_and_capped_parameters_cannot_look_complete() -> None:
    data = ui_inventory()
    parameters = data["features"][1]["parameters"]
    parameters.remove(param(data, 2, "thickness2"))
    duplicate = deepcopy(param(data, 2, "thickness1"))
    parameters.append(duplicate)
    parameters.append(
        {
            "btType": "BTMParameterQuantity-147",
            "parameterId": HOSTILE,
            "expression": HOSTILE,
        }
    )
    inventory = report(data)
    assert inventory.summary.any_missing
    assert inventory.summary.any_duplicate
    assert inventory.summary.any_uninspected
    assert inventory.summary.unrecognized_quantity_parameters == 1
    assert not inventory.summary.all_roles_inspected
    assert role(data, "thickness1").evidence is None
    assert HOSTILE not in inventory.model_dump_json()


@pytest.mark.parametrize("data", [None, {}, {"features": [None] * 21}])
def test_feature_inventory_bound_is_enforced(data: Any) -> None:
    with pytest.raises(EditError, match="invalid_provider_response"):
        extrude_quantity_inventory(data)


def test_models_are_strict_frozen_and_extra_forbidden() -> None:
    inventory = report(ui_inventory())
    with pytest.raises(ValidationError):
        ExtrudeQuantityInventory.model_validate(
            {**inventory.model_dump(), "private": HOSTILE}
        )
    with pytest.raises(ValidationError):
        field = "any_missing"
        setattr(inventory.summary, field, True)


@pytest.mark.parametrize(
    "environment,diagnostics,writes",
    [
        ("production", True, False),
        ("development", False, False),
        ("development", True, True),
    ],
)
def test_projection_hook_requires_dev_diagnostics_on_and_writes_off(
    environment: Any, diagnostics: bool, writes: bool
) -> None:
    settings = enabled_settings()
    settings.environment = environment
    settings.forge_safe_edit_diagnostics_enabled = diagnostics
    settings.forge_cad_writes_enabled = writes
    with httpx.Client(transport=httpx.MockTransport(Provider().handle)) as transport:
        client = safe_edit.CoverageClient(settings, transport, "synthetic-token")
        assert client._extrude_quantities(ui_inventory(), source_matches=True) is None


def test_one_inspector_refresh_emits_both_variants_with_zero_write_authority(
    harness: Harness, caplog: pytest.LogCaptureFixture
) -> None:
    user = harness.login()
    set_scope(harness, user, "OAuth2ReadPII OAuth2Read")
    settings = harness.runtime.settings
    settings.environment = "development"
    settings.forge_safe_edit_diagnostics_enabled = True
    assert not settings.forge_cad_writes_enabled
    provider = Provider()
    provider.data = current_inventory()
    param(provider.data, 2, "thickness2")["expression"] = "-2.5 mm"
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
    records = [
        json.loads(record.message.split("metadata=", 1)[1])
        for record in caplog.records
        if record.message.startswith("safe_edit_extrude_quantity_coverage ")
    ]
    assert response.status_code == 200 and len(calls) == 13
    assert len(records) == 2
    for inventory in records:
        assert inventory["summary"]["expected_roles"] == 10
        assert inventory["summary"]["roles_inspected"] == 10
        assert inventory["summary"]["all_roles_inspected"]
        assert [item["role"] for item in inventory["roles"]] == list(EXPECTED)
        thickness2 = next(
            item for item in inventory["roles"] if item["role"] == "thickness2"
        )
        assert thickness2["evidence"]["expression"] == {
            "expression_class": "literal",
            "number_class": "negative",
            "number_format": "decimal",
            "sign": "minus",
            "units": "mm",
        }
    assert "safe_edit_extrude_quantity_coverage" not in response.text
    assert provider.writes == 0 and fingerprint(provider.data) == original
    with harness.runtime.sessions() as db:
        assert db.scalar(select(func.count()).select_from(WriteRecord)) == 0
        assert db.scalar(select(func.count()).select_from(WriteFence)) == 0
