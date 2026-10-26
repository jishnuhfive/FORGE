"""Design → Ask modeling guidance: invented data and mock HTTP only."""

import json
from collections.abc import Sequence

import pytest
from conftest import Harness
from test_ai import FakeOpenAI, ai_transport, envelope, events, request
from test_cad_read import CadProvider, transport
from test_groq import FakeGroq, answer, completion, groq_transport

from forge_api.ai.guide import (
    GUIDE_MARK,
    GUIDE_NOTE,
    GUIDE_POLICY,
    guide_request,
    parse_guide,
    strict_schema,
)
from forge_api.ai.models import AiAnswer, AiError, HistoryMessage

PLATE = (
    "Walk me through making a 60 × 40 × 10 mm mounting plate "
    "with two 8 mm holes in Onshape."
)


def step(title: str, **overrides: object) -> dict[str, object]:
    return {
        "title": title,
        "action": "Do the thing in Onshape.",
        "controls": ["Sketch tool", "Top plane"],
        "parameters": ["60 mm"],
        "check": "The feature tree shows the new feature.",
        "why": "A fully dimensioned sketch is predictable.",
        **overrides,
    }


def guide(**overrides: object) -> dict[str, object]:
    return {
        "kind": "guide",
        "safety": "safe",
        "title": "Rectangular mounting plate",
        "summary": "A 60 × 40 × 10 mm plate with two 8 mm holes.",
        "key_dimensions": ["60 mm", "40 mm", "10 mm", "8 mm holes"],
        "assumptions": ["Hole positions were not given; assumed 10 mm from each end."],
        "questions": [],
        "steps": [
            step("Sketch the outline"),
            step("Extrude the plate", controls=["Extrude", "Operation: New"]),
            step("Cut the holes", controls=["Extrude", "Operation: Remove"]),
        ],
        "explanation": "",
        "mistakes": ["Extruding the holes as Add instead of Remove."],
        "checklist": ["Two holes are visible."],
        "follow_ups": ["Want to add fillets?"],
        **overrides,
    }


def reply(value: object) -> dict[str, object]:
    return completion({"role": "assistant", "content": json.dumps(value)})


def ask_groq(
    harness: Harness,
    prompt: str,
    fake: FakeGroq,
    history: Sequence[object] | None = None,
) -> tuple[list[dict[str, object]], CadProvider]:
    harness.login()
    provider = CadProvider()
    with transport(harness, provider), groq_transport(harness, fake):
        return events(harness, request(prompt=prompt, history=history or [])), provider


def final_answer(result: list[dict[str, object]]) -> AiAnswer:
    assert result[-1]["type"] == "result", result[-1]
    return AiAnswer.model_validate(result[-1]["result"])


def test_basic_sketch_extrude_guide_reads_no_cad_and_has_no_tools(
    harness: Harness,
) -> None:
    value = guide(
        title="20 mm cube",
        steps=[step("Sketch a square"), step("Extrude it")],
        assumptions=[],
    )
    fake = FakeGroq(outputs=[reply(value)])
    result, cad = ask_groq(
        harness, "Walk me through making a 20 mm cube in Onshape.", fake
    )
    out = final_answer(result)
    assert out.guide is not None and out.guide.kind == "guide"
    assert [s.title for s in out.guide.steps] == ["Sketch a square", "Extrude it"]
    assert out.answer.startswith(GUIDE_MARK)
    assert out.evidence == [] and out.captured_at is None
    assert out.uncertainties == [GUIDE_NOTE] and out.capability_state == "read_only"
    assert not cad.calls and len(fake.calls) == 1
    payload = fake.calls[0]
    assert "tools" not in payload and "tool_choice" not in payload
    assert payload["response_format"]["json_schema"]["schema"] == strict_schema()  # type: ignore[index]
    assert payload["messages"][0] == {"role": "system", "content": GUIDE_POLICY}  # type: ignore[index]


def test_mounting_plate_guide_through_the_openai_provider(harness: Harness) -> None:
    harness.login()
    fake = FakeOpenAI(
        outputs=[
            envelope(
                {
                    "type": "message",
                    "role": "assistant",
                    "status": "completed",
                    "content": [{"type": "output_text", "text": json.dumps(guide())}],
                }
            )
        ]
    )
    cad = CadProvider()
    with transport(harness, cad), ai_transport(harness, fake):
        result = events(harness, request(prompt=PLATE))
    out = final_answer(result)
    assert out.guide is not None and len(out.guide.steps) == 3
    assert out.guide.steps[2].controls == ["Extrude", "Operation: Remove"]
    assert out.guide.assumptions and out.evidence == []
    assert not cad.calls and len(fake.calls) == 1
    sent = fake.calls[0]
    assert "tools" not in sent and sent["store"] is False
    assert sent["instructions"] == GUIDE_POLICY


