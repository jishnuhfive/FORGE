"""Phase 16 preparation: synthetic representations, never live CAD evidence.

Exercise the existing registry, real resolver/approval boundary and pinned mock
transport together. Do not infer current UI-created Onshape serialization here.
"""

import json
from copy import deepcopy
from typing import Any

import httpx2 as httpx
import pytest
from conftest import Harness
from fastapi import Request
from sqlalchemy import select
from test_modify_plan import (
    PlanProvider,
    _no_dispatch,
    approve,
    discover,
    inventory,
    target,
)
from test_safe_edit import running

from forge_api.cad_edits import plan_service
from forge_api.cad_edits.domain import EditError, fingerprint
from forge_api.cad_edits.plans import (
    PlanPreview,
    RenameFeature,
    SemanticPlan,
    SetFilletRadius,
)
from forge_api.db.models import WriteFence
from forge_api.integrations.onshape.edit_registry import change
from forge_api.integrations.onshape.service import ReadGate

REQUIRED = (
    (2, "bodyType"),
    (2, "operationType"),
    (2, "entities"),
    (2, "endBound"),
    (2, "depth"),
    (3, "entities"),
    (3, "radius"),
)
EDITS = (
    (2, "SET_EXTRUDE_DEPTH"),
    (3, "SET_FILLET_RADIUS"),
    (2, "RENAME_FEATURE"),
    (3, "RENAME_FEATURE"),
    (3, "SET_SUPPRESSED"),
    (3, "SET_UNSUPPRESSED"),
)


def rejected_replacement(
    harness: Harness, provider: PlanProvider, position: int
) -> None:
    """An invalid replacement cannot gain rename/quantity authority at discovery
    or by injecting a semantic operation using a remaining suppression handle.
    Phase 9 suppression deliberately does not replace parameter definitions.
    """
    with running(harness, provider):
        req, catalog = discover(harness)
        option = next((t for t in catalog.targets if t.position == position), None)
        if option is not None:
            assert option.supported_operations == ("SET_SUPPRESSED",)
            for operation in (
                RenameFeature(
                    type="RENAME_FEATURE", target=option.handle, new_name="Renamed"
                ),
                SetFilletRadius(
                    type="SET_FILLET_RADIUS", target=option.handle, quantity="3 mm"
                ),
            ):
                req.app.state.cad_gate = ReadGate()
                with pytest.raises(EditError, match="unsupported_target"):
                    plan_service.prepare(
                        req,
                        harness.runtime,
                        SemanticPlan(
                            target_catalog=catalog.target_catalog,
                            operations=(operation,),
                        ),
                    )
        _no_dispatch(harness, provider)


@pytest.mark.parametrize("position,parameter", REQUIRED)
@pytest.mark.parametrize("case", ["missing", "duplicate", "wrong_type"])
def test_each_required_parameter_is_required_unique_and_typed(
    harness: Harness, position: int, parameter: str, case: str
) -> None:
    provider = PlanProvider()
    params = provider.data["features"][position - 1]["parameters"]
    item = next(p for p in params if p["parameterId"] == parameter)
    if case == "missing":
        params.remove(item)
    elif case == "duplicate":
        params.append(deepcopy(item))
    else:
        item["btType"] = "BTMParameterString-149"
    rejected_replacement(harness, provider, position)


@pytest.mark.parametrize("position", [2, 3])
@pytest.mark.parametrize("parameters", [None, [], {}, "parameters", [None], [1], [[]]])
def test_malformed_parameter_collections_never_authorize_replacement(
    harness: Harness, position: int, parameters: Any
) -> None:
    provider = PlanProvider()
    provider.data["features"][position - 1]["parameters"] = deepcopy(parameters)
    rejected_replacement(harness, provider, position)


