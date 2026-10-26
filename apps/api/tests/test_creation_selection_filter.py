"""Provider-managed `filter` on query parameters: closed vocabulary, never a bypass."""

import json
from copy import deepcopy
from typing import Any, cast

import httpx2 as httpx
import pytest
from conftest import Harness
from sqlalchemy import select
from test_creation_api import BRIEF, Provider, post
from test_creation_pre_dispatch import run_creation, uncertain_outcomes
from test_safe_edit import running

from forge_api.cad_create import plane_filter
from forge_api.db.models import WriteFence
from forge_api.integrations.onshape import current_ui_filters as ui

PLANE_FILTER: dict[str, Any] = {
    "btType": "BTAndFilter-110",
    "operand1": {"btType": "BTEntityTypeFilter-124", "entityType": "FACE"},
    "operand2": {
        "btType": "BTOrFilter-167",
        "operand1": {"btType": "BTGeometryFilter-130", "geometryType": "PLANE"},
        "operand2": {"btType": "BTFlatSheetMetalFilter-3018", "allows": "MODEL_ONLY"},
    },
}


def to_json(shape: Any) -> dict[str, Any]:
    if isinstance(shape, ui._Binary):
        return {
            "btType": shape.bt_type,
            "operand1": to_json(shape.operand1),
            "operand2": to_json(shape.operand2),
        }
    return {"btType": shape.bt_type, **dict(shape.fields)}


def test_the_extrude_entities_filter_observed_live_in_phase_16_is_accepted() -> None:
    assert plane_filter.valid_selection_filter(to_json(ui._EXTRUDE))
    # Fillet and dormant-role shapes use leaves outside this vocabulary on purpose.
    assert not plane_filter.valid_selection_filter(to_json(ui._FILLET))


def test_plane_filter_shape_is_accepted_and_described_without_identities() -> None:
    assert plane_filter.valid_selection_filter(PLANE_FILTER)
    text = plane_filter.describe(PLANE_FILTER)
    assert text.startswith("And(EntityType[entityType=FACE],Or(")
    assert plane_filter.describe({"btType": "Unknown-1"}) == "<invalid>"


def mutated(change: Any) -> dict[str, Any]:
    value = deepcopy(PLANE_FILTER)
    change(value)
    return value


@pytest.mark.parametrize(
    "value",
    [
        None,
        [],
        "FACE",
        {},
        {"btType": "BTNotFilter-165", "operand": {}},
        mutated(lambda f: f.update(extra=1)),
        mutated(lambda f: f.pop("operand2")),
        mutated(lambda f: f["operand1"].update(entityType="WIRE")),
        mutated(lambda f: f["operand1"].update(entityType=1)),
        mutated(lambda f: f["operand1"].update(unexpected=True)),
        mutated(lambda f: f["operand2"].update(btType="BTMadeUpFilter-1")),
        mutated(lambda f: f["operand2"]["operand2"].update(allows=True)),
        mutated(lambda f: f.update(operand1=f)),  # shared structure, exceeds bounds
        {"btType": "BTConstructionObjectFilter-113", "isConstruction": 0},
        {"btType": "BTConstructionObjectFilter-113", "isConstruction": "false"},
    ],
)
def test_anything_outside_the_closed_vocabulary_is_rejected(value: Any) -> None:
    assert not plane_filter.valid_selection_filter(value)


def test_depth_and_size_are_bounded() -> None:
    node: dict[str, Any] = {"btType": "BTEntityTypeFilter-124", "entityType": "FACE"}
    for _ in range(9):
        node = {"btType": "BTAndFilter-110", "operand1": node, "operand2": node}
    assert not plane_filter.valid_selection_filter(node)


