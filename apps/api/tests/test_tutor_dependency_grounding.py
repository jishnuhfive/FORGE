"""Human Test 3: canonical order is useful evidence, never dependency proof."""

import json
from copy import deepcopy
from typing import cast

import pytest
from conftest import Harness
from test_ai_graph import model_source
from test_cad_read import FEATURES, REF, CadProvider, transport
from test_groq import FakeGroq, groq_transport, inspection
from test_tutor_graph import catalog, evaluate, model
from test_tutor_route import answer_of, events, payload, tutor_answer

from forge_api.ai.evidence import project
from forge_api.ai.grounding import ORDER_SEMANTICS, ground
from forge_api.ai.models import Fact
from forge_api.integrations.onshape.models import FeatureSummaryList
from forge_api.tutor.service import (
    RELATIONSHIP_ACTION,
    RELATIONSHIP_EXPLANATION,
    resolve_tutor,
)

LIVE_QUESTION = "Does Extrude 1 depend on Sketch Gate?"
ORDER = '"Sketch Gate" comes before "Extrude 1" in the returned feature order.'


def canonical() -> dict[str, object]:
    _, facts = project(ground(model_source(), REF, "a" * 32), "none")
    return dict(facts)


def resolve(facts: dict[str, object], question: str = LIVE_QUESTION) -> str:
    return resolve_tutor(
        model(explanation="Yes. Sketch Gate drives Extrude 1."),
        check=None,
        facts=facts,
        used_cad=True,
        captured_at=None,
        question=question,
        cad_names=("Sketch Gate", "Extrude 1", "Fillet 1"),
    ).explanation


@pytest.mark.parametrize(
    "question",
    [
        LIVE_QUESTION,
        "Does Sketch Gate depend on Extrude 1?",
        'Does "Extrude 1" depend on "Sketch Gate"?',
        "Does 'Extrude 1' depend on 'Sketch Gate'?",
        "does extrude 1 depend on sketch gate?",
    ],
)
@pytest.mark.parametrize("field", ["explanation", "next_action", "reasoning_question"])
def test_dependency_question_surfaces_order_without_model_selected_ids(
    question: str, field: str
) -> None:
    claim = "Yes. Sketch Gate drives Extrude 1."
    answer, provider = evaluate(
        model_source(), model(**{field: claim}), question=question
    )
    assert "order_1_2" in {item["id"] for item in catalog(provider)["facts"]}
    assert "I can't confirm that relationship." in answer.explanation
    assert f"I can verify that {ORDER}" in answer.explanation
    assert "does not establish dependency" in answer.explanation
    assert '"Extrude 1" comes before "Sketch Gate"' not in answer.explanation
    assert answer.observed == []  # Server presentation cannot rely on model IDs.
    assert answer.next_action == RELATIONSHIP_ACTION
    assert answer.reasoning_question is None and ORDER_SEMANTICS in answer.unknowns
    assert claim not in answer.model_dump_json()
    for forbidden in (
        "yes",
        "no dependency",
        "owns",
        "ownership",
        "drives",
        "driven",
        "parent",
        "child",
        "consumes",
        "causality",
    ):
        assert forbidden not in answer.explanation.lower()


@pytest.mark.parametrize("availability", ["missing", "unknown", "unverified"])
def test_absent_or_unavailable_order_cannot_be_inferred_from_feature_indices(
    availability: str,
) -> None:
    facts = canonical()
    original = cast(Fact, facts.pop("order_1_2"))
    if availability != "missing":
        facts["order_1_2"] = original.model_copy(update={"status": availability})
    assert "feature_1" in facts and "feature_2" in facts
    assert resolve(facts) == RELATIONSHIP_EXPLANATION


@pytest.mark.parametrize(
    "fault",
    ["object", "id", "names", "direction", "ordinal", "suffix", "feature"],
)
def test_malformed_canonical_fact_cannot_supply_relationship_order(fault: str) -> None:
    facts = canonical()
    fact = cast(Fact, facts["order_1_2"])
    if fault == "object":
        facts["order_1_2"] = fact.model_dump()
    elif fault == "id":
        facts["order_1_2"] = fact.model_copy(update={"id": "order_2_3"})
    elif fault == "feature":
        facts["feature_1"] = Fact(
            id="feature_1", statement="Invented feature identity.", status="verified"
        )
    else:
        statement = {
            "names": fact.statement.replace("Sketch Gate", "Different Sketch"),
            "direction": fact.statement.replace("appears before", "appears after"),
            "ordinal": fact.statement.replace("first", "third"),
            "suffix": fact.statement + " Therefore it drives the extrude.",
        }[fault]
        facts["order_1_2"] = fact.model_copy(update={"statement": statement})
    assert resolve(facts) == RELATIONSHIP_EXPLANATION