@pytest.mark.parametrize("position", [2, 3])
@pytest.mark.parametrize("queries", [None, [], {}, "query"])
def test_entities_require_an_explicit_nonempty_query_list(
    harness: Harness, position: int, queries: Any
) -> None:
    provider = PlanProvider()
    params = provider.data["features"][position - 1]["parameters"]
    next(p for p in params if p["parameterId"] == "entities")["queries"] = queries
    rejected_replacement(harness, provider, position)


@pytest.mark.parametrize(
    "parameter,field,value",
    [
        ("bodyType", "value", "SURFACE"),
        ("bodyType", "enumName", "ToolBodyType"),
        ("operationType", "value", "ADD"),
        ("operationType", "value", "REMOVE"),
        ("operationType", "enumName", "BooleanOperationType"),
        ("endBound", "value", "SYMMETRIC"),
        ("endBound", "value", "UP_TO_FACE"),
        ("endBound", "enumName", "OtherBoundingType"),
    ],
)
def test_extrude_requires_exact_new_solid_blind_enums(
    harness: Harness, parameter: str, field: str, value: str
) -> None:
    provider = PlanProvider()
    params = provider.data["features"][1]["parameters"]
    next(p for p in params if p["parameterId"] == parameter)[field] = value
    rejected_replacement(harness, provider, 2)


@pytest.mark.parametrize(
    "position,parameter",
    [
        (2, "hasSecondDirection"),
        (2, "secondDirectionDepth"),
        (2, "thin"),
        (2, "hasDraft"),
        (2, "draftAngle"),
        (2, "endDepth"),
        (3, "variableFillet"),
        (3, "asymmetric"),
        (3, "width"),
        (3, "crossSection"),
        (3, "conicRho"),
    ],
)
def test_richer_real_looking_shapes_do_not_gain_replacement_authority(
    harness: Harness, position: int, parameter: str
) -> None:
    provider = PlanProvider()
    feature = provider.data["features"][position - 1]
    feature["name"] = "Extrude" if position == 2 else "Fillet"
    feature["parameters"].append(
        {"btType": "BTMParameterBoolean-144", "parameterId": parameter, "value": False}
    )
    # Even a false unknown option is not assumed to be a harmless default.
    rejected_replacement(harness, provider, position)


@pytest.mark.parametrize("value", [None, 0, 1, "true", [], {}])
def test_optional_tangent_propagation_must_be_an_explicit_boolean(
    harness: Harness, value: Any
) -> None:
    provider = PlanProvider()
    provider.data["features"][-1]["parameters"][-1]["value"] = value
    rejected_replacement(harness, provider, 3)


@pytest.mark.parametrize("case", ["duplicate", "wrong_type"])
def test_optional_tangent_propagation_is_unique_and_typed(
    harness: Harness, case: str
) -> None:
    provider = PlanProvider()
    params = provider.data["features"][-1]["parameters"]
    if case == "duplicate":
        params.append(deepcopy(params[-1]))
    else:
        params[-1]["btType"] = "BTMParameterEnum-145"
    rejected_replacement(harness, provider, 3)


@pytest.mark.parametrize("position", [2, 3])
@pytest.mark.parametrize("case", ["custom", "namespace", "subfeature", "display_name"])
def test_standard_display_names_cannot_authorize_nonstandard_features(
    harness: Harness, position: int, case: str
) -> None:
    provider = PlanProvider()
    feature = provider.data["features"][position - 1]
    feature["name"] = "Extrude" if position == 2 else "Fillet"
    if case == "custom":
        feature["btType"] = "BTMOtherFeature-999"
    elif case == "namespace":
        feature["namespace"] = "synthetic/custom.fs"
    elif case == "subfeature":
        feature["subFeatures"] = [deepcopy(feature)]
    else:
        feature["featureType"] = "chamfer"
    with running(harness, provider):
        with pytest.raises(EditError):
            discover(harness)
        _no_dispatch(harness, provider)


