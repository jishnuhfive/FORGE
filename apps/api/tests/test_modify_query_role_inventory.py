"""All-role evidence is bounded/read-only; synthetic filters grant no authority."""

import json
import logging
from copy import deepcopy
from typing import Any, get_args

import httpx2 as httpx
import pytest
from conftest import Harness
from pydantic import ValidationError
from sqlalchemy import func, select
from test_cad_read import REF, CadProvider, set_scope
from test_modify_filter_contracts import ordinary_inventory
from test_modify_plan import inventory
from test_modify_representation import enabled_settings
from test_modify_ui_conformance import param, replacement_rejects
from test_safe_edit import M0, M1, Provider

from forge_api.cad_edits import plan_service, plan_storage
from forge_api.cad_edits.domain import EditError, fingerprint
from forge_api.db.models import WriteFence, WriteRecord
from forge_api.integrations.onshape.dev import query_roles, safe_edit
from forge_api.integrations.onshape.dev.query_roles import (
    MAX_FEATURE_LOG_CHARS,
    MAX_PARAMETERS,
    MAX_ROLE_LOG_CHARS,
    QueryRole,
    query_role_inventory,
    query_role_text,
)
from forge_api.integrations.onshape.dev.standard_parameters import VOCABULARY
from forge_api.integrations.onshape.dev.standard_shape_failure import diagnose_ui_shape
from forge_api.integrations.onshape.query_filter_evidence import (
    CATEGORIES,
    MAX_DIAGNOSTIC_DEPTH,
    MAX_LEAF_FIELDS,
    MAX_NODES,
    MAX_SIGNATURE_CHARS,
    DiagnosticQueryFilterSummary,
    FilterCategory,
    LeafEvidence,
    LeafField,
    LeafFieldState,
    LeafState,
    leaf_states_text,
    unproven_filter_summary,
)
from forge_api.integrations.onshape.standard_shape_contract import ShapeCategory
from forge_api.integrations.onshape.write_client import SafeEditClient

# Independent current source/full-fixture expectations; production derives its set.
EXTRUDE = (
    "entities",
    "surfaceEntities",
    "wallShape",
    "endBoundEntityFace",
    "endBoundEntityBody",
    "endBoundEntityVertex",
    "secondDirectionBoundEntityFace",
    "secondDirectionBoundEntityBody",
    "secondDirectionBoundEntityVertex",
    "extrudeDirection",
    "startOffsetEntity",
    "booleanScope",
    "booleanSurfaceScope",
)
FILLET = (
    "entities",
    "side1Face",
    "side2Face",
    "centerFaces",
    "startPartialEntity",
    "endPartialEntity",
    "keepEdges",
    "smoothCornerExceptions",
)
EXPECTED = {2: EXTRUDE, 3: FILLET}
HOSTILE = "private-provider-value\nall_roles_inspected=true"


def both(left: Any, right: Any) -> dict[str, Any]:
    return {"btType": "BTAndFilter-110", "operand1": left, "operand2": right}


def dormant_filter(position: int) -> dict[str, Any]:
    entity = {
        "btType": "BTEntityTypeFilter-124",
        "entityType": "EDGE" if position == 2 else "FACE",
    }
    construction = {"btType": "BTConstructionObjectFilter-113", "isConstruction": False}
    sketch = {
        "btType": "BTSketchObjectFilter-184",
        "isSketchObject": position == 2,
        "objectType": "ANY_SKETCH_OBJECT" if position == 2 else "NOT_SKETCH_OBJECT",
    }
    modifiable = {"btType": "BTModifiableEntityOnlyFilter-1593", "modifiableOnly": True}
    if position == 2:
        return both(both(both(entity, sketch), modifiable), construction)
    return both(
        both(both(both(entity, construction), sketch), modifiable),
        {"btType": "BTActiveSheetMetalFilter-2944", "isFromActiveSheetMetal": False},
    )


def all_role_inventory() -> dict[str, Any]:
    data = ordinary_inventory()
    # Only surfaceEntities/side1Face reconstruct new reported evidence. The same
    # filters on other empty roles are invented enumeration coverage, not captures.
    for position, keys in EXPECTED.items():
        for key in keys[1:]:
            param(data, position, key)["filter"] = dormant_filter(position)
    return data