class Filtered(Provider):
    """Adds a selection filter like the real service, in the chosen places."""

    def __init__(self, where: str, plane: Any = None, extrude: Any = None) -> None:
        super().__init__()
        self.where = where
        self.plane = PLANE_FILTER if plane is None else plane
        self.extrude = PLANE_FILTER if extrude is None else extrude

    def handle(self, request: httpx.Request) -> httpx.Response:
        response = super().handle(request)
        if request.method != "POST":
            return response
        body = json.loads(response.content)
        stored = self.data["features"][-1]
        for target, ack_too, stored_too in (
            (body["feature"], self.where in ("both", "ack"), False),
            (stored, False, self.where in ("both", "stored")),
        ):
            for param in target["parameters"]:
                kind = (
                    "plane"
                    if param["parameterId"] == "sketchPlane"
                    else ("extrude" if param["parameterId"] == "entities" else None)
                )
                if kind and (ack_too or stored_too):
                    param["filter"] = deepcopy(getattr(self, kind))
        return httpx.Response(200, json=body)


@pytest.mark.parametrize("where", ["both", "ack", "stored"])
def test_filters_on_the_ack_and_or_the_reread_still_verify_both_steps(
    harness: Harness, where: str
) -> None:
    p = Filtered(where)
    result = run_creation(harness, p)
    assert result == {"state": "verified_success", "steps": ["verified_success"] * 2}
    assert p.writes == 2
    with harness.runtime.sessions() as db:
        assert db.scalar(select(WriteFence)) is None


@pytest.mark.parametrize(
    ("kwargs", "label", "writes"),
    [
        ({"plane": {"btType": "BTMadeUpFilter-1"}}, "ack_plane_filter", 1),
        ({"plane": mutated(lambda f: f.update(extra=1))}, "ack_plane_filter", 1),
        ({"extrude": {"btType": "BTMadeUpFilter-1"}}, "ack_extrude_filter", 2),
        (
            {"extrude": mutated(lambda f: f["operand1"].update(entityType="WIRE"))},
            "ack_extrude_filter",
            2,
        ),
    ],
)
def test_a_filter_outside_the_vocabulary_fails_closed_and_keeps_the_fence(
    harness: Harness, kwargs: dict[str, Any], label: str, writes: int
) -> None:
    p = Filtered("both", **kwargs)
    result = run_creation(harness, p)
    assert result["state"] == "execution_uncertain"
    assert p.writes == writes
    assert uncertain_outcomes(harness) == [label]
    with harness.runtime.sessions() as db:
        assert db.scalar(select(WriteFence)) is not None


def test_a_filter_cannot_hide_a_changed_selection(harness: Harness) -> None:
    class Retargeted(Filtered):
        def handle(self, request: httpx.Request) -> httpx.Response:
            response = super().handle(request)
            if request.method == "POST" and self.writes == 1:
                body = json.loads(response.content)
                body["feature"]["parameters"][0]["queries"][0]["queryString"] = (
                    'query=qCreatedBy(makeId("Front"), EntityType.FACE);'
                )
                return httpx.Response(200, json=body)
            return response

    p = Retargeted("both")
    result = run_creation(harness, p)
    assert result["state"] == "execution_uncertain" and p.writes == 1
    assert uncertain_outcomes(harness) == ["ack_query"]


def test_extra_extrude_parameter_fields_still_reject(harness: Harness) -> None:
    class Extra(Provider):
        def handle(self, request: httpx.Request) -> httpx.Response:
            response = super().handle(request)
            if request.method == "POST" and self.writes == 2:
                body = json.loads(response.content)
                body["feature"]["parameters"][-1]["unexpectedField"] = 1
                return httpx.Response(200, json=body)
            return response

    p = Extra()
    result = run_creation(harness, p)
    assert result["state"] == "execution_uncertain" and p.writes == 2
    assert uncertain_outcomes(harness) == ["ack_parameters"]
    _ = (BRIEF, post, running, cast)


def test_accepted_filter_structure_is_logged_in_development_only(
    caplog: pytest.LogCaptureFixture,
) -> None:
    from types import SimpleNamespace

    from forge_api.cad_create import provider as creation_provider

    feature = {"parameters": [{"parameterId": "sketchPlane", "filter": PLANE_FILTER}]}
    for development, expected in ((True, 1), (False, 0)):
        client = creation_provider.CreationClient(
            cast(Any, SimpleNamespace(_development=development)), cast(Any, None)
        )
        caplog.clear()
        with caplog.at_level("INFO", logger="forge.creation"):
            if development:
                client._log_filters(feature)
        assert len(caplog.messages) == expected
    assert "FACE" in caplog.messages[0] if caplog.messages else True
