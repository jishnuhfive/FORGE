"""Human-evidence-shaped synthetic contracts; all CAD traffic stays mocked."""

import json
import logging
from copy import deepcopy
from pathlib import Path
from typing import Any

import httpx2 as httpx
import pytest
from conftest import Harness
from sqlalchemy import func, select
from test_cad_read import REF, CadProvider, set_scope
from test_modify_common_metadata import OPERATIONS
from test_modify_conformance import operation_for, plan_for
from test_modify_plan import OP, PlanProvider, approve, inventory, target
from test_modify_query_filter_evidence import QUERY_ROLES
from test_modify_representation import enabled_settings, metadata
from test_modify_ui_conformance import param, replacement_rejects, ui_inventory
from test_safe_edit import M0, M1, Provider, bodies, config, running

from forge_api.cad_edits import plan_service
from forge_api.cad_edits.domain import EditError
from forge_api.cad_edits.plans import ResolvedOperation
from forge_api.db.models import WriteFence, WriteRecord
from forge_api.integrations.onshape import edit_registry, standard_edit_shapes
from forge_api.integrations.onshape.current_ui_filters import (
    matches_extrude_entities_filter,
    matches_fillet_entities_filter,
)
from forge_api.integrations.onshape.dev.standard_shape_failure import diagnose_ui_shape
from forge_api.integrations.onshape.edit_registry import change
from forge_api.integrations.onshape.modify_evidence import (
    project_modify_evidence,
    verify_operation,
)
from forge_api.integrations.onshape.query_filter_evidence import (
    leaf_states_text,
    unproven_filter_summary,
)
from forge_api.integrations.onshape.standard_edit_shapes import ui_quantity_parameter
from forge_api.integrations.onshape.standard_shape_contract import (
    ShapeCategory,
    ShapeValidationError,
)
from forge_api.integrations.onshape.write_client import SafeEditClient

FIXTURES = json.loads(
    (Path(__file__).parent / "fixtures/modify_observed_filters.json").read_text()
)
ROLES = ("extrude", "fillet")
HOSTILE = "private-provider-string\nreason=exact_match"
MISSING = object()


def ordinary_inventory() -> dict[str, Any]:
    data = ui_inventory()
    for position, role in ((2, "extrude"), (3, "fillet")):
        param(data, position, "entities")["filter"] = deepcopy(FIXTURES[role]["filter"])
    return data


def nodes(tree: Any) -> list[tuple[tuple[str, ...], Any]]:
    result: list[tuple[tuple[str, ...], Any]] = []
    stack: list[tuple[tuple[str, ...], Any]] = [((), tree)]
    while stack:
        path, node = stack.pop()
        result.append((path, node))
        for key in ("operand2", "operand1"):
            if key in node:
                stack.append(((*path, key), node[key]))
    return result


def at(tree: Any, path: tuple[str, ...]) -> Any:
    for key in path:
        tree = tree[key]
    return tree


NODE_PATHS = [
    (role, path) for role in ROLES for path, _ in nodes(FIXTURES[role]["filter"])
]
BINARY_PATHS = [
    (role, path)
    for role, path in NODE_PATHS
    if "operand1" in at(FIXTURES[role]["filter"], path)
]
ALTERNATES: dict[str, list[Any]] = {
    "allows": ["MODEL_ONLY", "MODEL_AND_FLATTENED", "FLATTENED_ONLY"],
    "objectType": ["ANY_SKETCH_OBJECT", "NOT_SKETCH_OBJECT", "USER_ENTITY"],
    "entityType": ["FACE", "EDGE", "VERTEX", "BODY"],
    "geometryType": ["LINE", "CYLINDER"],
    "edgeTopology": ["ONE_SIDED", "WIRE", "LAMINAR"],
    "smDefinitionEntityType": ["EDGE", "FACE"],
}
LEAF_DEVIATIONS = []
for role, path in NODE_PATHS:
    node = at(FIXTURES[role]["filter"], path)
    for field, current in node.items():
        if field == "btType" or field.startswith("operand"):
            continue
        cases = [MISSING, None, [], {}, 0, 1, "true", "false", "UNKNOWN", HOSTILE]
        cases += [not current] if type(current) is bool else ALTERNATES[field]
        for index, value in enumerate(cases):
            if type(value) is type(current) and value == current:
                continue
            LEAF_DEVIATIONS.append(
                pytest.param(
                    role, path, field, value, id=f"{role}-{path}-{field}-{index}"
                )
            )


