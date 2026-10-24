"""Closed historical representations cannot bypass current-UI validation.

All CAD/identities/queries are synthetic; provider traffic is mocked.
"""

from copy import deepcopy
from typing import Any

import httpx2 as httpx
import pytest
from conftest import Harness
from test_cad_read import REF
from test_modify_conformance import (
    initial_provider,
    operation_for,
    plan_for,
    rejected_replacement,
)
from test_modify_plan import OP, PlanProvider, approve, inventory, target
from test_modify_representation import metadata
from test_modify_ui_conformance import ui_inventory
from test_safe_edit import M0, bodies, config, running

from forge_api.cad_edits.domain import EditError, fingerprint
from forge_api.cad_edits.plans import ResolvedOperation
from forge_api.integrations.onshape import edit_registry
from forge_api.integrations.onshape.edit_registry import change, quantity_parameter
from forge_api.integrations.onshape.modify_evidence import project_modify_evidence
from forge_api.integrations.onshape.standard_edit_shapes import ui_quantity_parameter
from forge_api.integrations.onshape.standard_shape_contract import ShapeValidationError
from forge_api.integrations.onshape.write_client import SafeEditClient

REPLACEMENTS = (
    (2, "SET_EXTRUDE_DEPTH"),
    (3, "SET_FILLET_RADIUS"),
    (2, "RENAME_FEATURE"),
    (3, "RENAME_FEATURE"),
)
PARAMETERS = tuple(
    (position, p["parameterId"])
    for position in (2, 3)
    for p in inventory()["features"][position - 1]["parameters"]
)


def parameter(data: dict[str, Any], position: int, key: str) -> dict[str, Any]:
    return next(
        p
        for p in data["features"][position - 1]["parameters"]
        if p["parameterId"] == key
    )


def corrupt(data: dict[str, Any], position: int, case: str) -> None:
    entities = parameter(data, position, "entities")
    query = entities["queries"][0]
    if case == "filter":
        entities["filter"] = {"btType": "BTEntityTypeFilter-124", "entityType": "FACE"}
    elif case == "envelope_extra":
        entities["unknown"] = {"nested": True}
    elif case == "query_extra":
        query["unknown"] = {"nested": True}
    elif case == "query_filter":
        query["filter"] = {}
    elif case == "query_ui_metadata":
        query["deterministicIds"] = ["synthetic-edge"]
    elif case == "query_node":
        query["nodeId"] = "synthetic-query-node"
    elif case == "query_type":
        query["btType"] = "BTMIndividualQuery-138-extra"
    elif case == "query_missing":
        del query["featureId" if position == 2 else "queryString"]
    elif case == "query_empty":
        query["featureId" if position == 2 else "queryString"] = ""
    elif case == "query_value":
        query["featureId" if position == 2 else "queryString"] = ["synthetic"]
    elif case == "query_object":
        entities["queries"] = [{}]
    elif case == "query_scalar":
        entities["queries"] = ["synthetic"]
    else:
        raise AssertionError(case)


NESTED_CASES = (
    "filter",
    "envelope_extra",
    "query_extra",
    "query_filter",
    "query_ui_metadata",
    "query_node",
    "query_type",
    "query_missing",
    "query_empty",
    "query_value",
    "query_object",
    "query_scalar",
)


@pytest.mark.parametrize("position,kind", REPLACEMENTS)
@pytest.mark.parametrize("with_metadata", [False, True])
@pytest.mark.parametrize("reverse", [False, True])
def test_exact_historical_profiles_preserve_all_unrelated_fields(
    position: int, kind: str, with_metadata: bool, reverse: bool
) -> None:
    data = inventory()
    feature = data["features"][position - 1]
    if with_metadata:
        for p in feature["parameters"]:
            p["nodeId"] = "synthetic-" + p["parameterId"]
            if "expression" in p:
                p["isInteger"] = False
    if reverse:
        feature["parameters"].reverse()
    before = deepcopy(data)
    op = OP.validate_python(operation_for(kind, target(position).handle))
    updated, _ = change(data["features"], target(position), op)
    expected = deepcopy(feature)
    if kind == "RENAME_FEATURE":
        expected["name"] = "Conformance renamed"
    else:
        key = "depth" if position == 2 else "radius"
        next(p for p in expected["parameters"] if p["parameterId"] == key)[
            "expression"
        ] = "25 mm" if position == 2 else "3 mm"
    assert fingerprint(updated) == fingerprint(expected)
    assert data == before
    assert metadata(data, position)["replacement"] == "exact_match"


