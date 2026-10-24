"""DEV representation logs: invented CAD, GET-only mock transport, no authority."""

import json
import logging
from copy import deepcopy
from typing import Any

import httpx2 as httpx
import pytest
from conftest import Harness
from pydantic import BaseModel, ValidationError
from sqlalchemy import func, select
from test_cad_read import REF, CadProvider, set_scope
from test_modify_plan import inventory
from test_safe_edit import M0, M1, Provider

from forge_api.cad_edits import plan_service, plan_storage
from forge_api.cad_edits.domain import EditError
from forge_api.core.config import Settings
from forge_api.db.models import WriteFence, WriteRecord
from forge_api.integrations.onshape.dev import safe_edit
from forge_api.integrations.onshape.dev.modify_representation import (
    RepresentationCoverage,
    representation_coverage,
)
from forge_api.integrations.onshape.eligibility import MISSING
from forge_api.integrations.onshape.write_client import SafeEditClient


def metadata(data: Any, position: int = 2) -> dict[str, Any]:
    return (
        representation_coverage(
            data, source_matches=data.get("sourceMicroversion") == M0
        )
        .positions[position - 1]
        .model_dump(mode="json")
    )


def parameter(data: dict[str, Any], position: int, key: str) -> dict[str, Any]:
    return next(
        p
        for p in data["features"][position - 1]["parameters"]
        if p["parameterId"] == key
    )


def known(report: dict[str, Any], key: str) -> dict[str, Any]:
    return next(p for p in report["parameters"] if p["parameter_id"] == key)


def enabled_settings() -> Settings:
    return Settings(
        _env_file=None,
        environment="development",
        forge_safe_edit_diagnostics_enabled=True,
        forge_cad_writes_enabled=False,
    )


@pytest.mark.parametrize("position", [2, 3])
def test_supported_shapes_are_exact_matches_without_modifying_input(
    position: int,
) -> None:
    data = inventory()
    original = deepcopy(data)
    result = metadata(data, position)
    assert result["replacement"] == result["rename"] == "exact_match"
    assert result["definition_bt_type"] == "recognized_standard"
    assert result["parameter_shape_matches_registry"]
    assert not result["unknown_present"] and not result["duplicate_known_present"]
    quantity = known(result, "depth" if position == 2 else "radius")["quantity"]
    assert quantity == {
        "expression": "positive_mm_literal",
        "node_id": "missing",
        "is_integer": "missing",
        "supported_fields_only": True,
    }
    assert data == original
    assert metadata(data, 1)["replacement"] == "unavailable"


@pytest.mark.parametrize("position", [2, 3])
@pytest.mark.parametrize(
    "case",
    [
        "missing",
        "null",
        "malformed",
        "empty",
        "duplicate",
        "missing_required",
        "unknown",
        "bad_id",
        "bad_item",
    ],
)
def test_missing_duplicate_and_malformed_parameters_fail_closed(
    position: int, case: str
) -> None:
    data = inventory()
    feature = data["features"][position - 1]
    if case == "missing":
        del feature["parameters"]
    elif case == "null":
        feature["parameters"] = None
    elif case == "malformed":
        feature["parameters"] = {}
    elif case == "empty":
        feature["parameters"] = []
    elif case == "duplicate":
        feature["parameters"].append(deepcopy(feature["parameters"][0]))
    elif case == "missing_required":
        feature["parameters"].pop(0)
    elif case == "unknown":
        feature["parameters"].append({"parameterId": "private-unknown-not-logged"})
    elif case == "bad_id":
        feature["parameters"].append({"parameterId": ["private-invalid-id"]})
    else:
        feature["parameters"].append("private-malformed-parameter")
    result = metadata(data, position)
    expected = "unavailable" if case in ("missing", "null") else "unsupported_shape"
    assert result["replacement"] == result["rename"] == expected
    assert not result["parameter_shape_matches_registry"]
    assert result["duplicate_known_present"] is (case == "duplicate")
    assert result["malformed_parameter_present"] is (case in ("bad_id", "bad_item"))
    assert result["unknown_present"] is (case == "unknown")
    assert "private-" not in json.dumps(result)