@pytest.mark.parametrize("position", [2, 3])
@pytest.mark.parametrize("filters", [False, True])
def test_every_present_query_role_is_reported_once_in_source_order(
    position: int, filters: bool
) -> None:
    data = all_role_inventory() if filters else ordinary_inventory()
    original = deepcopy(data)
    reports = query_role_inventory(data)
    report = reports[position - 2]
    assert tuple(r.parameter for r in report.roles) == EXPECTED[position]
    assert len({r.parameter for r in report.roles}) == len(EXPECTED[position])
    assert report.summary.total_query_roles_discovered == len(EXPECTED[position])
    assert report.summary.total_query_roles_inspected == len(EXPECTED[position])
    assert report.summary.all_roles_inspected
    assert not any(
        (
            report.summary.any_malformed,
            report.summary.any_unexpected_fields,
            report.summary.any_uninspected,
            report.summary.any_truncated,
        )
    )
    for role in report.roles:
        assert role.occurrences == 1
        assert role.query_state == (
            "nonempty" if role.parameter == "entities" else "empty"
        )
        assert role.query_item_count == (1 if role.parameter == "entities" else 0)
        assert role.filter_present is (filters or role.parameter == "entities")
        if role.filter_present:
            assert role.query_filter is not None and role.query_filter.node_count > 1
            assert "signature=and(" in query_role_text(role)
    data["features"][position - 1]["parameters"].reverse()
    assert query_role_inventory(data) == reports
    data["features"][position - 1]["parameters"].reverse()
    assert data == original


@pytest.mark.parametrize("position,key", [(2, "surfaceEntities"), (3, "side1Face")])
def test_reported_dormant_filter_is_inspected_despite_empty_queries_and_first_failure(
    position: int, key: str
) -> None:
    data = all_role_inventory()
    report = query_role_inventory(data)[position - 2]
    role = next(r for r in report.roles if r.parameter == key)
    f = role.query_filter
    assert f is not None and role.query_state == "empty" and role.query_item_count == 0
    assert f.node_count == (7 if position == 2 else 9)
    assert f.max_depth == (4 if position == 2 else 5)
    assert "".join(f.signature) == (
        "and(and(and(entity_type,sketch_object),modifiable_entity_only),construction)"
        if position == 2
        else "and(and(and(and(entity_type,construction),sketch_object),"
        "modifiable_entity_only),active_sheet_metal)"
    )
    assert "modifiable_entity_only=true" in leaf_states_text(f)
    category: ShapeCategory = "extrude" if position == 2 else "fillet"
    first = diagnose_ui_shape(data["features"][position - 1], category)
    assert first.failure is not None and first.failure.parameter == key
    assert first.failure.reason == "query_filter_unproven"
    assert len(report.roles) == len(EXPECTED[position])
    replacement_rejects(data, position)


@pytest.mark.parametrize("position", [2, 3])
def test_absent_optional_role_is_not_invented(position: int) -> None:
    data = all_role_inventory()
    params = data["features"][position - 1]["parameters"]
    params.remove(param(data, position, EXPECTED[position][-1]))
    report = query_role_inventory(data)[position - 2]
    assert tuple(r.parameter for r in report.roles) == EXPECTED[position][:-1]
    assert report.summary.total_query_roles_discovered == len(EXPECTED[position]) - 1
    assert report.summary.all_roles_inspected


@pytest.mark.parametrize("source_kind", [True, False])
def test_discovery_uses_source_kind_or_actual_provider_representation(
    source_kind: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = all_role_inventory()
    if source_kind:
        monkeypatch.setitem(VOCABULARY["extrude"], "depth", "query")
    else:
        item = param(data, 2, "depth")
        item.clear()
        item.update(
            parameterId="depth",
            btType="BTMParameterQueryList-148",
            queries=[],
            filter=dormant_filter(2),
        )
    report = query_role_inventory(data)[0]
    assert (
        len(report.roles) == 14
        and sum(r.parameter == "depth" for r in report.roles) == 1
    )
    assert (
        report.summary.any_malformed
    )  # Source/provider disagreement is evidence only.


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, "null"),
        ({}, "wrong_type"),
        (False, "wrong_type"),
        (HOSTILE, "wrong_type"),
    ],
)
def test_malformed_query_list_does_not_prevent_filter_inspection(
    value: Any, expected: str
) -> None:
    data = all_role_inventory()
    param(data, 2, "surfaceEntities")["queries"] = value
    report = query_role_inventory(data)[0]
    role = report.roles[1]
    assert role.query_state == expected and role.query_item_count is None
    assert role.query_filter is not None and role.query_filter.node_count == 7
    assert role.malformed and report.summary.any_malformed
    assert HOSTILE not in report.model_dump_json()