@pytest.mark.parametrize("tangent", [None, False, True])
def test_supported_optional_tangent_variants_preserve_exact_definition(
    tangent: bool | None,
) -> None:
    features = inventory()["features"]
    params = features[-1]["parameters"]
    if tangent is None:
        params.pop()
    else:
        params[-1]["value"] = tangent
    original = deepcopy(features)
    for operation in (
        RenameFeature(type="RENAME_FEATURE", target=target().handle, new_name="Round"),
        SetFilletRadius(
            type="SET_FILLET_RADIUS", target=target().handle, quantity="3 mm"
        ),
    ):
        updated, _ = change(features, target(), operation)
        expected = deepcopy(original[-1])
        if isinstance(operation, RenameFeature):
            expected["name"] = "Round"
        else:
            expected["parameters"][1]["expression"] = "3 mm"
        assert fingerprint(updated) == fingerprint(expected)
        assert fingerprint(features) == fingerprint(original)


def operation_for(kind: str, handle: str) -> dict[str, str]:
    operation = {"type": kind, "target": handle}
    if kind == "RENAME_FEATURE":
        operation["new_name"] = "Conformance renamed"
    elif kind in ("SET_EXTRUDE_DEPTH", "SET_FILLET_RADIUS"):
        operation["quantity"] = "25 mm" if kind == "SET_EXTRUDE_DEPTH" else "3 mm"
    return operation


def plan_for(harness: Harness, position: int, kind: str) -> tuple[Request, PlanPreview]:
    req, catalog = discover(harness)
    option = next(t for t in catalog.targets if t.position == position)
    operation = operation_for(kind, option.handle)
    req.app.state.cad_gate = ReadGate()
    preview = plan_service.prepare(
        req,
        harness.runtime,
        SemanticPlan.model_validate_json(
            json.dumps(
                {"target_catalog": catalog.target_catalog, "operations": [operation]}
            )
        ),
    )
    return req, preview


def initial_provider(kind: str) -> PlanProvider:
    provider = PlanProvider()
    if kind == "SET_UNSUPPRESSED":
        provider.data["features"][-1]["suppressed"] = True
        provider.data["featureStates"]["synthetic-feature-2"]["inactive"] = True
    return provider


@pytest.mark.parametrize("position,kind", EDITS)
def test_cancel_then_fresh_single_operation_preserves_every_unrelated_field(
    harness: Harness, position: int, kind: str
) -> None:
    provider = initial_provider(kind)
    feature = provider.data["features"][position - 1]
    feature["nodeId"] = "synthetic-feature-node"
    feature["syntheticMetadata"] = {"nested": [None, False, 1, "unchanged"]}
    for param in feature["parameters"]:
        param["nodeId"] = "synthetic-parameter-" + param["parameterId"]
        if param["btType"] == "BTMParameterQuantity-147":
            param["isInteger"] = False
    before = deepcopy(provider.data)
    with running(harness, provider):
        req, preview = plan_for(harness, position, kind)
        result = plan_service.cancel(req, harness.runtime, preview.proposal_id)
        assert result.state == "cancelled" and result.operations == ("skipped",)
        assert fingerprint(provider.data) == fingerprint(before)
        _no_dispatch(harness, provider)
        with pytest.raises(EditError, match="proposal_used"):
            approve(harness, req, preview)
        req, preview = plan_for(harness, position, kind)
        result = approve(harness, req, preview)
        assert result.state == "verified_success"
        assert result.operations == ("verified_success",)
        assert provider.writes == 1
        expected = deepcopy(before)
        updated = expected["features"][position - 1]
        if kind == "RENAME_FEATURE":
            updated["name"] = "Conformance renamed"
        elif kind in ("SET_SUPPRESSED", "SET_UNSUPPRESSED"):
            updated["suppressed"] = kind == "SET_SUPPRESSED"
            expected["featureStates"][updated["featureId"]]["inactive"] = updated[
                "suppressed"
            ]
        else:
            parameter = "depth" if position == 2 else "radius"
            next(p for p in updated["parameters"] if p["parameterId"] == parameter)[
                "expression"
            ] = "25 mm" if position == 2 else "3 mm"
        expected["sourceMicroversion"] = provider.marker
        assert fingerprint(provider.data) == fingerprint(expected)
        payload = provider.payloads[0]
        assert payload["rejectMicroversionSkew"] is True
        assert payload["sourceMicroversion"] == before["sourceMicroversion"]
        if kind in ("RENAME_FEATURE", "SET_EXTRUDE_DEPTH", "SET_FILLET_RADIUS"):
            assert fingerprint(payload["feature"]) == fingerprint(updated)
        with pytest.raises(EditError, match="proposal_used"):
            approve(harness, req, preview)
        assert provider.writes == 1


