"""Synthetic provider bookkeeping variations; no real CAD or credentials."""

from copy import deepcopy
from typing import Any

import httpx2 as httpx
import pytest
from conftest import Harness
from server_depth_support import review, seed_server
from sqlalchemy import select
from test_cad_read import REF
from test_modify_current_query_contracts import current_inventory
from test_modify_plan import OP, PlanProvider, approve, prepare, target
from test_modify_ui_conformance import param
from test_safe_edit import M0, M1, bodies, config, running

from forge_api.cad_edits import depth_recovery, plan_storage
from forge_api.cad_edits.depth_contracts import DepthRecoveryDenied
from forge_api.cad_edits.domain import EditError, fingerprint
from forge_api.cad_edits.plans import ResolvedOperation
from forge_api.db.models import WriteFence, WriteRecord
from forge_api.integrations.onshape.edit_registry import change
from forge_api.integrations.onshape.modify_evidence import (
    project_modify_evidence,
    project_modify_raw_evidence,
    verify_operation,
)
from forge_api.integrations.onshape.semantic_inventory import canonical_inventory


def nodes(data: dict[str, Any], prefix: str, slot: str = "all") -> None:
    for i, feature in enumerate(data["features"]):
        if slot in ("all", "feature"):
            feature["nodeId"] = prefix + str(i)
        if slot in ("all", "suppression"):
            feature["suppressionState"]["nodeId"] = prefix + str(i)
        if i == 0:
            continue
        for j, parameter in enumerate(feature["parameters"]):
            if slot in ("all", "parameter"):
                parameter["nodeId"] = prefix + str(j)
            if slot in ("all", "query"):
                for k, query in enumerate(parameter.get("queries", [])):
                    query["nodeId"] = prefix + str(k)


def projection(data: Any, marker: str = M0) -> Any:
    return project_modify_evidence(
        REF, marker, data, config(marker), bodies(marker, explicit_flags=False)
    )


def operation(data: Any) -> Any:
    edit = OP.validate_python(
        {"type": "SET_EXTRUDE_DEPTH", "target": target(2).handle, "quantity": "30 mm"}
    )
    updated, preview = change(data["features"], target(2), edit)
    after = deepcopy(data)
    after["features"][1] = updated
    after["sourceMicroversion"] = M1
    return ResolvedOperation(operation=edit, target=target(2), preview=preview), after


@pytest.mark.parametrize("slot", ["feature", "parameter", "query", "suppression"])
@pytest.mark.parametrize("side", ["historical", "current"])
def test_only_declared_node_locations_vary_without_semantic_change(
    slot: str, side: str
) -> None:
    historical = current_inventory()
    nodes(historical, "original")
    resolved, current = operation(historical)
    baseline = projection(historical).baseline
    changed = historical if side == "historical" else current
    nodes(changed, "regenerated", slot)
    assert projection(historical).baseline == baseline
    before, after = projection(historical), projection(current, M1)
    verify_operation(before, after, resolved, M1)
    assert before.features() == historical["features"]  # payload evidence stays raw
    raw = deepcopy(changed)
    canonical_inventory(changed)
    assert changed == raw


@pytest.mark.parametrize("slot", ["feature", "parameter", "query", "suppression"])
@pytest.mark.parametrize("bad", [None, 0, {}, [], "", "x" * 257])
def test_malformed_nodes_reject_before_semantic_projection(slot: str, bad: Any) -> None:
    data = current_inventory()
    item = data["features"][1]
    if slot == "parameter":
        item = item["parameters"][0]
    elif slot == "query":
        item = param(data, 2, "entities")["queries"][0]
    elif slot == "suppression":
        item = item["suppressionState"]
    item["nodeId"] = bad
    with pytest.raises(EditError):
        projection(data)


CHANGES = (
    "identity",
    "order",
    "type",
    "name",
    "suppression",
    "parameter_id",
    "parameter_order",
    "btType",
    "depth",
    "radius",
    "value",
    "units",
    "enum",
    "importMicroversion",
    "parameterName",
    "valueString",
    "libraryRelationType",
    "queryString",
    "deterministicIds",
    "sketch_identity",
    "filter",
    "states",
    "configuration",
    "serialization",
    "library",
    "body",
    "unknown",
    "hidden_node",
)