def assert_rejected(role: str, tree: Any) -> None:
    position = 2 if role == "extrude" else 3
    predicate = (
        matches_extrude_entities_filter
        if role == "extrude"
        else matches_fillet_entities_filter
    )
    assert not predicate(tree)
    data = ordinary_inventory()
    param(data, position, "entities")["filter"] = tree
    with pytest.raises(ShapeValidationError) as caught:
        ui_quantity_parameter(
            data["features"][position - 1], "depth" if position == 2 else "radius"
        )
    assert caught.value.failure.reason == "query_filter_unproven"
    assert str(caught.value) == "unsupported_target"
    assert caught.value.query_filter is not None
    assert HOSTILE not in caught.value.query_filter.model_dump_json()
    replacement_rejects(data, position)


@pytest.mark.parametrize("role", ROLES)
def test_exact_reported_structure_and_typed_leaf_values_pass_only_their_role(
    role: str,
) -> None:
    raw = deepcopy(FIXTURES[role]["filter"])
    first = deepcopy(raw)
    own = (
        matches_extrude_entities_filter
        if role == "extrude"
        else matches_fillet_entities_filter
    )
    other = (
        matches_fillet_entities_filter
        if role == "extrude"
        else matches_extrude_entities_filter
    )
    assert own(raw) and not other(raw)
    summary = unproven_filter_summary(raw)
    assert "".join(summary.signature) == FIXTURES[role]["signature"]
    assert leaf_states_text(summary) == FIXTURES[role]["leaf_states"]
    assert summary.node_count == FIXTURES[role]["nodes"]
    assert summary.max_depth == FIXTURES[role]["depth"]
    assert not any(
        (
            summary.malformed,
            summary.missing_operand,
            summary.unexpected_fields,
            summary.uninspected,
            summary.truncated,
            summary.signature_truncated,
        )
    )
    # JSON object key order is immaterial; operand order is not.
    for _, node in nodes(raw):
        values = tuple(reversed(tuple(node.items())))
        node.clear()
        node.update(values)
    assert own(raw) and raw == first


@pytest.mark.parametrize("role,path,field,value", LEAF_DEVIATIONS)
def test_every_required_leaf_value_is_exact_typed_present_and_closed(
    role: str, path: tuple[str, ...], field: str, value: Any
) -> None:
    tree = deepcopy(FIXTURES[role]["filter"])
    node = at(tree, path)
    if value is MISSING:
        del node[field]
    else:
        node[field] = value
    assert_rejected(role, tree)


@pytest.mark.parametrize("role,path", NODE_PATHS)
@pytest.mark.parametrize(
    "fault", ["missing_type", "unknown_type", "opaque_type", "extra", "null", "array"]
)
def test_every_node_has_an_exact_closed_schema(
    role: str, path: tuple[str, ...], fault: str
) -> None:
    tree = deepcopy(FIXTURES[role]["filter"])
    node = at(tree, path)
    if fault == "missing_type":
        del node["btType"]
    elif fault == "unknown_type":
        node["btType"] = HOSTILE
    elif fault == "opaque_type":
        node["btType"] = "BTQueryFilter-183"
    elif fault == "extra":
        node[HOSTILE] = {HOSTILE: HOSTILE}
    else:
        replacement: list[Any] | None = None if fault == "null" else []
        if path:
            at(tree, path[:-1])[path[-1]] = replacement
        else:
            tree = replacement
    assert_rejected(role, tree)


@pytest.mark.parametrize("role,path", BINARY_PATHS)
@pytest.mark.parametrize(
    "fault", ["swap", "missing", "extra", "operator", "additional_node"]
)
def test_all_operator_positions_and_arities_are_exact(
    role: str, path: tuple[str, ...], fault: str
) -> None:
    tree = deepcopy(FIXTURES[role]["filter"])
    node = at(tree, path)
    if fault == "swap":
        node["operand1"], node["operand2"] = node["operand2"], node["operand1"]
    elif fault == "missing":
        del node["operand2"]
    elif fault == "extra":
        node["operand3"] = deepcopy(node["operand2"])
    elif fault == "operator":
        node["btType"] = (
            "BTOrFilter-167"
            if node["btType"] == "BTAndFilter-110"
            else "BTAndFilter-110"
        )
    else:
        node["operand1"] = {"btType": "BTNotFilter-165", "operand": node["operand1"]}
    assert_rejected(role, tree)


