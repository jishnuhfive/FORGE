"""Complete human-evidence-shaped ordinary profiles; synthetic CAD/transport only."""

import json
import logging
from copy import deepcopy
from pathlib import Path
from typing import Any

import httpx2 as httpx
import pytest
import test_modify_filter_contracts as entities_checks
from conftest import Harness
from test_cad_read import REF
from test_modify_common_metadata import OPERATIONS
from test_modify_conformance import operation_for, plan_for
from test_modify_filter_contracts import at, nodes, ordinary_inventory
from test_modify_plan import OP, PlanProvider, _no_dispatch, approve, discover, target
from test_modify_representation import enabled_settings, metadata
from test_modify_ui_conformance import param, parameters, replacement_rejects
from test_safe_edit import M0, M1, Provider, bodies, config, running

from forge_api.cad_edits import plan_service
from forge_api.cad_edits.domain import EditError, fingerprint
from forge_api.cad_edits.plans import ResolvedOperation, SemanticPlan
from forge_api.integrations.onshape import current_ui_filters, standard_edit_shapes
from forge_api.integrations.onshape.current_ui_filters import (
    matches_dormant_query_filter,
)
from forge_api.integrations.onshape.dev import safe_edit
from forge_api.integrations.onshape.dev.query_roles import query_role_inventory
from forge_api.integrations.onshape.dev.standard_shape_failure import diagnose_ui_shape
from forge_api.integrations.onshape.edit_registry import change
from forge_api.integrations.onshape.modify_evidence import (
    project_modify_evidence,
    verify_operation,
)
from forge_api.integrations.onshape.query_filter_evidence import (
    MAX_DEPTH,
    diagnostic_filter_summary,
    unproven_filter_summary,
)
from forge_api.integrations.onshape.service import ReadGate
from forge_api.integrations.onshape.standard_shape_contract import ShapeCategory

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures/modify_current_query_filters.json").read_text()
)
ROLES = tuple(
    (category, key)
    for category in ("extrude", "fillet")
    for key in FIXTURE[category]
    if key != "entities"
)
LEAF_FIELDS = tuple(
    (category, role, path, field, value)
    for category, role in ROLES
    for path, node in nodes(FIXTURE[category][role]["filter"])
    for field, value in node.items()
    if field != "btType" and not field.startswith("operand")
)


def current_inventory() -> dict[str, Any]:
    data = ordinary_inventory()
    for position, category in ((2, "extrude"), (3, "fillet")):
        for key, expected in FIXTURE[category].items():
            param(data, position, key)["filter"] = deepcopy(expected["filter"])
    return data


def first_leaf(tree: Any) -> Any:
    while "operand1" in tree:
        tree = tree["operand1"]
    return tree


@pytest.mark.parametrize("category,role", ROLES)
def test_every_exact_role_has_independent_identity_and_count_authority(
    category: str, role: str
) -> None:
    data = current_inventory()
    position = 2 if category == "extrude" else 3
    item = param(data, position, role)
    before = deepcopy(item)
    assert matches_dormant_query_filter(category, role, item)
    summary = diagnostic_filter_summary(item["filter"])
    assert summary.node_count == FIXTURE[category][role]["nodes"]
    assert summary.max_depth == FIXTURE[category][role]["depth"]
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
    assert not matches_dormant_query_filter(
        "fillet" if category == "extrude" else "extrude", role, item
    )
    assert not matches_dormant_query_filter(category, "entities", item)
    assert not matches_dormant_query_filter(category, "unknown", item)
    item["parameterId"] = "different-role"
    assert not matches_dormant_query_filter(category, role, item)
    assert before["queries"] == [] and len(FIXTURE[category]) == (
        13 if category == "extrude" else 8
    )


FAULTS = (
    "query_nonempty",
    "query_null",
    "query_type",
    "missing_node",
    "extra_node",
    "swap",
    "leaf_type",
    "leaf_value",
    "missing_leaf_field",
    "null",
    "wrong_type",
    "extra_field",
    "malformed",
    "opaque",
    "truncation",
    "wrong_role",
)