@pytest.mark.parametrize("field", CHANGES)
def test_every_meaningful_difference_still_rejects(field: str) -> None:
    historical = current_inventory()
    nodes(historical, "original")
    resolved, current = operation(historical)
    nodes(current, "new")
    depth = param(current, 2, "depth")
    query = param(current, 2, "entities")["queries"][0]
    configuration, body = config(M1), bodies(M1, explicit_flags=False)
    feature = current["features"][1]
    if field == "identity":
        feature["featureId"] = "other"
    elif field == "order":
        current["features"].reverse()
    elif field == "type":
        feature["featureType"] = "fillet"
    elif field == "name":
        feature["name"] = "Other"
    elif field == "suppression":
        feature["suppressed"] = True
    elif field == "parameter_id":
        depth["parameterId"] = "other"
    elif field == "parameter_order":
        feature["parameters"].reverse()
    elif field == "btType":
        depth["btType"] = "wrong"
    elif field == "depth":
        depth["expression"] = "31 mm"
    elif field == "radius":
        param(current, 3, "radius")["expression"] = "3 mm"
    elif field == "value":
        depth["value"] = 1
    elif field == "units":
        depth["units"] = "mm"
    elif field == "enum":
        param(current, 2, "bodyType")["value"] = "SURFACE"
    elif field in (
        "importMicroversion",
        "parameterName",
        "valueString",
        "libraryRelationType",
    ):
        depth[field] = "changed"
    elif field == "queryString":
        query["queryString"] = "other"
    elif field == "deterministicIds":
        query["deterministicIds"] = ["other"]
    elif field == "sketch_identity":
        query["featureId"] = "other"
    elif field == "filter":
        param(current, 2, "entities")["filter"] = {"btType": "wrong"}
    elif field == "states":
        current["featureStates"] = {}
    elif field == "configuration":
        configuration["other"] = True
    elif field == "serialization":
        current["serializationVersion"] = "other"
    elif field == "library":
        current["libraryVersion"] += 1
    elif field == "body":
        body["errorEnum"] = "ERROR"
    elif field == "unknown":
        feature["other"] = True
    elif field == "hidden_node":
        historical["features"][1]["unmodeled"] = {"nodeId": "old"}
        feature["unmodeled"] = {"nodeId": "new"}
    with pytest.raises(EditError):
        before = projection(historical)
        after = project_modify_evidence(REF, M1, current, configuration, body)
        verify_operation(before, after, resolved, M1)


@pytest.mark.parametrize("difference", [None, "semantic", "history"])
def test_retained_legacy_depth_approval_remains_raw_bound_before_canonical_recovery(
    harness: Harness,
    difference: str | None,
) -> None:
    provider = PlanProvider()
    provider.data = current_inventory()
    nodes(provider.data, "historical")
    historical = deepcopy(provider.data)
    with running(harness, provider):
        case = seed_server(harness, provider)
        # Construct a synthetic pre-repair retained row, including its original
        # raw approval digest. This fixture never reads/rewrites the real incident.
        with harness.runtime.sessions.begin() as db:
            row = db.get(WriteRecord, case.reference.historical.record_id)
            assert row
            saved = plan_storage.load(row)
            legacy = saved.plan.model_copy(
                update={
                    "policy_version": "modify-a1-1",
                    "baseline": project_modify_raw_evidence(
                        REF, M0, historical, config(), bodies(explicit_flags=False)
                    ).baseline,
                }
            )
            row.payload = saved.model_copy(update={"plan": legacy}).model_dump_json()
            row.digest = fingerprint(legacy.model_dump(mode="json"))
            case.reference = depth_recovery._development_reference(
                db, harness.runtime.settings, review(harness)
            )
        nodes(provider.data, "current")
        if difference == "semantic":
            param(provider.data, 2, "depth")["units"] = "mm"
        if difference == "history":
            original = provider.handle

            def altered(request: httpx.Request) -> httpx.Response:
                response = original(request)
                if f"/m/{M0}/" in request.url.path and request.url.path.endswith(
                    "features"
                ):
                    data = response.json()
                    nodes(data, "different-history")
                    return httpx.Response(200, json=data)
                return response

            provider.handle = altered  # type: ignore[method-assign]
        snapshot = case.snapshot()
        if difference:
            with pytest.raises(DepthRecoveryDenied):
                case.recover()
            assert case.snapshot() == snapshot
        else:
            result = case.recover()
            assert result.original_execution_outcome == "execution_uncertain"  # type: ignore[attr-defined]
            assert result.state == "operator_recovered"  # type: ignore[attr-defined]
        assert provider.writes == 0