@pytest.mark.parametrize(
    "fault",
    [
        "missing_queries",
        "wrong_parameter_type",
        "parameter_extra",
        "filter_extra",
        "unknown_type",
        "opaque_type",
        "null_filter",
        "missing_operand",
        "null_operand",
        "deep",
        "wide",
        "cycle",
    ],
)
def test_role_faults_are_closed_flagged_and_cannot_hide_later_roles(fault: str) -> None:
    data = all_role_inventory()
    item = param(data, 2, "surfaceEntities")
    tree = item["filter"]
    if fault == "missing_queries":
        del item["queries"]
    elif fault == "wrong_parameter_type":
        item["btType"] = HOSTILE
    elif fault == "parameter_extra":
        item[HOSTILE] = item  # Unknown values must not be traversed.
    elif fault == "filter_extra":
        tree[HOSTILE] = tree
    elif fault in ("unknown_type", "opaque_type"):
        tree["btType"] = HOSTILE if fault == "unknown_type" else "BTFeatureFilter-127"
    elif fault == "null_filter":
        item["filter"] = None
    elif fault == "missing_operand":
        del tree["operand2"]
    elif fault == "null_operand":
        tree["operand2"] = None
    elif fault == "deep":
        for _ in range(2000):
            tree = {"btType": "BTNotFilter-165", "operand": tree}
        item["filter"] = tree
    elif fault == "wide":
        for _ in range(7):
            tree = both(tree, tree)
        item["filter"] = tree
    else:
        tree["operand1"] = tree
    report = query_role_inventory(data)[0]
    role = report.roles[1]
    assert (
        len(report.roles) == 13 and report.roles[-1].parameter == "booleanSurfaceScope"
    )
    if fault in ("parameter_extra", "filter_extra"):
        assert role.unexpected_fields and role.uninspected
        assert (
            report.summary.any_unexpected_fields
            and not report.summary.all_roles_inspected
        )
    elif fault in ("unknown_type", "opaque_type"):
        assert role.uninspected and report.summary.any_uninspected
        assert not report.summary.all_roles_inspected
    elif fault in ("deep", "wide", "cycle", "missing_operand"):
        assert role.truncated and report.summary.any_truncated
        assert not report.summary.all_roles_inspected
    else:
        assert role.malformed and report.summary.any_malformed
    assert role.query_filter is None or (
        role.query_filter.node_count <= 64
        and role.query_filter.max_depth <= MAX_DIAGNOSTIC_DEPTH
    )
    assert HOSTILE not in report.model_dump_json() and HOSTILE not in query_role_text(
        role
    )


@pytest.mark.parametrize("identity", [HOSTILE, None, [HOSTILE]])
def test_unknown_query_role_identity_prevents_completeness_without_leaking(
    identity: Any,
) -> None:
    data = all_role_inventory()
    data["features"][1]["parameters"].append(
        {
            "parameterId": identity,
            "btType": "BTMParameterQueryList-148",
            "queries": [],
            "filter": dormant_filter(2),
        }
    )
    report = query_role_inventory(data)[0]
    assert len(report.roles) == 13
    assert report.summary.total_query_roles_discovered == 14
    assert report.summary.total_query_roles_inspected == 13
    assert report.summary.unrecognized_query_parameters == 1
    assert report.summary.any_uninspected and not report.summary.all_roles_inspected
    assert HOSTILE not in report.model_dump_json()


def test_duplicate_role_is_reported_once_without_selecting_one_payload() -> None:
    data = all_role_inventory()
    duplicate = deepcopy(param(data, 2, "surfaceEntities"))
    duplicate["filter"] = {"btType": HOSTILE}
    data["features"][1]["parameters"].append(duplicate)
    report = query_role_inventory(data)[0]
    role = report.roles[1]
    assert len(report.roles) == 13 and role.occurrences == 2
    assert role.query_filter is None and role.query_state is None
    assert role.malformed and role.uninspected and role.truncated
    assert report.summary.total_query_roles_inspected == 12
    assert not report.summary.all_roles_inspected


@pytest.mark.parametrize("params", [None, {}, [None], [HOSTILE]])
def test_malformed_parameter_collection_cannot_report_complete_roles(
    params: Any,
) -> None:
    data = all_role_inventory()
    data["features"][1]["parameters"] = params
    report = query_role_inventory(data)[0]
    assert report.summary.any_malformed and report.summary.any_uninspected
    assert not report.summary.all_roles_inspected


