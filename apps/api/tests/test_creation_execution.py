"""Offline kernel checks; no live adapter or approval endpoint is installed."""

from copy import deepcopy
from typing import Any

import pytest
from test_safe_edit import M0, M1, bodies, config, features

from forge_api.cad_create.compile import compile_brief
from forge_api.cad_create.evidence import CreationEvidence, verify_added
from forge_api.cad_create.execution import execute
from forge_api.cad_create.models import Dimension, PlateWithHolesBrief
from forge_api.cad_create.provider import feature
from forge_api.cad_edits.domain import EditError


def empty() -> CreationEvidence:
    inventory = features()
    inventory.update(features=[], featureStates={}, rollbackIndex=0)
    body = bodies()
    body["bodies"] = []
    return CreationEvidence.project(M0, inventory, config(), body)


def plan() -> Any:
    return compile_brief(
        PlateWithHolesBrief(
            width=Dimension(value=60, unit="mm"),
            length=Dimension(value=40, unit="mm"),
            thickness=Dimension(value=10, unit="mm"),
        )
    )


@pytest.mark.parametrize(
    "change",
    [
        "none",
        "nonempty",
        "body",
        "incomplete",
        "skew",
        "revision",
        "configured",
        "rollback",
        "library",
    ],
)
def test_empty_projection_is_separate_and_closed(change: str) -> None:
    e = empty()
    inv, cfg, body = deepcopy((e.inventory, e.configuration, e.bodies))
    if change == "nonempty":
        inv.update(features=features()["features"], rollbackIndex=3)
    elif change == "body":
        body["bodies"] = bodies()["bodies"]
    elif change == "incomplete":
        inv["isComplete"] = False
    elif change == "skew":
        inv["microversionSkew"] = True
    elif change == "revision":
        inv["sourceMicroversion"] = M1
    elif change == "configured":
        cfg["currentConfiguration"] = [{}]
    elif change == "rollback":
        inv["rollbackIndex"] = False
    elif change == "library":
        inv["libraryVersion"] = True
    if change == "none":
        CreationEvidence.project(M0, inv, cfg, body).require_empty()
    else:
        with pytest.raises(EditError):
            CreationEvidence.project(M0, inv, cfg, body).require_empty()


@pytest.mark.parametrize(
    "change", ["none", "extra", "prior", "config", "health", "marker"]
)
def test_added_feature_requires_fresh_exact_evidence(change: str) -> None:
    before = empty()
    ack = {**feature(plan().steps[0], {}), "featureId": "synthetic-sketch"}
    inv = deepcopy(before.inventory)
    inv.update(sourceMicroversion=M1, features=[ack], rollbackIndex=1)
    cfg = config(M1)
    body = deepcopy(before.bodies)
    body["microversionId"]["theId"] = M1
    if change == "extra":
        inv["features"].append({**ack, "featureId": "synthetic-extra"})
        inv["rollbackIndex"] = 2
    elif change == "prior":
        inv["features"][0] = {**ack, "name": "other"}
    elif change == "config":
        cfg["unrelated"] = True
    elif change == "health":
        body["errorEnum"] = "ERROR"
    elif change == "marker":
        inv["sourceMicroversion"] = M0
    if change == "none":
        verify_added(before, CreationEvidence.project(M1, inv, cfg, body), ack, M1)
    else:
        with pytest.raises(EditError):
            verify_added(before, CreationEvidence.project(M1, inv, cfg, body), ack, M1)