@pytest.mark.parametrize("category,role", ROLES)
@pytest.mark.parametrize("fault", FAULTS)
def test_each_role_rejects_query_topology_leaf_and_identity_deviations(
    category: str, role: str, fault: str
) -> None:
    data = current_inventory()
    position = 2 if category == "extrude" else 3
    item = param(data, position, role)
    tree = item["filter"]
    leaf = first_leaf(tree)
    field = next(key for key in leaf if key != "btType")
    if fault == "query_nonempty":
        item["queries"] = [
            {"btType": "BTMIndividualQuery-138", "queryString": "synthetic-query"}
        ]
    elif fault == "query_null":
        item["queries"] = None
    elif fault == "query_type":
        item["queries"] = {}
    elif fault == "missing_node":
        del tree["operand2"]
    elif fault == "extra_node":
        tree["operand1"] = {"btType": "BTNotFilter-165", "operand": tree["operand1"]}
    elif fault == "swap":
        tree["operand1"], tree["operand2"] = tree["operand2"], tree["operand1"]
    elif fault == "leaf_type":
        leaf["btType"] = "BTQueryFilter-183"
    elif fault == "leaf_value":
        leaf[field] = not leaf[field] if type(leaf[field]) is bool else "UNKNOWN"
    elif fault == "missing_leaf_field":
        del leaf[field]
    elif fault == "null":
        item["filter"] = None
    elif fault == "wrong_type":
        item["filter"] = []
    elif fault == "extra_field":
        leaf["private-key"] = "private-value"
    elif fault == "malformed":
        item["filter"] = {}
    elif fault == "opaque":
        item["filter"] = {"btType": "BTFeatureFilter-127"}
    elif fault == "truncation":
        for _ in range(20):
            tree = {"btType": "BTNotFilter-165", "operand": tree}
        item["filter"] = tree
    else:
        item["parameterId"] = "different-role"
    assert not matches_dormant_query_filter(category, role, item)
    replacement_rejects(data, position)


@pytest.mark.parametrize("category,role", ROLES)
@pytest.mark.parametrize("value", [None, 0, 1, [], {}, "true"])
def test_required_leaf_fields_do_not_coerce_primitives(
    category: str, role: str, value: Any
) -> None:
    data = current_inventory()
    position = 2 if category == "extrude" else 3
    item = param(data, position, role)
    leaf = first_leaf(item["filter"])
    leaf[next(k for k in leaf if k != "btType")] = value
    assert not matches_dormant_query_filter(category, role, item)
    replacement_rejects(data, position)


@pytest.mark.parametrize(
    "category,left,right",
    [
        ("extrude", "endBoundEntityFace", "secondDirectionBoundEntityFace"),
        ("extrude", "endBoundEntityBody", "secondDirectionBoundEntityBody"),
        ("extrude", "endBoundEntityVertex", "secondDirectionBoundEntityVertex"),
        ("fillet", "side1Face", "side2Face"),
        ("fillet", "side1Face", "centerFaces"),
        ("fillet", "startPartialEntity", "endPartialEntity"),
    ],
)
def test_equal_trees_still_require_the_explicit_caller_role(
    category: str, left: str, right: str
) -> None:
    data = current_inventory()
    position = 2 if category == "extrude" else 3
    one, two = param(data, position, left), param(data, position, right)
    assert one["filter"] == two["filter"]
    assert matches_dormant_query_filter(category, left, one)
    assert matches_dormant_query_filter(category, right, two)
    assert not matches_dormant_query_filter(category, right, one)
    assert not matches_dormant_query_filter(category, left, two)


@pytest.mark.parametrize("category,role,path,field,value", LEAF_FIELDS)
@pytest.mark.parametrize("fault", ["missing", "null", "coercion", "changed"])
def test_every_dormant_leaf_field_is_required_exact_and_typed(
    category: str, role: str, path: tuple[str, ...], field: str, value: Any, fault: str
) -> None:
    data = current_inventory()
    position = 2 if category == "extrude" else 3
    item = param(data, position, role)
    leaf = at(item["filter"], path)
    if fault == "missing":
        del leaf[field]
    elif fault == "null":
        leaf[field] = None
    elif fault == "coercion":
        leaf[field] = int(value) if type(value) is bool else 0
    else:
        leaf[field] = not value if type(value) is bool else "UNKNOWN"
    assert not matches_dormant_query_filter(category, role, item)
    replacement_rejects(data, position)


@pytest.mark.parametrize(
    "position,key",
    [
        (position, p["parameterId"])
        for position in (2, 3)
        for p in current_inventory()["features"][position - 1]["parameters"]
    ],
)
def test_current_full_profile_requires_every_serialized_parameter(
    position: int, key: str
) -> None:
    data = current_inventory()
    data["features"][position - 1]["parameters"].remove(param(data, position, key))
    replacement_rejects(data, position)