@pytest.mark.parametrize("role", ROLES)
def test_equivalent_reassociation_with_the_same_leaf_order_is_not_accepted(
    role: str,
) -> None:
    tree = deepcopy(FIXTURES[role]["filter"])
    node = tree["operand1"]["operand1"] if role == "extrude" else tree
    left = node["operand1"]
    node["operand1"] = left["operand1"]
    node["operand2"] = {
        "btType": "BTAndFilter-110",
        "operand1": left["operand2"],
        "operand2": node["operand2"],
    }
    assert_rejected(role, tree)


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("fault", ["deep", "wide", "cycle", "summary_instead_of_tree"])
def test_clipped_or_uninspected_evidence_cannot_grant_authority(
    role: str, fault: str
) -> None:
    tree = deepcopy(FIXTURES[role]["filter"])
    if fault == "deep":
        for _ in range(2000):
            tree = {"btType": "BTNotFilter-165", "operand": tree}
    elif fault == "wide":
        for _ in range(7):
            tree = {"btType": "BTAndFilter-110", "operand1": tree, "operand2": tree}
    elif fault == "cycle":
        tree["operand1"] = tree
    else:
        tree = unproven_filter_summary(tree).model_dump(mode="json")
    assert_rejected(role, tree)
    summary = unproven_filter_summary(tree)
    assert summary.node_count <= 64 and summary.max_depth <= 8
    if fault in ("deep", "wide", "cycle"):
        assert summary.truncated and summary.signature_truncated


