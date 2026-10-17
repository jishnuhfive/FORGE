"""Public wording across grounded answer paths; no live services or CAD."""

import re

import pytest
from test_ai_presentation import model
from test_cad_inspector import snapshot

from forge_api.ai.evidence import (
    FRESHNESS,
    UNITS,
    VALIDATION,
    project,
    resolve,
    resolve_write,
)
from forge_api.ai.models import Selection
from forge_api.ai.writes import READ_ONLY
from forge_api.integrations.onshape.inspector import inspect


@pytest.mark.parametrize(
    "selection,prompt,write",
    [
        ("unknown", "What is in this Part Studio?", False),
        ("FACE", "Explain the selected face.", False),
        ("EDGE", "Explain the selected edge.", False),
        ("none", "What is selected?", False),
        ("unknown", "What is selected?", False),
        ("unknown", "Make this model 20 mm wider.", True),
    ],
)
def test_public_answers_use_timeless_copy_without_weakening_unknowns(
    selection: Selection, prompt: str, write: bool
) -> None:
    inspector = inspect(snapshot(), "a" * 32)
    _, facts = project(inspector, selection)
    result = (
        resolve_write(prompt, facts, inspector)
        if write
        else resolve(
            model(fact_ids=["mass", "units", "validation"]),
            facts,
            inspector.source.captured_at,
            prompt=prompt,
            inspector=inspector,
            selection=selection,
        )
    )
    public_text = " ".join(
        [
            result.answer,
            *result.uncertainties,
            *(fact.statement for fact in result.evidence),
        ]
    )
    assert not re.search(r"\bPhase\s+\d", public_text, re.I)
    for internal in (
        "provider-native",
        "query_count",
        "inspection_request",
        "tool_use_failed",
        "structured output",
        "provider adapter",
        "HTTP status",
        "response schema",
        "OAuth2Read",
    ):
        assert internal not in public_text
    assert result.capability_state == "read_only"
    assert result.uncertainties == [FRESHNESS, UNITS, VALIDATION]
    assert "currentness and snapshot consistency remain unverified" in FRESHNESS
    assert "haven't been independently verified" in UNITS
    assert "Validation remains unverified" in VALIDATION
    if write:
        assert result.answer.startswith(READ_ONLY)
        assert "no CAD writes" in result.answer
        assert any(
            item.id == "write_target_unknown" and item.status == "unknown"
            for item in result.evidence
        )
    if selection in ("FACE", "EDGE"):
        assert result.answer.startswith(f"One {selection.lower()} is selected.")
        assert "are currently unknown" in result.answer
        assert all(
            item.status == "unknown"
            for item in result.evidence
            if item.id
            in (
                "selection_body",
                "selection_part",
                "selection_feature",
                "selection_dimensions",
                "selection_type",
                "selection_geometry",
            )
        )