@pytest.mark.parametrize(
    "position,key",
    [
        (2, "hasSecondDirection"),
        (2, "thin"),
        (2, "hasDraft"),
        (3, "variableFillet"),
        (3, "asymmetric"),
        (3, "width"),
    ],
)
def test_richer_shapes_are_counted_without_logging_unknown_ids(
    position: int, key: str
) -> None:
    data = inventory()
    data["features"][position - 1]["parameters"].append(
        {"parameterId": key, "value": False}
    )
    result = metadata(data, position)
    assert result["replacement"] == result["rename"] == "unsupported_shape"
    assert result["unknown_present"] and result["unknown_count"] == 1
    assert key not in json.dumps(result)


@pytest.mark.parametrize(
    "value,expected",
    [
        (MISSING, "missing"),
        (None, "null"),
        ([], "wrong_type"),
        ("private-type", "other"),
        ("BTMFeature-134", "recognized_standard"),
    ],
)
def test_definition_type_categories_are_closed(value: Any, expected: str) -> None:
    data = inventory()
    feature = data["features"][1]
    if value is MISSING:
        del feature["btType"]
    else:
        feature["btType"] = value
    result = metadata(data)
    assert result["definition_bt_type"] == expected
    assert (result["replacement"] == "exact_match") is (
        expected == "recognized_standard"
    )


@pytest.mark.parametrize(
    "value,expected",
    [
        (MISSING, "missing"),
        (None, "null"),
        ([], "wrong_type"),
        ("private-type", "other"),
        ("BTMParameterEnum-145", "enum"),
        ("BTMParameterQueryList-148", "query_list"),
        ("BTMParameterQuantity-147", "quantity"),
        ("BTMParameterBoolean-144", "boolean"),
    ],
)
def test_parameter_type_categories_are_closed(value: Any, expected: str) -> None:
    data = inventory()
    item = parameter(data, 2, "depth")
    if value is MISSING:
        del item["btType"]
    else:
        item["btType"] = value
    assert known(metadata(data), "depth")["bt_type"] == expected


@pytest.mark.parametrize(
    "expression,category",
    [
        ("1 in", "positive_in_literal"),
        ("0.001 mm", "positive_mm_literal"),
        ("0 mm", "other"),
        ("10001 mm", "other"),
        ("#private-variable", "other"),
        ("https://private.invalid/query", "other"),
        (MISSING, "missing"),
        (None, "wrong_type"),
        (True, "wrong_type"),
    ],
)
def test_quantities_log_classification_never_expression(
    expression: Any, category: str
) -> None:
    data = inventory()
    item = parameter(data, 2, "depth")
    if expression is MISSING:
        del item["expression"]
    else:
        item["expression"] = expression
    result = metadata(data)
    assert known(result, "depth")["quantity"]["expression"] == category
    assert (result["replacement"] == "exact_match") is category.startswith("positive_")
    if isinstance(expression, str):
        assert expression not in json.dumps(result)


@pytest.mark.parametrize(
    "field,value,expected",
    [
        ("nodeId", MISSING, "missing"),
        ("nodeId", "private-node", "string_present"),
        ("nodeId", None, "wrong_type"),
        ("isInteger", MISSING, "missing"),
        ("isInteger", False, "false"),
        ("isInteger", True, "true"),
        ("isInteger", 0, "wrong_type"),
        ("isInteger", "private-value", "wrong_type"),
    ],
)
def test_quantity_bookkeeping_is_sanitized(
    field: str, value: Any, expected: str
) -> None:
    data = inventory()
    item = parameter(data, 3, "radius")
    if value is not MISSING:
        item[field] = value
    result = metadata(data, 3)
    assert (
        known(result, "radius")["quantity"][
            "node_id" if field == "nodeId" else "is_integer"
        ]
        == expected
    )
    assert "private-" not in json.dumps(result)


@pytest.mark.parametrize(
    "key,value,expected",
    [
        ("bodyType", "SOLID", "SOLID"),
        ("bodyType", "SURFACE", "other"),
        ("operationType", "NEW", "NEW"),
        ("operationType", "REMOVE", "other"),
        ("endBound", "BLIND", "BLIND"),
        ("endBound", "UP_TO_FACE", "other"),
    ],
)
def test_enum_values_are_fixed_semantic_categories(
    key: str, value: str, expected: str
) -> None:
    data = inventory()
    item = parameter(data, 2, key)
    item["value"] = value
    assert known(metadata(data), key)["enum_value"] == expected
    item["enumName"] = "private-enum"
    result = metadata(data)
    assert known(result, key)["enum_name_matches"] is False
    assert result["replacement"] == "unsupported_shape"
    assert "private-enum" not in json.dumps(result)