@pytest.mark.parametrize(
    "bad", [None, "ack_semantic", "ack_node", "ack_missing_nodes", "post_semantic"]
)
def test_new_plan_stays_bound_across_node_regeneration_and_ack(
    harness: Harness,
    bad: str | None,
) -> None:
    provider = PlanProvider()
    provider.data = current_inventory()
    nodes(provider.data, "original")
    original = provider.handle

    def response(request: httpx.Request) -> httpx.Response:
        raw = original(request)
        if request.method == "POST":
            nodes(provider.data, "post-write")
            data = raw.json()
            data["feature"] = deepcopy(provider.data["features"][1])
            if bad == "ack_semantic":
                data["feature"]["name"] = "unapproved"
            elif bad == "ack_node":
                data["feature"]["nodeId"] = None
            elif bad == "ack_missing_nodes":
                acknowledged = data["feature"]
                acknowledged.pop("nodeId", None)
                acknowledged["suppressionState"].pop("nodeId", None)
                for item in acknowledged["parameters"]:
                    item.pop("nodeId", None)
                    for query in item.get("queries", []):
                        query.pop("nodeId", None)
            elif bad == "post_semantic":
                provider.data["features"][0]["name"] = "unapproved"
            return httpx.Response(200, json=data)
        return raw

    provider.handle = response  # type: ignore[method-assign]
    with running(harness, provider):
        request, preview = prepare(harness, ("SET_EXTRUDE_DEPTH",))
        with harness.runtime.sessions() as db:
            row = db.get(WriteRecord, preview.proposal_id)
            assert row
            saved = plan_storage.load(row)
        assert saved.plan.policy_version == "modify-semantic-nodes-2"
        assert saved.plan.baseline == projection(provider.data).baseline
        assert preview.digest == fingerprint(saved.plan.model_dump(mode="json"))
        nodes(provider.data, "pre-dispatch")
        result = approve(harness, request, preview)
        assert result.state == ("execution_uncertain" if bad else "verified_success")
        assert provider.writes == 1
        assert "nodeId" in provider.payloads[0]["feature"]


@pytest.mark.parametrize(
    "location",
    [
        "sketch_parameter",
        "parameter_extension",
        "filter",
        "feature_states",
        "configuration",
    ],
)
def test_node_named_fields_in_unmodeled_locations_remain_exact(location: str) -> None:
    data = current_inventory()
    other = deepcopy(data)
    if location == "sketch_parameter":
        data["features"][0]["parameters"] = [{"nodeId": "old"}]
        other["features"][0]["parameters"] = [{"nodeId": "new"}]
    elif location == "parameter_extension":
        param(data, 2, "depth")["extension"] = {"nodeId": "old"}
        param(other, 2, "depth")["extension"] = {"nodeId": "new"}
    elif location == "filter":
        param(data, 2, "entities")["filter"]["nodeId"] = "old"
        param(other, 2, "entities")["filter"]["nodeId"] = "new"
    elif location == "feature_states":
        data["featureStates"]["synthetic-feature-1"]["nodeId"] = "old"
        other["featureStates"]["synthetic-feature-1"]["nodeId"] = "new"
    else:
        before_config, after_config = config(), config()
        before_config["nodeId"], after_config["nodeId"] = "old", "new"
        assert (
            project_modify_evidence(REF, M0, data, before_config, bodies()).baseline
            != project_modify_evidence(REF, M0, other, after_config, bodies()).baseline
        )
        return
    assert fingerprint(canonical_inventory(data)) != fingerprint(
        canonical_inventory(other)
    )