class UnverifiableProvider(PlanProvider):
    """HTTP success may mutate synthetic CAD but cannot establish success alone."""

    def __init__(self, kind: str, fault: str) -> None:
        super().__init__()
        self.fault = fault
        if kind == "SET_UNSUPPRESSED":
            self.data["features"][-1]["suppressed"] = True
            self.data["featureStates"]["synthetic-feature-2"]["inactive"] = True

    def handle(self, request: httpx.Request) -> httpx.Response:
        response = super().handle(request)
        if request.method == "POST":
            data = response.json()
            if self.fault == "ack_missing_revision":
                del data["sourceMicroversion"]
            elif self.fault == "ack_unchanged_revision":
                data["sourceMicroversion"] = self.guards[-1]
            elif self.fault == "ack_missing_skew":
                del data["microversionSkew"]
            elif self.fault == "ack_wrong_identity":
                returned = data["feature"] if "feature" in data else data["features"][0]
                returned["featureId"] = "synthetic-other-feature"
            return httpx.Response(200, json=data)
        if self.writes and request.url.path.endswith("/features"):
            data = response.json()
            if self.fault == "post_read_incomplete":
                data["isComplete"] = False
            elif self.fault == "post_read_unrelated_change":
                data["features"][0]["name"] = "Unexpected sketch rename"
            elif self.fault == "post_read_missing":
                return httpx.Response(503, json={})
            return httpx.Response(200, json=data)
        return response


@pytest.mark.parametrize("position,kind", EDITS)
@pytest.mark.parametrize(
    "fault",
    [
        "ack_missing_revision",
        "ack_unchanged_revision",
        "ack_missing_skew",
        "ack_wrong_identity",
        "post_read_incomplete",
        "post_read_unrelated_change",
        "post_read_missing",
    ],
)
def test_every_operation_requires_valid_ack_and_fresh_exact_evidence_without_retry(
    harness: Harness, position: int, kind: str, fault: str
) -> None:
    provider = UnverifiableProvider(kind, fault)
    with running(harness, provider):
        req, catalog = discover(harness)
        option = next(t for t in catalog.targets if t.position == position)
        other = next(t for t in catalog.targets if t.position != position)
        operations = [
            operation_for(kind, option.handle),
            operation_for("RENAME_FEATURE", other.handle),
        ]
        req.app.state.cad_gate = ReadGate()
        preview = plan_service.prepare(
            req,
            harness.runtime,
            SemanticPlan.model_validate_json(
                json.dumps(
                    {"target_catalog": catalog.target_catalog, "operations": operations}
                )
            ),
        )
        result = approve(harness, req, preview)
        assert result.state == "execution_uncertain"
        assert result.operations == ("execution_uncertain", "skipped")
        assert provider.writes == 1
        assert plan_service.status(req, harness.runtime, preview.proposal_id) == result
        with pytest.raises(EditError, match="proposal_used"):
            approve(harness, req, preview)
        with pytest.raises(EditError, match="workspace_fenced"):
            discover(harness)
        assert provider.writes == 1
        with harness.runtime.sessions() as db:
            assert db.scalar(select(WriteFence)) is not None