@pytest.mark.parametrize(
    "value,state,count",
    [
        (MISSING, "missing", None),
        (None, "null", None),
        ({}, "wrong_type", None),
        ([], "empty", 0),
        (
            [{"btType": "BTMIndividualQuery-138", "queryString": "private-query"}],
            "nonempty",
            1,
        ),
    ],
)
def test_query_shape_only_never_query_contents(
    value: Any, state: str, count: int | None
) -> None:
    data = inventory()
    item = parameter(data, 3, "entities")
    if value is MISSING:
        del item["queries"]
    else:
        item["queries"] = value
    result = metadata(data, 3)
    query = known(result, "entities")["query"]
    assert query["state"] == state and query["count"] == count
    assert query["correct_envelope"] is isinstance(value, list)
    assert (result["replacement"] == "exact_match") is (state == "nonempty")
    assert "private-query" not in json.dumps(result)


@pytest.mark.parametrize("value", [MISSING, False, True, None, 0, "private-bool"])
def test_optional_tangent_boolean_metadata(value: Any) -> None:
    data = inventory()
    params = data["features"][-1]["parameters"]
    if value is MISSING:
        params.pop()
    else:
        params[-1]["value"] = value
    result = metadata(data, 3)
    tangent = known(result, "tangentPropagation")
    assert tangent["present"] is (value is not MISSING)
    assert tangent["boolean_type_valid"] is (
        None if value is MISSING else type(value) is bool
    )
    assert tangent["boolean_value"] is (value if type(value) is bool else None)
    assert (result["replacement"] == "exact_match") is (
        value is MISSING or type(value) is bool
    )


def test_counts_and_collections_are_bounded_and_report_truncation() -> None:
    data = inventory()
    params = data["features"][1]["parameters"]
    params.extend({"parameterId": "private-unknown"} for _ in range(25))
    parameter(data, 2, "entities")["queries"] = [{}] * 2001
    result = metadata(data)
    assert result["parameter_count"] == 20 and result["parameter_count_capped"]
    assert result["unknown_count"] == 20 and result["unknown_count_capped"]
    assert result["replacement"] == "unsupported_shape"
    query = known(result, "entities")["query"]
    assert query["count"] == 2000 and query["count_capped"]
    assert query["item_types"] == ["missing"]
    data["features"] *= 7
    with pytest.raises(EditError, match="invalid_provider_response"):
        representation_coverage(data, source_matches=True)


@pytest.mark.parametrize(
    "field,value",
    [
        ("isComplete", False),
        ("namespace", "private-custom"),
        ("subFeatures", [{}]),
        ("returnAfterSubfeatures", True),
        ("suppressed", None),
        ("name", ""),
        ("name", "private\nname"),
    ],
)
def test_incomplete_or_nonstandard_definition_never_reports_rename_exact(
    field: str, value: Any
) -> None:
    data = inventory()
    (data if field == "isComplete" else data["features"][1])[field] = value
    result = metadata(data)
    assert result["rename"] != "exact_match"
    if field == "name":
        assert result["replacement"] == "exact_match" and not result["name_usable"]


@pytest.mark.parametrize("identity", [MISSING, None, "", {}, "x" * 257])
def test_missing_or_malformed_identity_never_reports_exact_match(identity: Any) -> None:
    data = inventory()
    if identity is MISSING:
        del data["features"][1]["featureId"]
    else:
        data["features"][1]["featureId"] = identity
    result = metadata(data)
    assert not result["identity_usable"]
    assert result["replacement"] == result["rename"] == "unavailable"


def test_mismatched_pinned_source_never_reports_exact_match() -> None:
    data = inventory()
    data["sourceMicroversion"] = M1
    assert metadata(data)["replacement"] == "unavailable"
    assert metadata(data, 3)["rename"] == "unavailable"
    report = representation_coverage(data, source_matches=False)
    assert report.inventory_complete and not report.source_matches
    assert M1 not in report.model_dump_json()


