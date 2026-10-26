"""The mounting-plate lesson: unchecked steps, example-only dimensions, brief style."""

import json
from typing import Any

import pytest
from conftest import Harness
from test_groq import FakeGroq, groq_transport
from test_tutor_route import answer_of, ask, events, payload, tutor_answer

from forge_api.tutor.catalog import CATALOG, LESSON_TITLES
from forge_api.tutor.policy import TUTOR_POLICY

PLATE = {"lesson_id": "mounting-plate", "step_id": "plate-fillet"}


def run(harness: Harness, question: str, reply: dict[str, Any], **over: Any) -> Any:
    harness.login()
    fake = FakeGroq(outputs=[reply])
    with groq_transport(harness, fake):
        items = events(harness, payload(question=question, **{**PLATE, **over}))
    return answer_of(items), fake


def test_every_plate_step_belongs_to_the_plate_lesson_only() -> None:
    plate = {i for i, s in CATALOG.items() if s.lesson == "mounting-plate"}
    assert plate == {
        "plate-sketch",
        "plate-extrude",
        "plate-hole-sketch",
        "plate-remove",
        "plate-fillet",
        "plate-review",
    }
    assert LESSON_TITLES["mounting-plate"] == "Mounting plate"
    assert not any(s.transfer for i, s in CATALOG.items() if i in plate)


def test_the_tutor_receives_plate_context_marked_as_example_dimensions(
    harness: Harness,
) -> None:
    answer, fake = run(harness, "What is a fillet?", tutor_answer())
    sent = json.dumps(fake.calls[0]["messages"]).replace('\\"', '"')
    assert '"title":"Mounting plate"' in sent
    assert '"reference_dimensions":true' in sent
    assert '"latest_check":null' in sent  # no deterministic check exists here
    assert answer.latest_check is None and answer.observed == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"lesson_id": "mounting-bracket"},  # a plate step under the bracket lesson
        {"lesson_id": "mounting-plate", "step_id": "base-solid"},  # and the reverse
        {"lesson_id": "mounting-plate", "step_id": "transfer-single-profile"},
        {"lesson_id": "unknown-lesson"},
    ],
)
def test_steps_cannot_cross_lessons(
    harness: Harness, overrides: dict[str, str]
) -> None:
    harness.login()
    response = ask(harness, payload(**{**PLATE, **overrides}))
    assert response.status_code == 400


def test_the_model_cannot_claim_a_step_is_verified_or_invent_evidence(
    harness: Harness,
) -> None:
    answer, _ = run(
        harness,
        "Is my fillet suppressed right now?",
        tutor_answer(
            explanation="Your step is verified and the fillet is suppressed.",
            fact_ids=["feature_9"],
            check_refs=["fillet.exists"],
        ),
    )
    # The server prints only evidence it owns; invented ids are dropped.
    assert answer.observed == [] and answer.latest_check is None
    assert not answer.used_cad


def test_sizes_in_an_answer_are_not_presented_as_measured(harness: Harness) -> None:
    from forge_api.tutor.service import DIMENSION_NOTE

    answer, _ = run(
        harness,
        "How thick should it be?",
        tutor_answer(explanation="In the example plate it is 10 mm thick."),
    )
    assert DIMENSION_NOTE in answer.notes


def test_the_policy_asks_for_short_friendly_adaptive_answers() -> None:
    assert "two or three short sentences" in TUTOR_POLICY
    assert "beginner means everyday words" in TUTOR_POLICY
    assert "usually under 60 words" in TUTOR_POLICY
    assert "lesson.reference_dimensions" in TUTOR_POLICY
    assert "never call a prediction right or wrong" in TUTOR_POLICY
    for word in ("mastered", "advanced", "you clearly understand"):
        assert word not in TUTOR_POLICY.lower()