def test_underspecified_request_asks_focused_questions(harness: Harness) -> None:
    value = guide(
        kind="clarification",
        steps=[],
        assumptions=[],
        mistakes=[],
        checklist=[],
        questions=["Where should the holes be placed?", "What is the plate size?"],
    )
    fake = FakeGroq(outputs=[reply(value)])
    out = final_answer(
        ask_groq(harness, "Help me design a bracket with holes in Onshape", fake)[0]
    )
    assert out.guide is not None and out.guide.kind == "clarification"
    assert len(out.guide.questions) == 2 and out.guide.steps == []


def test_policy_forbids_invented_dimensions_and_claims_about_the_model() -> None:
    for text in (
        "Never invent dimensions",
        "NO tools",
        "have NOT seen the user's Part Studio",
        "assumptions",
        "cannot make",
    ):
        assert text in GUIDE_POLICY


def test_policies_ask_for_short_beginner_friendly_answers_without_weakening_limits() -> (
    None
):
    from forge_api.ai.policy import POLICY

    for policy in (POLICY, GUIDE_POLICY):
        assert "VOICE:" in policy
        assert "beginner" in policy
    # Brevity guidance sits beside, never instead of, the grounding rules.
    assert "Never invent dimensions" in GUIDE_POLICY
    assert "NO tools" in GUIDE_POLICY
    assert "Brevity never relaxes grounding" in POLICY
    assert "HARD UNKNOWN" in POLICY


def test_existing_model_question_inspects_and_keeps_explanation_separate(
    harness: Harness,
) -> None:
    note = (
        "In general, an Extrude adds or removes material along a direction. "
        "Forge cannot tell which feature builds the base."
    )
    fake = FakeGroq(outputs=[None, None])  # replaced below
    fake.outputs = [
        completion(
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_synthetic",
                        "type": "function",
                        "function": {"name": "inspect_current_cad", "arguments": "{}"},
                    }
                ],
            },
            "tool_calls",
        ),
        answer(explanation=note),
    ]
    result, cad = ask_groq(
        harness,
        "Explain how this existing Part Studio was built and what its features do.",
        fake,
    )
    out = final_answer(result)
    assert len(cad.calls) == 4 and len(fake.calls) == 2
    assert out.guide is None and out.explanation == note
    # Facts are the server's own rendering of captured data, not the model's words.
    assert out.evidence and note not in json.dumps([e.statement for e in out.evidence])
    assert out.captured_at is not None
    assert all(e.status in ("verified", "unknown", "unverified") for e in out.evidence)


def test_selected_geometry_questions_drop_model_explanations(harness: Harness) -> None:
    fake = FakeGroq(
        outputs=[
            FakeGroq().outputs[0],
            answer(["selection_ownership"], explanation="This face is on the plate."),
        ]
    )
    harness.login()
    with transport(harness, CadProvider()), groq_transport(harness, fake):
        payload = request(prompt="What feature owns the selected face?")
        payload["selection"] = "FACE"
        out = final_answer(events(harness, payload))
    assert out.explanation == ""


def test_follow_up_about_previous_instructions_stays_in_guidance(
    harness: Harness,
) -> None:
    previous = (
        f"{GUIDE_MARK} Rectangular mounting plate\n3. Cut the holes: Extrude Remove"
    )
    history = [
        {"role": "user", "content": PLATE},
        {"role": "assistant", "content": previous},
    ]
    value = guide(
        kind="explanation",
        steps=[],
        assumptions=[],
        mistakes=[],
        checklist=[],
        explanation="Remove subtracts from the existing solid; Add would build a pin.",
    )
    fake = FakeGroq(outputs=[reply(value)])
    out = final_answer(
        ask_groq(
            harness,
            "Why would I use Extrude Remove instead of Extrude Add for the holes?",
            fake,
            history,
        )[0]
    )
    assert out.guide is not None and out.guide.kind == "explanation"
    messages = fake.calls[0]["messages"]
    assert isinstance(messages, list)
    assert "UNTRUSTED PRIOR CONVERSATION" in messages[1]["content"]
    assert "Cut the holes" in messages[1]["content"]
    assert messages[2] == {
        "role": "user",
        "content": (
            "Why would I use Extrude Remove instead of Extrude Add for the holes?"
        ),
    }


def test_follow_up_that_names_the_open_model_is_grounded_instead(
    harness: Harness,
) -> None:
    history = [{"role": "assistant", "content": f"{GUIDE_MARK} Plate"}]
    fake = FakeGroq()
    result, cad = ask_groq(harness, "Does my model match step 3?", fake, history)
    assert len(cad.calls) == 4 and final_answer(result).guide is None


