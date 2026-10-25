"""Explicit zero-hole requests produce an empty-holes brief; nothing is assumed."""

import asyncio
import json
from typing import Any, cast

import httpx2 as httpx
import pytest
from pydantic import SecretStr

from forge_api.cad_create import natural_language as nl
from forge_api.cad_create.planner import (
    NeedsClarification,
    PlannerResult,
    PlanReady,
    plan_creation,
)
from forge_api.core.config import Settings

FAILED_LIVE = [
    "Create a 60 by 40 by 10 mm plate with no holes (0 holes).",
    "Create a solid rectangular plate. Width: 60 mm. Length: 40 mm. "
    "Thickness: 10 mm. Exactly zero holes. No cutouts.",
]
PLATE: dict[str, Any] = {
    "kind": "rect_plate_with_through_holes",
    "width": {"value": 60, "unit": "mm"},
    "length": {"value": 40, "unit": "mm"},
    "thickness": {"value": 10, "unit": "mm"},
}


def brief(holes: list[dict[str, Any]]) -> PlannerResult:
    return plan_creation({"outcome": "brief", "design": {**PLATE, "holes": holes}})


def clarify(*fields: str) -> PlannerResult:
    return plan_creation(
        {"outcome": "clarification", "reason": "missing_dimension", "fields": fields}
    )


HOLE = {
    "diameter": {"value": 8, "unit": "mm"},
    "placement": {"mode": "center"},
}


class Model:
    """Scripted stand-in for `_ask`; records the hint note of each call."""

    def __init__(self, *results: PlannerResult) -> None:
        self.results = list(results)
        self.notes: list[str] = []

    async def __call__(
        self,
        settings: Settings,
        transport: httpx.AsyncClient,
        text: str,
        request_id: str,
        note: str = "",
    ) -> PlannerResult:
        self.notes.append(note)
        return self.results.pop(0)


def run(monkeypatch: pytest.MonkeyPatch, text: str, model: Model) -> PlannerResult:
    monkeypatch.setattr(nl, "_ask", model)
    return asyncio.run(nl.interpret(cast(Any, None), cast(Any, None), text, "r"))


@pytest.mark.parametrize("text", FAILED_LIVE)
def test_exact_failed_requests_reach_a_zero_hole_brief(
    monkeypatch: pytest.MonkeyPatch, text: str
) -> None:
    model = Model(clarify("hole_count"), brief([]))
    result = run(monkeypatch, text, model)
    assert isinstance(result, PlanReady) and result.brief.holes == ()
    assert model.notes == ["", nl.ZERO_HOLES_NOTE]


@pytest.mark.parametrize("text", FAILED_LIVE)
def test_a_model_that_already_returns_the_brief_is_not_asked_twice(
    monkeypatch: pytest.MonkeyPatch, text: str
) -> None:
    model = Model(brief([]))
    assert isinstance(run(monkeypatch, text, model), PlanReady)
    assert model.notes == [""]


@pytest.mark.parametrize(
    "text",
    [
        "plate 60x40x10 mm with no holes",
        "plate 60x40x10 mm, zero holes",
        "plate 60x40x10 mm, 0 holes",
        "plate 60x40x10 mm without holes",
        "plate 60x40x10 mm without any holes",
        "plate 60x40x10 mm. Holes: 0",
        "plate 60x40x10 mm. Holes: none",
        "Plate 60x40x10 mm. No holes. No cutouts.",
        "PLATE 60x40x10 MM, NO HOLES",
    ],
)
def test_explicit_zero_hole_phrases_are_recognized(text: str) -> None:
    assert nl.states_zero_holes(text)


