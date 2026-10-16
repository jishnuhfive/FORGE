"""Invented evidence only: presentation must never strengthen captured semantics."""

import json

import pytest
from pydantic import ValidationError
from test_cad_inspector import snapshot

from forge_api.ai.evidence import project, resolve
from forge_api.ai.models import AiError, Fact, ModelAnswer
from forge_api.ai.presentation import PARAMETER_CAVEAT, SUGGESTIONS
from forge_api.integrations.onshape.inspector import InspectorParameter, inspect


def model(**overrides: object) -> ModelAnswer:
    return ModelAnswer.model_validate(
        {
            "fact_ids": ["feature_1", "feature_2", "parts", "bodies"],
            "suggestion_ids": [],
            "assumption_ids": [],
            "question_ids": [],
            "safety": "safe",
            **overrides,
        }
    )


@pytest.mark.parametrize("statement", ["", " ", "\t\n", "\u00a0"])
def test_blank_evidence_is_rejected(statement: str) -> None:
    with pytest.raises(ValidationError):
        Fact(id="feature_1", statement=statement, status="verified")


def test_resolver_rejects_internal_blank_fact_too() -> None:
    inspector = inspect(snapshot(), "a" * 32)
    _, facts = project(inspector, "none")
    facts["feature_1"] = Fact.model_construct(
        id="feature_1", statement=" \n ", status="verified"
    )
    with pytest.raises(AiError):
        resolve(model(), facts, inspector.source.captured_at)


def test_inventory_is_concise_grounded_and_does_not_upgrade_active() -> None:
    inspector = inspect(snapshot(), "a" * 32)
    inspector.bodies.items[0].face_count = 6
    # "complete" means field coverage, never sketch correctness/constraint state.
    inspector.features.items[0].completeness = "complete"
    inspector.features.items[0].parameters = [
        InspectorParameter(
            label="Entities", kind="query_count", state="available", count=1
        ),
        InspectorParameter(
            label="Option", kind="boolean", state="available", boolean=False
        ),
    ]
    payload, facts = project(inspector, "unknown")
    before = inspector.model_dump()
    result = resolve(
        model(
            fact_ids=["parameter_1_1", "parameter_1_2", "features_completeness"],
            suggestion_ids=["check_material"],
        ),
        facts,
        inspector.source.captured_at,
        prompt="What is in this Part Studio?",
        inspector=inspector,
    )
    assert '"Sketch 1", followed by "Extrude 1"' in result.answer
    assert "2 active features" in result.answer and '"Part 1"' in result.answer
    assert "6 face entries" in result.answer
    assert "Edge and vertex counts remain unverified" in result.answer
    assert all(
        term not in result.answer
        for term in (
            "query_count",
            "boolean",
            "enum",
            "complete",
            "fully constrained",
            "passed",
        )
    )
    assert "parameter_1_1" not in [f.id for f in result.evidence]
    assert all(f.statement.strip() for f in result.evidence)
    assert result.discussion == ""
    assert any("exact mass" in item for item in result.uncertainties)
    assert any("validation" in item for item in result.uncertainties)
    assert (
        json.loads(payload)["cad_evidence"]["features"]["items"][0]["completeness"]
        == "complete"
    )
    assert inspector.model_dump() == before


def test_parameter_details_keep_values_and_consolidate_caveats() -> None:
    inspector = inspect(snapshot(), "a" * 32)
    inspector.features.items[0].parameters = [
        InspectorParameter(
            label="Entities", kind="query_count", state="available", count=2
        ),
        InspectorParameter(
            label="Option", kind="boolean", state="available", boolean=False
        ),
    ]
    _, facts = project(inspector, "none")
    result = resolve(
        model(fact_ids=["parameter_1_1", "parameter_1_2"]),
        facts,
        inspector.source.captured_at,
        prompt="Explain the sketch parameters.",
        inspector=inspector,
    )
    assert (
        "selection query returned 2 entries" in result.answer
        and "false" in result.answer
    )
    assert "query_count" not in result.answer and "boolean" not in result.answer
    assert "Expressions are not evaluated" not in result.answer
    assert result.uncertainties.count(PARAMETER_CAVEAT) == 1


@pytest.mark.parametrize(
    "word",
    [
        "complete",
        "valid",
        "correct",
        "fully constrained",
        "finished",
        "manufacturable",
        "passed",
    ],
)
def test_model_cannot_publish_semantic_upgrades_in_free_discussion(word: str) -> None:
    with pytest.raises(ValidationError):
        model(discussion=f"The sketch is active and {word}.")
    with pytest.raises(ValidationError):
        model(suggestion_ids=[f"The sketch is {word}."])


def test_suggestions_are_optional_reviewed_next_steps_not_cad_restatements() -> None:
    inspector = inspect(snapshot(), "a" * 32)
    _, facts = project(inspector, "none")
    result = resolve(
        model(suggestion_ids=["review_dimensions"]), facts, inspector.source.captured_at
    )
    assert result.discussion == SUGGESTIONS["review_dimensions"]
    assert (
        result.discussion not in result.answer and "Sketch 1" not in result.discussion
    )
    assert resolve(model(), facts, inspector.source.captured_at).discussion == ""
    with pytest.raises(AiError):
        resolve(
            model(suggestion_ids=["check_material", "check_material"]),
            facts,
            inspector.source.captured_at,
        )


def test_empty_and_partial_inventory_never_turn_unknown_into_zero_or_solid() -> None:
    inspector = inspect(
        snapshot(
            features={"features": [], "isComplete": True},
            parts=[],
            bodies={"bodies": []},
        ),
        "a" * 32,
    )
    _, facts = project(inspector, "none")
    result = resolve(
        model(fact_ids=["features", "parts", "bodies"]),
        facts,
        inspector.source.captured_at,
        prompt="Describe this model",
        inspector=inspector,
    )
    assert "0 captured features" in result.answer and "solid" not in result.answer
    inspector.source.features.count = None
    inspector.source.parts.count = None
    _, facts = project(inspector, "unknown")
    result = resolve(
        model(fact_ids=["features"]),
        facts,
        inspector.source.captured_at,
        prompt="Summarize this Part Studio",
        inspector=inspector,
    )
    assert "total feature count is unknown" in result.answer
    assert "total part count is unknown" in result.answer
    assert "0 captured features" not in result.answer