def test_parameter_and_query_counts_are_capped_without_reading_query_contents() -> None:
    data = all_role_inventory()
    param(data, 2, "surfaceEntities")["queries"] = [{HOSTILE: HOSTILE}] * 2001
    data["features"][1]["parameters"] += [
        {"parameterId": HOSTILE, "queries": []}
    ] * 2000
    report = query_role_inventory(data)[0]
    assert report.summary.parameter_count_capped and report.summary.any_truncated
    assert report.summary.total_query_roles_discovered <= MAX_PARAMETERS
    assert not report.summary.all_roles_inspected
    role = report.roles[1]
    assert role.query_item_count == 2000 and role.query_count_capped and role.truncated
    assert HOSTILE not in report.model_dump_json()


def test_schema_maximum_log_size_and_whole_feature_output_are_bounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = unproven_filter_summary(dormant_filter(2)).model_dump()
    category = max(get_args(FilterCategory), key=len)
    field = max(get_args(LeafField), key=len)
    state = max(get_args(LeafState), key=len)
    raw.update(
        signature=(category,) * (MAX_SIGNATURE_CHARS // len(category)),
        categories=(category,) * len(CATEGORIES),
        leaf_states=tuple(
            LeafEvidence(
                visit=64,
                fields=(LeafFieldState(field=field, state=state),) * MAX_LEAF_FIELDS,
            )
            for _ in range(MAX_NODES)
        ),
    )
    maximum = DiagnosticQueryFilterSummary.model_validate(raw)
    monkeypatch.setattr(query_roles, "diagnostic_filter_summary", lambda _: maximum)
    report = query_role_inventory(all_role_inventory())[0]
    assert len(report.roles) == 13 and any(r.query_filter is None for r in report.roles)
    assert report.summary.any_truncated and report.summary.any_uninspected
    assert not report.summary.all_roles_inspected
    lines = [
        "safe_edit_query_role noSketchGeometry=false position=20 category=extrude "
        + query_role_text(r)
        for r in report.roles
    ]
    assert all(len(line) < MAX_ROLE_LOG_CHARS for line in lines)
    assert (
        sum(map(len, lines)) + len(report.summary.model_dump_json()) + 128
        < MAX_FEATURE_LOG_CHARS
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("parameter", HOSTILE),
        ("query_state", HOSTILE),
        ("occurrences", HOSTILE),
        ("query_filter", {HOSTILE: HOSTILE}),
    ],
)
def test_projection_schema_cannot_contain_arbitrary_provider_text(
    field: str, value: Any
) -> None:
    raw = query_role_inventory(all_role_inventory())[0].roles[0].model_dump()
    raw[field] = value
    with pytest.raises(ValidationError) as caught:
        QueryRole.model_validate(raw)
    assert HOSTILE not in str(caught.value)