def test_depth_nine_exception_is_not_a_generic_production_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = current_inventory()
    item = param(data, 2, "extrudeDirection")
    assert MAX_DEPTH == 8
    assert unproven_filter_summary(item["filter"]).signature_truncated
    assert diagnostic_filter_summary(item["filter"]).max_depth == 9
    calls = []
    original = current_ui_filters._matches

    def observe(*args: Any, **kwargs: Any) -> bool:
        calls.append(kwargs.get("depth_limit", 8))
        return original(*args, **kwargs)

    monkeypatch.setattr(current_ui_filters, "_matches", observe)
    for category, role in ROLES:
        p = param(data, 2 if category == "extrude" else 3, role)
        assert matches_dormant_query_filter(category, role, p)
        assert calls[-1] == (9 if role == "extrudeDirection" else 8)
        if role != "extrudeDirection":
            p["filter"] = deepcopy(item["filter"])
            assert not matches_dormant_query_filter(category, role, p)


@pytest.mark.parametrize("position,kind", OPERATIONS)
@pytest.mark.parametrize("reverse", [False, True])
def test_whole_current_profile_is_exact_and_replacements_preserve_every_field(
    position: int, kind: str, reverse: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = current_inventory()
    feature = data["features"][position - 1]
    if reverse:
        feature["parameters"].reverse()
    before = deepcopy(data)

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("Diagnostic used for acceptance")

    monkeypatch.setattr(standard_edit_shapes, "unproven_filter_summary", forbidden)
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
        next(
            p
            for p in expected["parameters"]
            if p["parameterId"] == ("depth" if position == 2 else "radius")
        )["expression"] = "25 mm" if position == 2 else "3 mm"
    assert fingerprint(updated) == fingerprint(expected) and data == before
    assert [p["parameterId"] for p in parameters(updated)] == [
        p["parameterId"] for p in feature["parameters"]
    ]


@pytest.mark.parametrize("category,role", ROLES)
@pytest.mark.parametrize(
    "fault", ["missing_parameter", "missing_filter", "parameter_extra"]
)
def test_complete_current_profile_cannot_drop_or_ignore_dormant_parameters(
    category: str, role: str, fault: str
) -> None:
    data = current_inventory()
    position = 2 if category == "extrude" else 3
    item = param(data, position, role)
    if fault == "missing_parameter":
        data["features"][position - 1]["parameters"].remove(item)
    elif fault == "missing_filter":
        del item["filter"]
    else:
        item["private-field"] = "private-value"
    replacement_rejects(data, position)


@pytest.mark.parametrize("position", [2, 3])
def test_active_filtered_entities_require_exactly_one_query_item(position: int) -> None:
    data = current_inventory()
    item = param(data, position, "entities")
    item["queries"] *= 2
    replacement_rejects(data, position)


@pytest.mark.parametrize("position,kind", OPERATIONS)
def test_complete_current_payload_cancels_then_approves_once_and_verifies(
    harness: Harness, position: int, kind: str
) -> None:
    provider = PlanProvider()
    provider.data = current_inventory()
    original = deepcopy(provider.data)
    with running(harness, provider):
        req, preview = plan_for(harness, position, kind)
        assert (
            plan_service.cancel(req, harness.runtime, preview.proposal_id).state
            == "cancelled"
        )
        _no_dispatch(harness, provider)
        req, preview = plan_for(harness, position, kind)
        assert approve(harness, req, preview).state == "verified_success"
        expected, _ = change(
            original["features"],
            target(position),
            OP.validate_python(operation_for(kind, target(position).handle)),
        )
        assert provider.payloads[0]["feature"] == expected
        post = next(c for c in provider.calls if c.method == "POST")
        assert 8192 < len(post.content) <= 32768
        assert (
            provider.writes == 1
            and provider.payloads[0]["rejectMicroversionSkew"] is True
        )
        with pytest.raises(EditError, match="proposal_used"):
            approve(harness, req, preview)
        assert provider.writes == 1


@pytest.mark.parametrize("category,role", ROLES)
@pytest.mark.parametrize("effect", ["remove", "add", "subtype", "order", "leaf"])
@pytest.mark.parametrize("quantity", [False, True])
def test_every_dormant_filter_delta_fails_whole_inventory_exact_verification(
    category: str, role: str, effect: str, quantity: bool
) -> None:
    position = 2 if category == "extrude" else 3
    data = current_inventory()
    before = project_modify_evidence(REF, M0, data, config(), bodies())
    kind = (
        ("SET_EXTRUDE_DEPTH" if position == 2 else "SET_FILLET_RADIUS")
        if quantity
        else "RENAME_FEATURE"
    )
    op = OP.validate_python(operation_for(kind, target(position).handle))
    updated, preview = change(data["features"], target(position), op)
    data["features"][position - 1] = updated
    item = param(data, position, role)
    if effect == "remove":
        del item["filter"]
    elif effect == "add":
        item["filter"]["extra"] = {"btType": "BTQueryFilter-183"}
    elif effect == "subtype":
        item["filter"]["btType"] = "BTNotFilter-165"
    elif effect == "order":
        f = item["filter"]
        f["operand1"], f["operand2"] = f["operand2"], f["operand1"]
    else:
        leaf = first_leaf(item["filter"])
        key = next(k for k in leaf if k != "btType")
        leaf[key] = not leaf[key] if type(leaf[key]) is bool else "UNKNOWN"
    data["sourceMicroversion"] = M1
    after = project_modify_evidence(REF, M1, data, config(M1), bodies(M1))
    with pytest.raises(EditError, match="verification_failed"):
        verify_operation(
            before,
            after,
            ResolvedOperation(operation=op, target=target(position), preview=preview),
            M1,
        )


def test_guarded_diagnostics_report_complete_13_and_8_exact_profiles_without_proposals(
    caplog: pytest.LogCaptureFixture,
) -> None:
    provider = Provider()
    provider.data = current_inventory()
    before = deepcopy(provider.data)
    reports = query_role_inventory(provider.data)
    assert [
        (r.summary.total_query_roles_discovered, r.summary.total_query_roles_inspected)
        for r in reports
    ] == [(13, 13), (8, 8)]
    with (
        httpx.Client(transport=httpx.MockTransport(provider.handle)) as transport,
        caplog.at_level(logging.WARNING),
    ):
        safe_edit.CoverageClient(
            enabled_settings(), transport, "synthetic-token"
        ).compare(REF)
    assert caplog.text.count("safe_edit_standard_shape_validation") == 4
    assert "query_filter_unproven" not in caplog.text
    assert "safe_edit_standard_shape_failure" not in caplog.text
    assert 'parameter_shape_matches_registry":true' in caplog.text
    assert len(provider.calls) == 4 and provider.writes == 0 and provider.data == before


def test_full_inspector_keeps_existing_privacy_read_and_zero_proposal_guarantees(
    harness: Harness, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Reuse the unchanged 13-GET/privacy/zero-record proof with the full fixture.
    # current_inventory holds the original imported entities-only fixture builder.
    monkeypatch.setattr(entities_checks, "ordinary_inventory", current_inventory)
    entities_checks.test_writes_off_inspector_reports_exact_matches_without_proposal_or_mutation(
        harness, caplog
    )
    summaries = [
        json.loads(r.message.split("metadata=", 1)[1])
        for r in caplog.records
        if r.message.startswith("safe_edit_query_role_summary ")
    ]
    assert len(summaries) == 4
    for summary in summaries:
        count = 13 if summary["category"] == "extrude" else 8
        assert (
            summary["total_query_roles_discovered"]
            == summary["total_query_roles_inspected"]
            == count
        )
        assert summary["all_roles_inspected"]
        assert not any(
            summary[k]
            for k in (
                "any_malformed",
                "any_unexpected_fields",
                "any_uninspected",
                "any_truncated",
            )
        )
    direction = [
        r.message for r in caplog.records if "parameter=extrudeDirection " in r.message
    ]
    assert len(direction) == 2
    assert all(
        "max_depth=9 node_count=17" in row and "signature_truncated=false" in row
        for row in direction
    )


@pytest.mark.parametrize("position,kind", OPERATIONS)
def test_changed_postwrite_dormant_filter_is_uncertain_and_stops_the_suffix(
    harness: Harness, position: int, kind: str
) -> None:
    class ChangedReadProvider(PlanProvider):
        def handle(self, request: httpx.Request) -> httpx.Response:
            response = super().handle(request)
            if (
                self.writes
                and request.method == "GET"
                and request.url.path.endswith("/features")
            ):
                data = response.json()
                key = "surfaceEntities" if position == 2 else "side1Face"
                param(data, position, key)["filter"]["btType"] = "BTOrFilter-167"
                return httpx.Response(200, json=data)
            return response

    provider = ChangedReadProvider()
    provider.data = current_inventory()
    with running(harness, provider):
        req, catalog = discover(harness)
        first = next(t for t in catalog.targets if t.position == position)
        second = next(t for t in catalog.targets if t.position == 5 - position)
        req.app.state.cad_gate = ReadGate()
        preview = plan_service.prepare(
            req,
            harness.runtime,
            SemanticPlan.model_validate_json(
                json.dumps(
                    {
                        "target_catalog": catalog.target_catalog,
                        "operations": [
                            operation_for(kind, first.handle),
                            operation_for("RENAME_FEATURE", second.handle),
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
