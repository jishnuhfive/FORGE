"""Relationship safety without replacing ordinary graph-backed Tutor teaching."""

from typing import cast

import pytest
from test_ai_graph import model_source
from test_tutor_graph import catalog, evaluate, model

from forge_api.ai.grounding import ORDER_SEMANTICS
from forge_api.integrations.onshape.models import FeatureSummaryList
from forge_api.tutor.service import RELATIONSHIP_EXPLANATION

TEACHING = (
    "An extrude adds depth to a profile. Use it when the shape has a constant "
    "cross-section."
)
ACTION = "Consider which tool best fits the shape you want."
QUESTION = "How would a fillet change a sharp corner?"


@pytest.mark.parametrize(
    "question",
    [
        "Why did I use an extrude here?",
        "When should I use a fillet?",
        "How do I use an extrude?",
        "Why would someone use a sketch before an extrude?",
        "Why would I use a sketch before an extrude?",
        "How do I use this feature?",
        "How do I use Extrude 1?",
        "What inputs can I enter in the extrude dialog?",
        "How do I find the help references?",
        "What help references should I use for Extrude 1?",
        "Do I need help references for Extrude 1?",
        "When connected to Onshape, how do I use the fillet tool?",
        "Based on my goal, when should I use an extrude?",
        "How can I build my own sketch?",
        "What does a dependency mean?",
        "How do CAD dependencies work?",
    ],
)
def test_normal_questions_keep_teaching_with_graph_evidence(question: str) -> None:
    answer, provider = evaluate(
        model_source(),
        model(
            explanation=TEACHING,
            next_action=ACTION,
            reasoning_question=QUESTION,
            fact_ids=["order_1_2"],
        ),
        question=question,
    )
    assert "order_semantics" in {fact["id"] for fact in catalog(provider)["facts"]}
    assert answer.used_cad and ORDER_SEMANTICS in answer.unknowns
    assert answer.explanation == TEACHING != RELATIONSHIP_EXPLANATION
    assert answer.next_action == ACTION and answer.reasoning_question == QUESTION
    assert answer.observed[0].source == "cad"
    assert "returned feature order" in answer.observed[0].statement


@pytest.mark.parametrize(
    "question",
    [
        "Does Extrude 1 depend on Sketch Gate?",
        "Is Sketch Gate the parent of Extrude 1?",
        "Is Extrude 1 driven by Sketch Gate?",
        "Does this feature own that face?",
        "Does Extrude 1 use Sketch Gate as its input?",
        "Does Extrude 1 use Sketch Gate?",
        "Does this feature use that sketch?",
        "Is Extrude 1 connected to Sketch Gate?",
        "Does Extrude 1 reference Sketch Gate?",
        "Does Extrude 1 have no dependency because the relationship is missing?",
    ],
)
def test_relationship_questions_still_guard_even_bare_yes(question: str) -> None:
    answer, _ = evaluate(model_source(), model(explanation="Yes."), question=question)
    assert answer.explanation == RELATIONSHIP_EXPLANATION


@pytest.mark.parametrize("field", ["explanation", "next_action", "reasoning_question"])
@pytest.mark.parametrize(
    "claim",
    [
        "Extrude 1 depends on Sketch Gate because it comes after it.",
        "Sketch Gate owns Extrude 1.",
        "Extrude 1 is driven by Sketch Gate.",
        "Extrude 1 consumes Sketch Gate.",
        "Extrude 1 uses Sketch Gate as its input.",
        "Sketch Gate is the parent of Extrude 1.",
        "Extrude 1 is connected to Sketch Gate.",
        "Extrude 1 references Sketch Gate.",
        "Extrude 1 is based on Sketch Gate.",
        "Extrude 1 is linked to Sketch Gate.",
        "These features reference this profile.",
        "This feature has no dependency because no relationship was returned.",
        "In general, Extrude 1 depends on Sketch Gate.",
        "In general, your extrude uses your sketch as its input.",
    ],
)
def test_current_model_claims_still_guard_all_prose_fields(
    field: str, claim: str
) -> None:
    answer, _ = evaluate(
        model_source(), model(**{field: claim}, fact_ids=["order_1_2"])
    )
    assert answer.explanation == RELATIONSHIP_EXPLANATION
    assert claim not in answer.model_dump_json()
    assert "returned feature order" in answer.observed[0].statement


@pytest.mark.parametrize("field", ["explanation", "next_action", "reasoning_question"])
@pytest.mark.parametrize(
    "teaching",
    [
        "In general, a dependency means one feature uses another feature's geometry.",
        "In general, an extrude uses a sketch/profile as input.",
        "Typically, extrudes reference a sketch profile as input.",
        "In CAD, a child feature may depend on a parent feature's geometry.",
        "General CAD knowledge: dependencies connect feature inputs "
        "to earlier geometry.",
        "A dependency means one feature relies on another feature's geometry.",
        "An extrude commonly uses a sketch profile as its input.",
    ],
)
def test_explicit_general_teaching_remains_model_teaching(
    field: str, teaching: str
) -> None:
    reply = model(**{field: teaching}, fact_ids=["order_1_2"])
    answer, _ = evaluate(model_source(), reply)
    assert getattr(answer, field) == teaching
    assert answer.explanation != RELATIONSHIP_EXPLANATION
    assert ORDER_SEMANTICS in answer.unknowns
    assert [item.source for item in answer.observed] == ["cad"]


@pytest.mark.parametrize(
    "text",
    [
        "In general, extrudes use profiles as input. Extrude 1 depends on Sketch Gate.",
        "In general, extrudes use profiles as input. Your extrude owns that sketch.",
        "General CAD knowledge: features can depend on earlier geometry. "
        "In this model, Extrude 1 consumes Sketch Gate.",
        "This relationship is unknown, but Extrude 1 definitely depends "
        "on Sketch Gate.",
    ],
)
def test_general_prefix_or_unknown_word_cannot_hide_specific_claim(text: str) -> None:
    answer, _ = evaluate(model_source(), model(explanation=text))
    assert answer.explanation == RELATIONSHIP_EXPLANATION


def test_ordinary_model_advice_uses_use_input_references_and_based_on() -> None:
    text = (
        "Use Extrude 1 to explore depth. Enter an input in the dialog. "
        "Consult the help references. Based on your goal, try a rounded corner."
    )
    answer, _ = evaluate(model_source(), model(explanation=text))
    assert answer.explanation == text


@pytest.mark.parametrize("name", ["Sketch", "Extrude", "Fillet"])
def test_generic_type_used_as_feature_name_does_not_hijack_teaching(name: str) -> None:
    source = model_source()
    data = cast(FeatureSummaryList, source.documents["features"].normalized)
    data.items[0].name = name
    teaching = "In general, an extrude uses a sketch profile as input."
    answer, _ = evaluate(source, model(explanation=teaching))
    assert answer.explanation == teaching


@pytest.mark.parametrize("name", ["Gate.*[x]", "Profile Alpha"])
def test_named_inputs_are_data_and_specific_claims_still_guard(name: str) -> None:
    source = model_source()
    data = cast(FeatureSummaryList, source.documents["features"].normalized)
    data.items[0].name = name
    claim = f"In general, a feature uses {name} as its input."
    answer, _ = evaluate(source, model(explanation=claim))
    assert answer.explanation == RELATIONSHIP_EXPLANATION


def test_original_general_explanation_and_unknown_caveat_remain_allowed() -> None:
    text = (
        "In general CAD, a dependency means one feature uses another's geometry. "
        "That relationship is unknown for this model."
    )
    answer, _ = evaluate(model_source(), model(explanation=text))
    assert answer.explanation == text