@pytest.mark.parametrize(
    "fault", ["diagnostics", "writes", "environment", "source", "incomplete"]
)
def test_projection_guard_cannot_be_bypassed(
    fault: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = enabled_settings()
    data = all_role_inventory()
    if fault == "diagnostics":
        settings.forge_safe_edit_diagnostics_enabled = False
    elif fault == "writes":
        settings.forge_cad_writes_enabled = True
    elif fault == "environment":
        settings.environment = "production"
    elif fault == "incomplete":
        data["isComplete"] = False

    def forbidden(*_: Any) -> Any:
        raise AssertionError("Guarded inventory ran")

    monkeypatch.setattr(safe_edit, "query_role_inventory", forbidden)
    with httpx.Client(transport=httpx.MockTransport(forbidden)) as transport:
        assert (
            safe_edit.CoverageClient(settings, transport, "private-token")._query_roles(
                data, source_matches=fault != "source"
            )
            is None
        )


@pytest.mark.parametrize("fault", ["head", "diagnostics", "writes", "environment"])
def test_no_query_inventory_logs_after_head_or_guard_changes(
    fault: str, caplog: pytest.LogCaptureFixture
) -> None:
    settings = enabled_settings()
    provider = Provider()
    provider.data = all_role_inventory()
    heads = 0

    def read(request: httpx.Request) -> httpx.Response:
        nonlocal heads
        response = provider.handle(request)
        if request.url.path.endswith("currentmicroversion"):
            heads += 1
            if heads == 2:
                if fault == "head":
                    return httpx.Response(200, json={"microversion": M1})
                if fault == "diagnostics":
                    settings.forge_safe_edit_diagnostics_enabled = False
                elif fault == "writes":
                    settings.forge_cad_writes_enabled = True
                else:
                    settings.environment = "production"
        return response

    with (
        httpx.Client(transport=httpx.MockTransport(read)) as transport,
        caplog.at_level(logging.WARNING),
    ):
        client = safe_edit.CoverageClient(settings, transport, "private-token")
        if fault == "head":
            with pytest.raises(EditError, match="model_changed"):
                client.compare(REF)
        else:
            client.compare(REF)
    assert "safe_edit_query_role" not in caplog.text and provider.writes == 0


def test_each_inventory_record_rechecks_the_write_off_guard(
    caplog: pytest.LogCaptureFixture,
) -> None:
    settings = enabled_settings()
    provider = Provider()
    provider.data = all_role_inventory()

    class DisableAfterFirst(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            if record.getMessage().startswith("safe_edit_query_role "):
                settings.forge_safe_edit_diagnostics_enabled = False

    handler = DisableAfterFirst()
    safe_edit.logger.addHandler(handler)
    try:
        with (
            httpx.Client(transport=httpx.MockTransport(provider.handle)) as transport,
            caplog.at_level(logging.WARNING),
        ):
            safe_edit.CoverageClient(settings, transport, "private-token").compare(REF)
    finally:
        safe_edit.logger.removeHandler(handler)
    assert (
        sum(r.message.startswith("safe_edit_query_role ") for r in caplog.records) == 1
    )
    assert "safe_edit_query_role_summary" not in caplog.text


def test_inspector_inventory_is_private_read_only_and_adds_zero_gets(
    harness: Harness, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    user = harness.login()
    set_scope(harness, user, "OAuth2ReadPII OAuth2Read")
    settings = harness.runtime.settings
    settings.environment = "development"
    settings.forge_safe_edit_diagnostics_enabled = True
    assert not settings.forge_cad_writes_enabled
    provider = Provider()
    provider.data = all_role_inventory()
    for position, keys in EXPECTED.items():
        for key in keys:
            for query in param(provider.data, position, key)["queries"]:
                query["queryString"] = HOSTILE
    before = fingerprint(provider.data)
    normal = CadProvider()
    calls: list[httpx.Request] = []

    def forbidden(*_: Any) -> Any:
        raise AssertionError("Read-only inventory reached mutation/approval authority")

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
    assert response.status_code == 200 and len(calls) == 13
    rows = [
        r.message
        for r in caplog.records
        if r.message.startswith("safe_edit_query_role ")
    ]
    summaries = [
        json.loads(r.message.split("metadata=", 1)[1])
        for r in caplog.records
        if r.message.startswith("safe_edit_query_role_summary ")
    ]
    assert len(rows) == 42 and len(summaries) == 4
    for mode in ("true", "false"):
        for position, keys in EXPECTED.items():
            group = [
                line
                for line in rows
                if f"noSketchGeometry={mode} position={position} " in line
            ]
            assert [
                line.split("parameter=", 1)[1].split()[0] for line in group
            ] == list(keys)
    assert [s["total_query_roles_discovered"] for s in summaries] == [13, 8, 13, 8]
    assert all(s["all_roles_inspected"] for s in summaries)
    assert "parameter=surfaceEntities reason=query_filter_unproven" in caplog.text
    assert "parameter=side1Face reason=query_filter_unproven" in caplog.text
    assert "safe_edit_probe outcome=eligible_no_proposal_no_write" in caplog.text
    for forbidden_text in (
        HOSTILE,
        "private-",
        "BTAndFilter",
        "BTMParameterQueryList",
        "MODEL_ONLY",
        REF.documentId,
        REF.workspaceId,
        REF.elementId,
        M0,
        "synthetic-feature-",
    ):
        assert forbidden_text not in caplog.text
    assert "safe_edit_query_role" not in response.text
    assert not any("query_role" in header.lower() for header in response.headers)
    assert provider.writes == 0 and fingerprint(provider.data) == before
    with harness.runtime.sessions() as db:
        assert db.scalar(select(func.count()).select_from(WriteRecord)) == 0
        assert db.scalar(select(func.count()).select_from(WriteFence)) == 0


def test_diagnostics_do_not_change_historical_or_current_eligibility() -> None:
    data = all_role_inventory()
    before = fingerprint(data)
    query_role_inventory(data)
    assert fingerprint(data) == before
    for position in (2, 3):
        replacement_rejects(data, position)
    # Historical profiles still have only their original entities role.
    assert [
        tuple(r.parameter for r in f.roles) for f in query_role_inventory(inventory())
    ] == [("entities",), ("entities",)]


@pytest.mark.parametrize("data", [None, {}, {"features": [None] * 21}])
def test_feature_inventory_bound_is_enforced(data: Any) -> None:
    with pytest.raises(EditError, match="invalid_provider_response"):
        query_role_inventory(data)