def test_every_nested_metadata_model_is_frozen_strict_and_extra_forbidden() -> None:
    report = representation_coverage(inventory(), source_matches=True)
    models: list[BaseModel] = []

    def visit(value: Any) -> None:
        if isinstance(value, BaseModel):
            models.append(value)
            for name in type(value).model_fields:
                visit(getattr(value, name))
        elif isinstance(value, tuple):
            for item in value:
                visit(item)

    visit(report)
    for model in models:
        assert model.model_config["strict"]
        assert model.model_config["extra"] == "forbid"
        with pytest.raises(ValidationError):
            type(model).model_validate(
                {**model.model_dump(), "private-extra": "private-input"}
            )
        with pytest.raises(ValidationError):
            setattr(model, next(iter(type(model).model_fields)), "private-input")
    raw = report.model_dump()
    raw["positions"][1]["unknown_count"] = True
    with pytest.raises(ValidationError):
        RepresentationCoverage.model_validate(raw)
    raw = report.model_dump(mode="json")
    raw["positions"][1]["parameters"][0]["parameter_id"] = "private-id"
    with pytest.raises(ValidationError) as caught:
        RepresentationCoverage.model_validate_json(json.dumps(raw))
    assert "private-id" not in str(caught.value)


def hostile_inventory() -> dict[str, Any]:
    data = inventory()
    data["features"][1]["btType"] = "private-feature-type"
    for feature in data["features"]:
        feature["name"] = "private-name https://private.invalid/name"
        feature["private-raw"] = {"token": "private-token", "coordinates": [123.456]}
        for item in feature["parameters"]:
            item["nodeId"] = "private-node"
            if "queries" in item:
                item["queries"] = [
                    {
                        "btType": "BTMIndividualQuery-138",
                        "queryString": "private-query",
                        "deterministicIds": ["private-geometry-id"],
                    },
                    {
                        "btType": "BTMIndividualSketchRegionQuery-140",
                        "featureId": "private-feature-id",
                    },
                    {"btType": "private-query-type"},
                    {},
                    {"btType": None},
                    {"btType": []},
                    "private-query-object",
                ]
            elif "expression" in item:
                item["expression"] = "123.456 mm"
                item["btType"] = "private-quantity-type"
            else:
                item["value"] = "private-provider-value"
                item["enumName"] = "private-enum-name"
        feature["parameters"].append(
            {
                "parameterId": "private-unknown-id https://private.invalid/id",
                "btType": "private-param-type",
            }
        )
    return data


def test_hostile_provider_data_cannot_escape_pinned_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    provider = Provider()
    provider.data = hostile_inventory()
    original = deepcopy(provider.data)
    with (
        httpx.Client(transport=httpx.MockTransport(provider.handle)) as transport,
        caplog.at_level(logging.WARNING),
    ):
        safe_edit.CoverageClient(
            enabled_settings(), transport, "private-token"
        ).compare(REF)
    reports = [
        json.loads(r.message.split("metadata=")[1])
        for r in caplog.records
        if r.message.startswith("safe_edit_representation_coverage ")
    ]
    assert len(reports) == 2
    for report in reports:
        assert [p["category"] for p in report["positions"]] == [
            "sketch",
            "extrude",
            "fillet",
        ]
        assert report["positions"][1]["unknown_count"] == 1
        assert report["positions"][1]["replacement"] == "unsupported_shape"
        query = known(report["positions"][2], "entities")["query"]
        assert set(query["item_types"]) == {
            "individual_query",
            "sketch_region_query",
            "other",
            "missing",
            "null",
            "wrong_type",
        }
    for private in (
        "private-",
        "123.456",
        "synthetic-feature-",
        REF.documentId,
        REF.workspaceId,
        REF.elementId,
        M0,
        "https://",
        json.dumps(original),
    ):
        assert private not in caplog.text
    assert provider.data == original
    assert len(provider.calls) == 4 and all(c.method == "GET" for c in provider.calls)


