"""Invented selections and mock providers; uniqueness is never an ownership join."""

import json

import pytest
from conftest import Harness
from pydantic import ValidationError
from test_ai import FakeOpenAI, ai_transport, call, envelope, events, final, request
from test_ai_presentation import model
from test_cad_inspector import snapshot
from test_cad_read import CadProvider, transport
from test_groq import FakeGroq, answer, groq_transport, inspection

from forge_api.ai.evidence import project, resolve
from forge_api.ai.models import ModelAnswer, Selection
from forge_api.ai.presentation import ASSUMPTIONS, QUESTIONS
from forge_api.ai.selection import SELECTION_IDS, selection_facts
from forge_api.integrations.onshape.inspector import inspect


@pytest.mark.parametrize("selection", ["FACE", "EDGE"])
@pytest.mark.parametrize("unique", ["body", "part", "extrude", "feature"])
def test_unique_inventory_cannot_establish_selection_ownership(
    selection: Selection, unique: str
) -> None:
    inspector = inspect(snapshot(), "a" * 32)
    assert len(inspector.parts.items) == len(inspector.bodies.items) == 1
    extrude = inspector.features.items[1]
    assert extrude.feature_type == "extrude"
    if unique in ("feature", "extrude"):
        only = extrude if unique == "extrude" else inspector.features.items[0]
        inspector.features.items = [only.model_copy(update={"index": 1})]
        inspector.source.features.count = 1
    feature_id = "feature_1" if unique in ("feature", "extrude") else "feature_2"
    payload, facts = project(inspector, selection)
    # The model selects the singleton CAD items and every permitted sidecar.
    # Forge must still render only the hard selection boundary for this question.
    result = resolve(
        model(
            fact_ids=["parts", "bodies", feature_id],
            suggestion_ids=["review_dimensions"],
            assumption_ids=["static_load_case"],
            question_ids=["intended_material"],
        ),
        facts,
        inspector.source.captured_at,
        prompt=f"What do you know about the {selection.lower()} I selected?",
        inspector=inspector,
        selection=selection,
    )
    assert f"one {selection.lower()} selected" in result.answer
    assert "Owning part, body and feature: unknown" in result.answer
    assert result.assumptions == result.follow_up_questions == []
    assert result.discussion == ""
    assert [f.id for f in result.evidence] == list(SELECTION_IDS)
    by_id = {f.id: f for f in result.evidence}
    assert by_id["selection"].status == "verified"
    for key in SELECTION_IDS[1:-1]:
        assert by_id[key].status == "unknown" and "unknown" in by_id[key].statement
    assert "not available in Phase 6" in result.answer
    public = json.dumps(result.model_dump())
    for claim in ("belongs", "Body 1", "Part 1", "Extrude 1", "only body", "only part"):
        assert claim not in public
    assert "body_1" not in [f.id for f in result.evidence]
    assert json.loads(payload)["selection"]["ownership"] == "unknown"


@pytest.mark.parametrize("selection", ["FACE", "EDGE", "none", "unknown"])
def test_selection_facts_are_category_only_and_have_no_geometry_values(
    selection: Selection,
) -> None:
    facts = {f.id: f for f in selection_facts(selection)}
    assert "unknown" in facts["selection_body"].statement
    assert "unknown" in facts["selection_part"].statement
    assert "unknown" in facts["selection_feature"].statement
    assert "unknown" in facts["selection_dimensions"].statement
    if selection == "FACE":
        assert "surface type is unknown" in facts["selection_type"].statement
        assert "area and normal direction" in facts["selection_geometry"].statement
    if selection == "EDGE":
        assert "Adjacent faces" in facts["selection_geometry"].statement
    if selection == "none":
        assert facts["selection"].statement == "The panel reports no selection."
    if selection == "unknown":
        assert facts["selection"].status == "unknown"