@pytest.mark.parametrize("name", ["Sketch Gate", "Extrude 1", "SKETCH GATE"])
def test_duplicate_requested_name_never_guesses_a_join(name: str) -> None:
    source = model_source()
    data = cast(FeatureSummaryList, source.documents["features"].normalized)
    data.items[2].name = name
    answer, _ = evaluate(source, model(explanation="Yes."), question=LIVE_QUESTION)
    assert answer.explanation == RELATIONSHIP_EXPLANATION


@pytest.mark.parametrize(
    "question",
    [
        "Does Extrude depend on Sketch Gate?",
        "Does Extrude 1 depend on Sketch?",
        "Does Extrude 1 depend on Missing Sketch?",
        "Does Fillet 1 depend on Sketch Gate?",
        "Does Sketch Gate depend on Sketch Gate?",
        "Does Extrude 1 depend on Sketch Gate or Fillet 1?",
    ],
)
def test_unidentified_or_nonadjacent_pair_keeps_conservative_fallback(
    question: str,
) -> None:
    assert resolve(canonical(), question) == RELATIONSHIP_EXPLANATION


def test_ownership_question_keeps_safety_boundary_with_order_available() -> None:
    answer, _ = evaluate(
        model_source(),
        model(explanation="Yes. Sketch Gate owns Extrude 1.", fact_ids=["order_1_2"]),
        question="Is Extrude 1 owned by Sketch Gate?",
    )
    assert answer.explanation == RELATIONSHIP_EXPLANATION
    assert "Sketch Gate owns Extrude 1." not in answer.model_dump_json()
    assert "Yes." not in answer.explanation
    assert answer.observed[0].status == "verified"
    assert "returned feature order" in answer.observed[0].statement
    assert ORDER_SEMANTICS in answer.unknowns


@pytest.mark.parametrize("name", ['Gate.*[x] "quoted" \\ profile', "Fillet."])
def test_names_match_as_whole_literal_data(name: str) -> None:
    source = model_source()
    data = cast(FeatureSummaryList, source.documents["features"].normalized)
    data.items[0].name = name
    answer, _ = evaluate(
        source,
        model(),
        question=f"Does Extrude 1 depend on {json.dumps(name)}?",
    )
    assert f'{json.dumps(name)} comes before "Extrude 1"' in answer.explanation
    assert "I can't confirm that relationship." in answer.explanation


def test_ambiguous_quoted_label_does_not_pick_one_of_two_canonical_names() -> None:
    source = model_source()
    data = cast(FeatureSummaryList, source.documents["features"].normalized)
    data.items[2].name = '"Sketch Gate"'
    answer, _ = evaluate(
        source, model(), question='Does Extrude 1 depend on "Sketch Gate"?'
    )
    assert answer.explanation == RELATIONSHIP_EXPLANATION


def test_names_containing_question_delimiters_cannot_select_an_ambiguous_pair() -> None:
    source = model_source(count=4)
    data = cast(FeatureSummaryList, source.documents["features"].normalized)
    for item, name in zip(
        data.items, ("A", "B depend on C", "A depend on B", "C"), strict=True
    ):
        item.name = name
    answer, _ = evaluate(source, model(), question="Does A depend on B depend on C?")
    assert answer.explanation == RELATIONSHIP_EXPLANATION


def test_long_escaped_names_keep_whole_names_and_existing_explanation_bound() -> None:
    source = model_source()
    data = cast(FeatureSummaryList, source.documents["features"].normalized)
    names = ('"' * 256, "\\" * 256)
    data.items[0].name, data.items[1].name = names
    answer, _ = evaluate(
        source,
        model(),
        question=f"Does {names[1]} depend on {names[0]}?",
    )
    assert len(answer.explanation) <= 1200
    assert f"{json.dumps(names[0])} comes before {json.dumps(names[1])}" in (
        answer.explanation
    )
    assert "does not establish dependency" in answer.explanation


def test_http_dependency_answer_uses_existing_four_get_read_only_path(
    harness: Harness,
) -> None:
    harness.login()
    features = deepcopy(FEATURES)
    cast(list[dict[str, object]], features["features"])[0]["name"] = "Sketch Gate"
    cad = CadProvider(responses={**CadProvider().responses, "features": features})
    fake = FakeGroq(outputs=[inspection(), tutor_answer(explanation="Yes.")])
    with transport(harness, cad), groq_transport(harness, fake):
        answer = answer_of(
            events(harness, payload(question=LIVE_QUESTION, context=REF.model_dump()))
        )
    assert f"I can verify that {ORDER}" in answer.explanation
    assert "I can't confirm that relationship." in answer.explanation
    assert answer.observed == []
    assert len(cad.calls) == 4 and {call.method for call in cad.calls} == {"GET"}
    assert (
        len(fake.calls) == 2 and not harness.runtime.settings.forge_cad_writes_enabled
    )
    public = answer.model_dump_json()
    assert all(
        value not in public
        for value in (REF.documentId, REF.workspaceId, REF.elementId)
    )