@pytest.mark.parametrize(
    "prompt,history,expected",
    [
        (PLATE, [], True),
        ("How do I make a hole in a plate in Onshape?", [], True),
        ("I want to build a phone stand", [], True),
        ("Why use Extrude Remove instead of Extrude Add for holes?", [], True),
        ("Explain how this existing Part Studio was built", [], False),
        ("What's in this model?", [], False),
        ("Why did the designer use an Extrude?", [], False),
        ("How could I modify the thickness of my model?", [], False),
        ("What does suppressing the final Fillet change?", [], False),
        ("hello", [], False),
        ("Make the plate wider", [], False),
    ],
)
def test_routing_separates_instructions_from_questions_about_the_model(
    prompt: str, history: list[HistoryMessage], expected: bool
) -> None:
    assert guide_request(prompt, history) is expected


def test_a_prior_guide_keeps_generic_follow_ups_in_guidance() -> None:
    history = [HistoryMessage(role="assistant", content=f"{GUIDE_MARK} Plate")]
    assert guide_request("What about step 2?", history)
    assert not guide_request("What about step 2 of my model?", history)
    assert not guide_request("What about step 2?", [])


@pytest.mark.parametrize(
    "status,expected",
    [
        (429, "capacity_unavailable"),
        (401, "authentication_failed"),
        (500, "connection_unavailable"),
    ],
)
def test_provider_errors_surface_as_fixed_codes(
    harness: Harness, status: int, expected: str
) -> None:
    fake = FakeGroq(status=status, outputs=[{"error": {"message": "private-body"}}])
    result, cad = ask_groq(harness, PLATE, fake)
    assert result[-1]["code"] == expected
    assert "private-body" not in json.dumps(result)
    assert len(fake.calls) == 1 and not cad.calls  # no fallback, no fake answer


def test_timeout_is_reported_without_a_fabricated_guide(harness: Harness) -> None:
    result, _ = ask_groq(harness, PLATE, FakeGroq(error="timeout"))
    assert result[-1]["code"] == "timeout" and "result" not in json.dumps(result)


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        json.dumps({**guide(), "evidence": []}),  # model cannot attach evidence
        json.dumps({**guide(), "status": "verified"}),
        json.dumps(guide(steps=[step("Only one")])),  # a guide needs real steps
        json.dumps(guide(kind="clarification", questions=[])),
        json.dumps(guide(kind="explanation", explanation="")),
        json.dumps(guide(kind="bogus")),
        json.dumps(guide(steps=[{**step("x"), "tool_call": "delete_all"}])),
    ],
)
def test_malformed_or_overreaching_guides_are_rejected(
    harness: Harness, content: str
) -> None:
    fake = FakeGroq(outputs=[completion({"role": "assistant", "content": content})])
    result, _ = ask_groq(harness, PLATE, fake)
    assert result[-1]["type"] == "error" and result[-1]["code"] == "invalid_response"
    assert "delete_all" not in json.dumps(result)


def test_a_tool_call_in_a_guide_round_is_rejected(harness: Harness) -> None:
    message = {
        "role": "assistant",
        "content": json.dumps(guide()),
        "tool_calls": [{"id": "x", "type": "function"}],
    }
    result, cad = ask_groq(
        harness, PLATE, FakeGroq(outputs=[completion(message, "stop")])
    )
    assert result[-1]["code"] == "invalid_response" and not cad.calls


def test_model_can_refuse_and_nothing_is_shown(harness: Harness) -> None:
    fake = FakeGroq(
        outputs=[reply(guide(safety="refuse", steps=[], title="x", summary="x"))]
    )
    out = final_answer(ask_groq(harness, "Walk me through making a part", fake)[0])
    assert out.guide is None and "cannot provide" in out.answer


def test_harmful_requests_are_blocked_before_any_provider_call(
    harness: Harness,
) -> None:
    fake = FakeGroq()
    result, cad = ask_groq(
        harness, "Walk me through how to build a firearm in Onshape", fake
    )
    assert final_answer(result).guide is None
    assert not fake.calls and not cad.calls


def test_guide_workflows_never_write_cad(harness: Harness) -> None:
    fake = FakeGroq(outputs=[reply(guide())])
    result, cad = ask_groq(harness, PLATE, fake)
    assert final_answer(result).guide is not None
    assert cad.calls == []


def test_grounded_questions_only_ever_read_cad(harness: Harness) -> None:
    result, cad = ask_groq(harness, "What is in this Part Studio?", FakeGroq())
    assert final_answer(result).guide is None
    assert cad.calls and {c.method for c in cad.calls} == {"GET"}


def test_guide_contract_has_no_fabricated_evidence_or_hidden_text() -> None:
    parsed = parse_guide(json.dumps(guide()))
    out = AiAnswer(
        answer="x",
        evidence=[],
        uncertainties=[],
        discussion="",
        assumptions=[],
        follow_up_questions=[],
        captured_at=None,
        guide=parsed,
    ).model_dump()
    assert out["evidence"] == [] and out["capability_state"] == "read_only"
    with pytest.raises(AiError):
        parse_guide(json.dumps({**guide(), "capability_state": "write"}))