@pytest.mark.parametrize(
    "text",
    [
        "plate 60x40x10 mm",
        "plate 60x40x10 mm with a hole",
        "plate 60x40x10 mm with 10 holes",
        "plate 60x40x10 mm with no holes and one 8 mm hole",
        "plate 60x40x10 mm, zero holes, then drill 2 holes",
        "plate 60x40x10 mm with no holes but a slot",
        "plate 60x40x10 mm, holes: 4",
        "make a hole-free plate",
    ],
)
def test_omitted_contradictory_or_other_wording_is_not_zero_holes(text: str) -> None:
    assert not nl.states_zero_holes(text)


def test_omitted_hole_count_is_never_assumed_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = Model(clarify("hole_count"))
    result = run(monkeypatch, "Create a 60 by 40 by 10 mm plate.", model)
    assert isinstance(result, NeedsClarification)
    assert result.fields == ("hole_count",) and model.notes == [""]


def test_contradictory_request_with_a_model_hole_still_clarifies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for first in (brief([HOLE]), clarify("hole_count")):
        second = [brief([HOLE])] if isinstance(first, NeedsClarification) else []
        model = Model(first, *second)
        result = run(monkeypatch, FAILED_LIVE[0], model)
        assert isinstance(result, NeedsClarification)
        assert result.fields == ("hole_count",)
        assert result.reason == "ambiguous_intent"


def test_request_wording_with_a_hole_is_left_to_the_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    text = "Plate 60 by 40 by 10 mm with no holes and one 8 mm hole at center."
    model = Model(brief([HOLE]))
    result = run(monkeypatch, text, model)
    assert isinstance(result, PlanReady) and len(result.brief.holes) == 1
    assert model.notes == [""]


def test_missing_dimension_is_still_asked_and_hole_questions_are_dropped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = Model(clarify("thickness", "hole_count"))
    result = run(monkeypatch, "A 60 by 40 mm plate with no holes", model)
    assert isinstance(result, NeedsClarification)
    assert result.fields == ("thickness",) and model.notes == [""]


def test_unresolved_hole_only_clarification_invents_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = Model(clarify("hole_count"), clarify("hole_position"))
    result = run(monkeypatch, FAILED_LIVE[0], model)
    assert isinstance(result, NeedsClarification)
    assert result.fields == ("hole_position",)


def test_retry_that_needs_a_dimension_asks_for_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = Model(clarify("hole_count"), clarify("width", "hole_diameter"))
    result = run(monkeypatch, FAILED_LIVE[0], model)
    assert isinstance(result, NeedsClarification) and result.fields == ("width",)


def test_policy_does_not_demand_hole_position_for_a_plate_without_holes() -> None:
    assert "hole position must be explicitly stated" not in nl.POLICY
    assert "empty holes array" in nl.POLICY
    assert "never assume an unstated hole count is zero" in nl.POLICY


@pytest.mark.parametrize("text", FAILED_LIVE)
def test_hint_reaches_the_model_only_as_server_owned_instructions(text: str) -> None:
    sent: list[dict[str, Any]] = []
    answers = [
        {
            "outcome": "clarification",
            "reason": "missing_dimension",
            "fields": ["hole_count"],
        },
        {"outcome": "brief", "design": {**PLATE, "holes": []}},
    ]

    def ai(request: httpx.Request) -> httpx.Response:
        sent.append(json.loads(request.content))
        text_out = json.dumps({"result": answers[len(sent) - 1]})
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": text_out}],
                    }
                ],
            },
        )

    settings = Settings(
        forge_ai_provider="openai",
        openai_api_key=SecretStr("synthetic-only"),
        _env_file=None,
    )

    async def go() -> PlannerResult:
        async with httpx.AsyncClient(transport=httpx.MockTransport(ai)) as client:
            return await nl.interpret(settings, client, text, "r")

    result = asyncio.run(go())
    assert isinstance(result, PlanReady) and result.brief.holes == ()
    assert nl.ZERO_HOLES_NOTE not in sent[0]["instructions"]
    assert nl.ZERO_HOLES_NOTE in sent[1]["instructions"]
    assert [b["input"] for b in sent] == [text, text]
    assert all(b["tool_choice"] == "none" and "tools" not in b for b in sent)