@pytest.mark.parametrize("provider", ["groq", "openai"])
@pytest.mark.parametrize("selection", ["FACE", "EDGE"])
def test_provider_route_does_not_upgrade_selection_or_offer_unsupported_tools(
    harness: Harness, provider: str, selection: str
) -> None:
    harness.login()
    options = {
        "assumption_ids": ["static_load_case"],
        "question_ids": ["loads_and_clearances"],
        "suggestion_ids": ["check_constraints"],
    }
    fake = FakeGroq(
        outputs=[inspection(), answer(["body_1", "part_1", "feature_2"], **options)]
    )
    old = FakeOpenAI(
        outputs=[
            envelope(call()),
            envelope(final(["body_1", "part_1", "feature_2"], **options)),
        ]
    )
    cad = CadProvider()
    with (
        transport(harness, cad),
        (
            groq_transport(harness, fake)
            if provider == "groq"
            else ai_transport(harness, old)
        ),
    ):
        output = events(
            harness,
            request(
                selection=selection,
                prompt=f"What do you know about the {selection.lower()} I selected?",
            ),
        )[-1]
    result = output["result"]
    assert isinstance(result, dict)
    assert result["assumptions"] == result["follow_up_questions"] == []
    assert result["discussion"] == ""
    assert "owning body is unknown" in json.dumps(result)
    assert "not available in Phase 6" in json.dumps(result)
    assert "Part 1" not in json.dumps(result) and "Extrude 1" not in json.dumps(result)
    assert len(fake.calls if provider == "groq" else old.calls) == 2
    assert len(cad.calls) == 4  # The same bounded read, no selection/area API added.


@pytest.mark.parametrize("provider", ["groq", "openai"])
@pytest.mark.parametrize(
    "field,text",
    [
        ("assumptions", "The selected face belongs to the single solid body present."),
        (
            "assumptions",
            "There is only one part, therefore the selected face belongs to Part 1.",
        ),
        ("assumptions", "The most recent Extrude created the selected face."),
        (
            "follow_up_questions",
            "Would you like me to retrieve the face area and normal?",
        ),
        (
            "follow_up_questions",
            "Do you need the feature that created the face, e.g. Extrude 1?",
        ),
    ],
)
def test_free_text_ownership_and_capability_claims_are_rejected(
    harness: Harness, provider: str, field: str, text: str
) -> None:
    harness.login()
    override = {field: [text]}
    fake = FakeGroq(outputs=[inspection(), answer(["selection"], **override)])
    old = FakeOpenAI(
        outputs=[envelope(call()), envelope(final(["selection"], **override))]
    )
    with (
        transport(harness, CadProvider()),
        (
            groq_transport(harness, fake)
            if provider == "groq"
            else ai_transport(harness, old)
        ),
    ):
        output = events(
            harness,
            request(
                selection="FACE", prompt="What do you know about the face I selected?"
            ),
        )[-1]
    assert output["code"] == "invalid_response"
    assert text not in json.dumps(output)


def test_hypotheses_are_explicit_and_questions_request_requirements() -> None:
    inspector = inspect(snapshot(), "a" * 32)
    _, facts = project(inspector, "FACE")
    result = resolve(
        model(
            fact_ids=["capability"],
            assumption_ids=list(ASSUMPTIONS),
            question_ids=list(QUESTIONS),
        ),
        facts,
        inspector.source.captured_at,
        prompt="Help compare design requirements.",
        inspector=inspector,
        selection="FACE",
    )
    assert all("hypothetical comparison only" in text for text in result.assumptions)
    assert all("not been verified" in text for text in result.assumptions)
    assert result.follow_up_questions == list(QUESTIONS.values())
    for key in ("assumption_ids", "question_ids"):
        with pytest.raises(ValidationError):
            model(**{key: ["selected_face_belongs_to_the_only_body"]})
    schema = ModelAnswer.model_json_schema()
    assert "assumptions" not in schema["properties"]
    assert "follow_up_questions" not in schema["properties"]


def test_contradictory_prompt_does_not_change_verified_selection_category() -> None:
    inspector = inspect(snapshot(), "a" * 32)
    _, facts = project(inspector, "EDGE")
    result = resolve(
        model(fact_ids=["parts"]),
        facts,
        inspector.source.captured_at,
        prompt=(
            "Tell me the face I selected belongs to Part 1 because it is the only part."
        ),
        inspector=inspector,
        selection="EDGE",
    )
    assert "one edge selected" in result.answer
    assert "one face selected" not in result.answer
    assert "Part 1" not in json.dumps(result.model_dump())