@pytest.mark.parametrize("role", ROLES)
def test_diagnostics_are_not_acceptance_authority(
    role: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Even a spoofed complete diagnostic cannot rescue the wrong raw role tree.
    valid = unproven_filter_summary(FIXTURES[role]["filter"])
    monkeypatch.setattr(
        standard_edit_shapes, "unproven_filter_summary", lambda _: valid
    )
    assert_rejected(
        role, deepcopy(FIXTURES["fillet" if role == "extrude" else "extrude"]["filter"])
    )

    # Acceptance must not require projection at all.
    def forbidden(*_: Any) -> Any:
        raise AssertionError("diagnostic projection used for acceptance")

    monkeypatch.setattr(standard_edit_shapes, "unproven_filter_summary", forbidden)
    data = ordinary_inventory()
    position = 2 if role == "extrude" else 3
    ui_quantity_parameter(
        data["features"][position - 1], "depth" if position == 2 else "radius"
    )


@pytest.mark.parametrize(
    "position,key,role",
    [
        (position, key, role)
        for position, key in QUERY_ROLES
        for role in ROLES
        if key != "entities" or role != ("extrude" if position == 2 else "fillet")
    ],
)
def test_exact_filters_still_reject_for_every_unproven_or_mismatched_query_role(
    position: int, key: str, role: str
) -> None:
    data = ui_inventory()
    param(data, position, key)["filter"] = deepcopy(FIXTURES[role]["filter"])
    replacement_rejects(data, position)


@pytest.mark.parametrize("position,kind", OPERATIONS)
def test_historical_profile_cannot_use_the_new_filter_contract_or_fall_through(
    position: int, kind: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = inventory()
    param(data, position, "entities")["filter"] = deepcopy(
        FIXTURES["extrude" if position == 2 else "fillet"]["filter"]
    )

    def forbidden(*_: Any) -> Any:
        raise AssertionError("Historical filter fell through to current UI")

    monkeypatch.setattr(edit_registry, "ui_quantity_parameter", forbidden)
    op = OP.validate_python(operation_for(kind, target(position).handle))
    with pytest.raises(EditError, match="unsupported_target"):
        change(data["features"], target(position), op)


@pytest.mark.parametrize("position,kind", OPERATIONS)
@pytest.mark.parametrize("reverse", [False, True])
def test_full_current_ui_replacements_preserve_every_accepted_unrelated_field(
    position: int, kind: str, reverse: bool
) -> None:
    data = ordinary_inventory()
    feature = data["features"][position - 1]
    if reverse:
        feature["parameters"].reverse()
    original = deepcopy(data)
    category: ShapeCategory = "extrude" if position == 2 else "fillet"
    assert diagnose_ui_shape(feature, category).failure is None
    report = metadata(data, position)
    assert report["parameter_shape_matches_registry"]
    assert report["replacement"] == report["rename"] == "exact_match"
    op = OP.validate_python(operation_for(kind, target(position).handle))
    updated, _ = change(data["features"], target(position), op)
    expected = deepcopy(feature)
    if kind == "RENAME_FEATURE":
        expected["name"] = "Conformance renamed"
    else:
        quantity = "depth" if position == 2 else "radius"
        next(p for p in expected["parameters"] if p["parameterId"] == quantity)[
            "expression"
        ] = "25 mm" if position == 2 else "3 mm"
    assert updated == expected and data == original
    assert len(feature["parameters"]) == (50 if position == 2 else 38)


@pytest.mark.parametrize("position", [2, 3])
@pytest.mark.parametrize(
    "fault",
    [
        "unknown",
        "duplicate",
        "malformed",
        "richer_mode",
        "query_missing",
        "query_extra",
    ],
)
def test_exact_filter_never_weakens_the_rest_of_the_full_feature_contract(
    position: int, fault: str
) -> None:
    data = ordinary_inventory()
    params = data["features"][position - 1]["parameters"]
    if fault == "unknown":
        params[-1]["parameterId"] = HOSTILE
    elif fault == "duplicate":
        params[-1] = deepcopy(params[0])
    elif fault == "malformed":
        params[-1] = None
    elif fault == "richer_mode":
        param(data, position, "hasDraft" if position == 2 else "isVariable")[
            "value"
        ] = True
    elif fault == "query_missing":
        del param(data, position, "entities")["queries"]
    else:
        param(data, position, "entities")[HOSTILE] = HOSTILE
    replacement_rejects(data, position)


@pytest.mark.parametrize("position,kind", OPERATIONS)
def test_exact_filter_replacements_require_approval_and_preserve_the_full_payload(
    harness: Harness, position: int, kind: str
) -> None:
    provider = PlanProvider()
    provider.data = ordinary_inventory()
    original = deepcopy(provider.data)
    with running(harness, provider):  # Synthetic enabled Settings + MockTransport only.
        req, preview = plan_for(harness, position, kind)
        assert provider.writes == 0 and provider.data == original
        assert (
            plan_service.cancel(req, harness.runtime, preview.proposal_id).state
            == "cancelled"
        )
        assert provider.writes == 0
        req, preview = plan_for(harness, position, kind)
        result = approve(harness, req, preview)
        assert result.state == "verified_success" and provider.writes == 1
        expected, _ = change(
            original["features"],
            target(position),
            OP.validate_python(operation_for(kind, target(position).handle)),
        )
        assert provider.payloads[0]["feature"] == expected
        assert provider.payloads[0]["rejectMicroversionSkew"] is True
        assert (
            len(next(c.content for c in provider.calls if c.method == "POST")) <= 8192
        )
        with pytest.raises(EditError, match="proposal_used"):
            approve(harness, req, preview)
        assert provider.writes == 1


@pytest.mark.parametrize("position,kind", OPERATIONS)
@pytest.mark.parametrize(
    "effect", ["filter_removed", "filter_changed", "parameter_order"]
)
def test_exact_filter_proposals_still_reject_stale_definitions_before_dispatch(
    harness: Harness, position: int, kind: str, effect: str
) -> None:
    provider = PlanProvider()
    provider.data = ordinary_inventory()
    with running(harness, provider):
        req, preview = plan_for(harness, position, kind)
        query = param(provider.data, position, "entities")
        if effect == "filter_removed":
            del query["filter"]
        elif effect == "filter_changed":
            query["filter"]["operand2"]["btType"] = HOSTILE
        else:
            provider.data["features"][position - 1]["parameters"].reverse()
        assert approve(harness, req, preview).state == "rejected_stale"
        assert provider.writes == 0


@pytest.mark.parametrize("position,kind", OPERATIONS)
def test_exact_representation_cannot_bypass_the_writes_off_transport_guard(
    position: int, kind: str
) -> None:
    data = ordinary_inventory()
    op = OP.validate_python(operation_for(kind, target(position).handle))
    _, preview = change(data["features"], target(position), op)
    resolved = ResolvedOperation(operation=op, target=target(position), preview=preview)
    evidence = project_modify_evidence(REF, M0, data, config(), bodies())

    def forbidden(_: httpx.Request) -> httpx.Response:
        raise AssertionError("Writes-OFF exact contract reached provider dispatch")

    with httpx.Client(transport=httpx.MockTransport(forbidden)) as transport:
        client = SafeEditClient(enabled_settings(), transport, "synthetic-token")
        with pytest.raises(EditError, match="write_disabled"):
            client.execute_operation(evidence, resolved)


@pytest.mark.parametrize("kind", ["SET_SUPPRESSED", "SET_UNSUPPRESSED"])
@pytest.mark.parametrize("valid_filter", [True, False])
def test_suppression_keeps_independent_terminal_authority_and_attribute_transport(
    harness: Harness, kind: str, valid_filter: bool
) -> None:
    provider = PlanProvider()
    provider.data = ordinary_inventory()
    if not valid_filter:
        param(provider.data, 3, "entities")["filter"] = {"btType": HOSTILE}
    if kind == "SET_UNSUPPRESSED":
        provider.data["features"][-1]["suppressed"] = True
        provider.data["featureStates"]["synthetic-feature-2"]["inactive"] = True
    before = deepcopy(provider.data["features"][-1]["parameters"])
    with running(harness, provider):
        req, preview = plan_for(harness, 3, kind)
        assert approve(harness, req, preview).state == "verified_success"
    body = provider.payloads[0]
    assert body["updateSuppressionAttributes"] is True
    assert set(body["features"][0]) == {"btType", "featureId", "suppressed"}
    assert next(c.url.path for c in provider.calls if c.method == "POST").endswith(
        "/features/updates"
    )
    assert provider.data["features"][-1]["parameters"] == before


@pytest.mark.parametrize("position,kind", OPERATIONS)
@pytest.mark.parametrize(
    "effect", ["preserve", "remove", "semantic", "operand_order", "other_feature"]
)
def test_fresh_exact_effect_verification_includes_all_accepted_filter_fields(
    position: int, kind: str, effect: str
) -> None:
    data = ordinary_inventory()
    before = project_modify_evidence(REF, M0, data, config(), bodies())
    op = OP.validate_python(operation_for(kind, target(position).handle))
    updated, preview = change(data["features"], target(position), op)
    data["features"][position - 1] = updated
    query = param(
        data, 5 - position if effect == "other_feature" else position, "entities"
    )
    if effect == "remove":
        del query["filter"]
    elif effect in ("semantic", "other_feature"):
        leaf = query["filter"]
        while "operand1" in leaf:
            leaf = leaf["operand1"]
        field = "allows" if "allows" in leaf else "isFromActiveSheetMetal"
        leaf[field] = not leaf[field] if type(leaf[field]) is bool else "MODEL_ONLY"
    elif effect == "operand_order":
        f = query["filter"]
        f["operand1"], f["operand2"] = f["operand2"], f["operand1"]
    data["sourceMicroversion"] = M1
    after = project_modify_evidence(REF, M1, data, config(M1), bodies(M1))
    resolved = ResolvedOperation(operation=op, target=target(position), preview=preview)
    if effect == "preserve":
        verify_operation(before, after, resolved, M1)
    else:
        with pytest.raises(EditError, match="verification_failed"):
            verify_operation(before, after, resolved, M1)


def test_writes_off_inspector_reports_exact_matches_without_proposal_or_mutation(
    harness: Harness, caplog: pytest.LogCaptureFixture
) -> None:
    user = harness.login()
    set_scope(harness, user, "OAuth2ReadPII OAuth2Read")
    settings = harness.runtime.settings
    settings.environment = "development"
    settings.forge_safe_edit_diagnostics_enabled = True
    assert not settings.forge_cad_writes_enabled
    provider = Provider()
    provider.data = ordinary_inventory()
    original = deepcopy(provider.data)
    normal = CadProvider()
    calls = []

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
    for role in ROLES:
        assert (
            caplog.text.count(
                f"safe_edit_standard_shape_validation category={role} "
                "outcome=exact_match"
            )
            == 2
        )
    reports = [
        json.loads(r.message.split("metadata=", 1)[1])
        for r in caplog.records
        if r.message.startswith("safe_edit_representation_coverage ")
    ]
    assert len(reports) == 2
    for report in reports:
        for position in report["positions"][1:]:
            assert position["parameter_shape_matches_registry"]
            assert position["replacement"] == position["rename"] == "exact_match"
    assert "safe_edit_probe outcome=eligible_no_proposal_no_write" in caplog.text
    assert "query_filter_unproven" not in caplog.text
    for forbidden in (
        HOSTILE,
        "BTFlatSheetMetalFilter",
        "MODEL_AND_FLATTENED",
        REF.documentId,
        REF.workspaceId,
        REF.elementId,
        "synthetic-feature-",
        provider.marker,
    ):
        assert forbidden not in caplog.text
    assert "safe_edit_" not in response.text
    assert provider.data == original and provider.writes == 0
    with harness.runtime.sessions() as db:
        assert db.scalar(select(func.count()).select_from(WriteRecord)) == 0
        assert db.scalar(select(func.count()).select_from(WriteFence)) == 0