@pytest.mark.parametrize("shape", ["missing", "duplicate", "unknown", "query"])
def test_invalid_target_shape_cannot_gain_node_canonical_authority(shape: str) -> None:
    data = current_inventory()
    nodes(data, "original")
    parameters = data["features"][1]["parameters"]
    if shape == "missing":
        parameters.pop()
    elif shape == "duplicate":
        parameters.append(deepcopy(parameters[0]))
    elif shape == "unknown":
        parameters.append(
            {
                "btType": "BTMParameterBoolean-144",
                "parameterId": "unknown",
                "value": False,
                "nodeId": "original",
            }
        )
    else:
        param(data, 2, "entities")["queries"][0]["btType"] = "unknown"
    other = deepcopy(data)
    nodes(other, "different", "parameter")
    semantic_features = canonical_inventory(data)["features"]
    assert isinstance(semantic_features, list)
    semantic_feature = semantic_features[1]
    assert isinstance(semantic_feature, dict)
    assert semantic_feature["parameters"] == parameters
    assert fingerprint(canonical_inventory(data)) != fingerprint(
        canonical_inventory(other)
    )
    with pytest.raises(EditError):
        operation(data)


def test_old_pending_policy_cannot_gain_new_execution_semantics(
    harness: Harness,
) -> None:
    provider = PlanProvider()
    with running(harness, provider):
        _, preview = prepare(harness, ("SET_EXTRUDE_DEPTH",))
        with harness.runtime.sessions.begin() as db:
            row = db.get(WriteRecord, preview.proposal_id)
            assert row
            saved = plan_storage.load(row)
            old = saved.plan.model_copy(update={"policy_version": "modify-a1-1"})
            row.payload = saved.model_copy(update={"plan": old}).model_dump_json()
            row.digest = fingerprint(old.model_dump(mode="json"))
            db.flush()
            unchanged = row.payload, row.digest
            with pytest.raises(EditError, match="model_changed"):
                plan_storage.claim(
                    db, row.id, row.user_id, row.session_hash, row.digest
                )
            assert row.state == "pending" and (row.payload, row.digest) == unchanged
            assert not list(db.scalars(select(WriteFence)))
        assert provider.writes == 0


@pytest.mark.parametrize("vary_nodes", [False, True])
def test_legacy_fillet_reconciliation_keeps_original_raw_contract(
    harness: Harness,
    vary_nodes: bool,
) -> None:
    from test_modify_recovery import current, reconcile, uncertain

    provider = PlanProvider()
    provider.data = current_inventory()
    nodes(provider.data, "original")
    with running(harness, provider):
        preview = uncertain(harness)
        with harness.runtime.sessions.begin() as db:
            row = db.get(WriteRecord, preview.proposal_id)
            assert row
            saved = plan_storage.load(row)
            old = saved.plan.model_copy(
                update={
                    "policy_version": "modify-a1-1",
                    "baseline": project_modify_raw_evidence(
                        REF, M0, provider.data, config(), bodies(explicit_flags=False)
                    ).baseline,
                }
            )
            row.payload = saved.model_copy(update={"plan": old}).model_dump_json()
            row.digest = fingerprint(old.model_dump(mode="json"))
        current(provider, True)
        if vary_nodes:
            nodes(provider.data, "changed")
        result = reconcile(harness, preview)
        assert result.status_code == (409 if vary_nodes else 200)
        assert provider.writes == 0
        with harness.runtime.sessions() as db:
            row = db.get(WriteRecord, preview.proposal_id)
            assert row and row.digest == fingerprint(old.model_dump(mode="json"))
            assert row.state == (
                "execution_uncertain" if vary_nodes else "reconciled_current_state"
            )
            assert bool(list(db.scalars(select(WriteFence)))) == vary_nodes


def test_unsupported_missing_node_envelope_cannot_equal_valid_semantic_projection() -> (
    None
):
    historical = current_inventory()
    nodes(historical, "valid")
    resolved, after = operation(historical)
    for feature in after["features"]:
        feature.pop("nodeId", None)
        feature["suppressionState"].pop("nodeId", None)
        for parameter in feature.get("parameters", []):
            parameter.pop("nodeId", None)
            for query in parameter.get("queries", []):
                query.pop("nodeId", None)
    # Quantity nodeId is required in this current-UI profile. A raw unsupported
    # envelope must not equal the stripped representation of a valid envelope.
    with pytest.raises(EditError):
        verify_operation(projection(historical), projection(after, M1), resolved, M1)