@pytest.mark.parametrize("position,kind", REPLACEMENTS)
@pytest.mark.parametrize("case", NESTED_CASES)
def test_nested_fields_cannot_bypass_quantity_or_rename(
    position: int, kind: str, case: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = inventory()
    corrupt(data, position, case)
    before = deepcopy(data)

    def forbidden(*args: Any) -> Any:
        raise AssertionError("Failed historical profiles must never fall back to UI")

    monkeypatch.setattr(edit_registry, "ui_quantity_parameter", forbidden)
    op = OP.validate_python(operation_for(kind, target(position).handle))
    with pytest.raises(EditError, match="unsupported_target"):
        change(data["features"], target(position), op)
    result = metadata(data, position)
    assert result["replacement"] == result["rename"] == "unsupported_shape"
    assert data == before


@pytest.mark.parametrize("position,key", PARAMETERS)
@pytest.mark.parametrize(
    "case",
    [
        "missing",
        "duplicate",
        "unknown",
        "wrong_type",
        "extra_field",
        "node_type",
        "ui_metadata",
    ],
)
def test_every_parameter_is_required_unique_typed_and_closed(
    position: int, key: str, case: str
) -> None:
    data = inventory()
    item = parameter(data, position, key)
    params = data["features"][position - 1]["parameters"]
    if case == "missing":
        params.remove(item)
    elif case == "duplicate":
        params.append(deepcopy(item))
    elif case == "unknown":
        params.append({"parameterId": "synthetic-unknown", "value": False})
    elif case == "wrong_type":
        item["btType"] = "BTMParameterString-149"
    elif case == "extra_field":
        item["unknown"] = {"nested": "synthetic"}
    elif case == "node_type":
        item["nodeId"] = {"nested": "synthetic"}
    else:
        item["libraryRelationType"] = "DEFAULT"
    for kind in (
        "RENAME_FEATURE",
        "SET_EXTRUDE_DEPTH" if position == 2 else "SET_FILLET_RADIUS",
    ):
        op = OP.validate_python(operation_for(kind, target(position).handle))
        with pytest.raises(EditError, match="unsupported_target"):
            change(data["features"], target(position), op)


@pytest.mark.parametrize("position", [2, 3])
@pytest.mark.parametrize("case", NESTED_CASES)
def test_invalid_historical_profiles_never_gain_plan_or_dispatch_authority(
    harness: Harness, position: int, case: str
) -> None:
    provider = PlanProvider()
    corrupt(provider.data, position, case)
    rejected_replacement(harness, provider, position)


@pytest.mark.parametrize("position,kind", REPLACEMENTS)
@pytest.mark.parametrize("case", ["filter", "envelope_extra", "query_extra"])
def test_transport_rechecks_complete_fresh_profile_before_post(
    harness: Harness, position: int, kind: str, case: str
) -> None:
    data = inventory()
    op = OP.validate_python(operation_for(kind, target(position).handle))
    _, preview = change(data["features"], target(position), op)
    resolved = ResolvedOperation(operation=op, target=target(position), preview=preview)
    corrupt(data, position, case)
    evidence = project_modify_evidence(REF, M0, data, config(), bodies())

    def forbidden(request: httpx.Request) -> httpx.Response:
        raise AssertionError("Unsupported definition reached transport")

    # Enabled only on a synthetic client with an in-process, network-free mock.
    settings = harness.runtime.settings.model_copy(
        update={"forge_cad_writes_enabled": True}
    )
    with httpx.Client(transport=httpx.MockTransport(forbidden)) as transport:
        client = SafeEditClient(settings, transport, "synthetic-token")
        with pytest.raises(EditError, match="unsupported_target"):
            client.check_operation(evidence, resolved)
        with pytest.raises(EditError, match="unsupported_target"):
            client.execute_operation(evidence, resolved)


@pytest.mark.parametrize("position", [2, 3])
def test_whole_current_ui_feature_reaches_closed_filter_rejection(
    position: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = ui_inventory()
    corrupt(data, position, "filter")
    feature = data["features"][position - 1]
    before = deepcopy(feature)
    called: list[str] = []

    def inspect(raw: Any, parameter_id: str) -> dict[str, Any]:
        assert raw is feature and raw == before
        called.append(parameter_id)
        return ui_quantity_parameter(raw, parameter_id)

    monkeypatch.setattr(edit_registry, "ui_quantity_parameter", inspect)
    with pytest.raises(ShapeValidationError) as caught:
        quantity_parameter(
            feature, "SET_EXTRUDE_DEPTH" if position == 2 else "SET_FILLET_RADIUS"
        )
    assert caught.value.failure.parameter == "entities"
    assert caught.value.failure.reason == "query_filter_unproven"
    assert caught.value.query_filter is not None
    assert called == ["depth" if position == 2 else "radius"]
    assert feature == before


@pytest.mark.parametrize("kind", ["SET_SUPPRESSED", "SET_UNSUPPRESSED"])
def test_suppression_transmits_only_attributes_with_opaque_replacement_parameters(
    harness: Harness, kind: str
) -> None:
    provider = initial_provider(kind)
    corrupt(provider.data, 3, "filter")
    original = deepcopy(provider.data["features"][-1]["parameters"])
    with running(harness, provider):
        req, preview = plan_for(harness, 3, kind)
        assert approve(harness, req, preview).state == "verified_success"
    assert provider.writes == 1
    assert len(provider.payloads) == 1
    body = provider.payloads[0]
    assert set(body) == {
        "btType",
        "sourceMicroversion",
        "rejectMicroversionSkew",
        "serializationVersion",
        "libraryVersion",
        "updateSuppressionAttributes",
        "features",
    }
    assert body["btType"] == "BTUpdateFeaturesCall-1748"
    assert body["updateSuppressionAttributes"] is True
    assert body["features"] == [
        {
            "btType": "BTMFeature-134",
            "featureId": target().feature_id,
            "suppressed": kind == "SET_SUPPRESSED",
        }
    ]
    assert provider.data["features"][-1]["parameters"] == original


@pytest.mark.parametrize("kind", ["SET_SUPPRESSED", "SET_UNSUPPRESSED"])
def test_suppression_cannot_expand_to_nonterminal_fillet(kind: str) -> None:
    provider = initial_provider(kind)
    features = provider.data["features"]
    other = deepcopy(features[-1])
    other["featureId"] = "synthetic-other-feature"
    features.append(other)
    op = OP.validate_python(operation_for(kind, target().handle))
    with pytest.raises(EditError, match="unsupported_target"):
        change(features, target(), op)