@pytest.mark.parametrize(
    "failure", ["none", "stale", "ack", "fresh", "transport", "preflight"]
)
def test_sequential_kernel_does_not_advance_dependency_before_verification(
    failure: str,
) -> None:
    start = empty()
    p = plan()
    events = []

    class Provider:
        current = start
        count = 0

        def capture(self) -> CreationEvidence:
            events.append("read")
            if failure == "stale" and not self.count:
                return CreationEvidence.project(
                    M0,
                    {**start.inventory, "unrelated": True},
                    start.configuration,
                    start.bodies,
                )
            return self.current

        def preflight(self, step: Any, verified: Any, before: Any) -> Any:
            events.append("preflight")
            if failure == "preflight":
                raise EditError("unsupported_target")
            if step.id == "s02":
                assert verified["s01"]["featureId"] == "synthetic-1"
            return feature(step, verified)

        def dispatch(self, payload: Any) -> Any:
            events.append("dispatch")
            self.count += 1
            if failure == "transport":
                raise EditError("onshape_unavailable")
            marker = f"{self.count + 1:024x}"
            ack = {**payload, "featureId": f"synthetic-{self.count}"}
            inv = deepcopy(self.current.inventory)
            inv.update(
                sourceMicroversion=marker,
                features=[*inv["features"], ack],
                rollbackIndex=self.count,
            )
            cfg = config(marker)
            body = deepcopy(self.current.bodies)
            body["microversionId"]["theId"] = marker
            if payload["featureType"] == "extrude":
                body["bodies"] = bodies()["bodies"]
            if failure == "fresh":
                inv["features"][-1] = {**ack, "name": "unrelated"}
            self.current = CreationEvidence.project(marker, inv, cfg, body)
            if failure == "ack":
                ack = {**ack, "name": "wrong"}
            return marker, ack

    provider = Provider()

    def journal(states: Any, dispatched: bool) -> None:
        events.append("journal")

    result = execute(p, start, provider, journal)
    if failure == "none":
        assert result.state == "verified_success" and provider.count == 2
        assert events.index("journal") < events.index("dispatch")
    else:
        assert result.state == (
            "rejected" if failure in ("stale", "preflight") else "execution_uncertain"
        )
        assert provider.count == (0 if failure in ("stale", "preflight") else 1)
        assert result.steps[-1] == "skipped"


def test_unknown_dependencies_fail_before_payload() -> None:
    with pytest.raises(EditError):
        feature(plan().steps[1], {})


@pytest.mark.parametrize(
    "mutation",
    [
        "none",
        "bookkeeping",
        "geometry",
        "construction",
        "unknown",
        "count",
        "order",
        "parameter",
        "query",
        "query_ids",
        "query_type",
        "suppression",
    ],
)
def test_closed_rectangle_acknowledgement(mutation: str) -> None:
    from forge_api.cad_create.provider import acknowledge

    before = empty()
    sent = feature(plan().steps[0], {})
    assert sent["entities"][0]["geometry"]["pntX"] == -0.03
    assert sent["entities"][0]["geometry"]["pntY"] == -0.02
    assert sent["entities"][0]["endParam"] == 0.06
    actual = {**deepcopy(sent), "featureId": "synthetic-sketch"}
    entity = actual["entities"][0]
    plane = actual["parameters"][0]
    if mutation == "bookkeeping":
        entity.update(
            nodeId="synthetic-node",
            index=0,
            isConstruction=False,
            parameters=[],
            entityType="CURVE",
        )
        entity["geometry"]["entityType"] = "LINE"
    elif mutation == "geometry":
        entity["geometry"]["pntX"] = 0.04
    elif mutation == "construction":
        entity["isConstruction"] = True
    elif mutation == "unknown":
        entity["unknown"] = True
    elif mutation == "count":
        actual["entities"].pop()
    elif mutation == "order":
        actual["entities"].reverse()
    elif mutation == "parameter":
        plane["unknown"] = True
    elif mutation == "query":
        plane["queries"][0]["featureId"] = "other"
    elif mutation == "query_ids":
        plane["queries"][0]["deterministicIds"] = [None]
    elif mutation == "query_type":
        plane["queries"][0]["btType"] = "unknown"
    elif mutation == "suppression":
        actual["suppressionState"] = {
            "btType": "BTMSuppressionState-1924",
            "suppressionConfigured": True,
        }
    result = {"microversionSkew": False, "sourceMicroversion": M1, "feature": actual}
    if mutation in ("none", "bookkeeping"):
        marker, ack = acknowledge(sent, result, before)
        assert marker == M1 and ack == actual
    else:
        with pytest.raises(EditError):
            acknowledge(sent, result, before)


def test_circle_operation_is_generic_and_metric() -> None:
    from forge_api.cad_create.models import (
        BasePlaneRef,
        CreateSketchCircle,
        CreationStep,
    )

    step = CreationStep(
        id="s01",
        intent="define_base_profile",
        depends_on=(),
        op=CreateSketchCircle(
            target=BasePlaneRef(plane="TOP"),
            center_x_um=1000,
            center_y_um=2000,
            diameter_um=8000,
        ),
    )
    result = feature(step, {})
    geometry = result["entities"][0]["geometry"]
    assert (
        geometry["radius"] == 0.004
        and geometry["xCenter"] == 0.001
        and geometry["yCenter"] == 0.002
    )