@pytest.mark.parametrize(
    "enabled,environment,writes",
    [
        (False, "development", False),
        (True, "development", True),
        (True, "production", False),
        (True, "test", False),
    ],
)
def test_runtime_guards_prevent_projection_credentials_and_provider_io(
    harness: Harness,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    enabled: bool,
    environment: str,
    writes: bool,
) -> None:
    settings = harness.runtime.settings
    settings.forge_safe_edit_diagnostics_enabled = enabled
    settings.environment = environment  # type: ignore[assignment]
    settings.forge_cad_writes_enabled = writes

    def forbidden(*_: Any, **__: Any) -> Any:
        raise AssertionError("guarded diagnostic executed")

    monkeypatch.setattr(safe_edit, "representation_coverage", forbidden)
    monkeypatch.setattr(safe_edit, "shape_validation_coverage", forbidden)
    monkeypatch.setattr(
        harness.runtime.tokens, "get_valid_onshape_access_token", forbidden
    )
    with (
        httpx.Client(transport=httpx.MockTransport(forbidden)) as transport,
        caplog.at_level(logging.WARNING),
    ):
        safe_edit.probe(harness.runtime, transport, REF, "synthetic-user")
        assert (
            safe_edit.CoverageClient(
                settings, transport, "private-token"
            )._representation(inventory(), source_matches=True)
            is None
        )
    assert not caplog.records


@pytest.mark.parametrize(
    "fault",
    [
        "changed_head",
        "disabled_before_log",
        "writes_on_before_log",
        "production_before_log",
    ],
)
def test_no_representation_log_after_head_or_flag_changes(
    fault: str, caplog: pytest.LogCaptureFixture
) -> None:
    settings = enabled_settings()
    provider = Provider()
    provider.data = inventory()
    heads = 0

    def read(request: httpx.Request) -> httpx.Response:
        nonlocal heads
        response = provider.handle(request)
        if request.url.path.endswith("currentmicroversion"):
            heads += 1
            if heads == 2:
                if fault == "changed_head":
                    return httpx.Response(200, json={"microversion": M1})
                if fault == "disabled_before_log":
                    settings.forge_safe_edit_diagnostics_enabled = False
                elif fault == "writes_on_before_log":
                    settings.forge_cad_writes_enabled = True
                else:
                    settings.environment = "production"
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
    assert "safe_edit_representation_coverage" not in caplog.text
    assert "safe_edit_standard_parameter_coverage" not in caplog.text
    assert "safe_edit_standard_shape_" not in caplog.text
    assert provider.writes == 0


def test_inspector_probe_reuses_reads_has_no_public_metadata_or_authority(
    harness: Harness, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    user = harness.login()
    set_scope(harness, user, "OAuth2ReadPII OAuth2Read")
    harness.runtime.settings.environment = "development"
    harness.runtime.settings.forge_safe_edit_diagnostics_enabled = True
    assert not harness.runtime.settings.forge_cad_writes_enabled
    provider = Provider()
    provider.data = inventory()
    normal = CadProvider()
    calls: list[httpx.Request] = []

    def forbidden(*_: Any, **__: Any) -> Any:
        raise AssertionError("representation diagnostic reached authority")

    for module, name in (
        (plan_service, "discover"),
        (plan_service, "prepare"),
        (plan_service, "approve"),
        (plan_storage, "store"),
        (SafeEditClient, "execute_operation"),
        (SafeEditClient, "suppress_terminal_fillet"),
    ):
        monkeypatch.setattr(module, name, forbidden)

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
    assert response.status_code == 200
    assert (
        len(calls) == 13
    )  # Existing Inspector + compare + structural/body probe budget.
    assert caplog.text.count("safe_edit_representation_coverage noSketchGeometry=") == 2
    assert caplog.text.count("safe_edit_standard_shape_failure category=") == 4
    for field in (
        "safe_edit_representation",
        "parameter_shape_matches_registry",
        "unknown_count",
        "replacement",
        "rename",
        "standard_parameter_coverage",
        "source_vocabulary_only_no_edit_authority",
        "standard_shape_failure",
        "standard_shape_validation",
    ):
        assert field not in response.text and all(
            field not in k.lower() for k in response.headers
        )
    assert provider.writes == 0
    with harness.runtime.sessions() as db:
        assert db.scalar(select(func.count()).select_from(WriteRecord)) == 0
        assert db.scalar(select(func.count()).select_from(WriteFence)) == 0
