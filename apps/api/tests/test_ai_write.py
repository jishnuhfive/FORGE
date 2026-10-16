"""Invented CAD and mock transport only. Safe metadata never includes content."""

import asyncio
import json
import logging
from typing import cast

import httpx2 as httpx
import pytest
from conftest import Harness
from pydantic import SecretStr
from test_ai import FakeOpenAI, ai_transport, events, request
from test_cad_inspector import snapshot
from test_cad_read import CadProvider, transport
from test_groq import FakeGroq, answer, completion, groq_transport, inspection

from forge_api.ai.diagnostics import Reason, Stage, emit_diagnostic
from forge_api.ai.groq import GroqProvider
from forge_api.ai.models import AiError, AiRequest, ModelAnswer
from forge_api.ai.policy import REFUSAL
from forge_api.ai.provider import AgentTask
from forge_api.ai.service import run_agent
from forge_api.ai.writes import (
    NO_WRITES,
    WIDTH_UNKNOWN,
    WRITE_LIMITATION,
    write_request,
)
from forge_api.core.config import Settings
from forge_api.integrations.onshape.inspector import CadInspector, inspect

WRITE = "Make this model 20 mm wider."


@pytest.mark.parametrize("provider", ["groq", "openai"])
@pytest.mark.parametrize("failure", ["tool_use_failed", "timeout", "malformed"])
def test_explicit_write_never_calls_provider_even_if_tool_generation_would_fail(
    harness: Harness,
    caplog: pytest.LogCaptureFixture,
    provider: str,
    failure: str,
) -> None:
    harness.login()
    fake = (
        FakeGroq(
            status=400 if failure == "tool_use_failed" else 200,
            error="timeout" if failure == "timeout" else None,
            outputs=[
                {
                    "error": {
                        "code": "tool_use_failed",
                        "type": "invalid_request_error",
                        "failed_generation": "synthetic-private-model-claim",
                    }
                }
            ],
        )
        if provider == "groq"
        else FakeOpenAI(
            status=400,
            error="timeout" if failure == "timeout" else None,
            outputs=["synthetic-private-malformed-output"],
        )
    )
    cad = CadProvider()
    with (
        transport(harness, cad),
        groq_transport(harness, fake)
        if isinstance(fake, FakeGroq)
        else ai_transport(harness, fake),
        caplog.at_level(logging.DEBUG),
    ):
        harness.runtime.settings.environment = "development"
        stream = events(harness, request(prompt=WRITE))
        result = stream[-1]
    assert result["type"] == "result"
    public = result["result"]
    assert isinstance(public, dict)
    assert public["capability_state"] == "read_only"
    assert public["answer"].startswith(WRITE_LIMITATION)
    assert NO_WRITES in public["answer"] and WIDTH_UNKNOWN in public["answer"]
    assert '"Sketch 1"' in public["answer"] and '"Extrude 1"' in public["answer"]
    assert "20 mm" not in public["answer"] and "endDepth" not in public["answer"]
    assert public["discussion"] == "" and public["assumptions"] == []
    assert public["follow_up_questions"] == []
    assert public["evidence"][2]["status"] == "unknown"
    assert all(req.method == "GET" for req in cad.calls)
    assert WRITE not in caplog.text and "Sketch 1" not in caplog.text
    assert len(fake.calls) == 0 and len(cad.calls) == 4
    assert [event.get("stage") for event in stream[:-1]] == [
        "understanding",
        "inspecting",
        "preparing",
    ]
    assert "synthetic-private-model-claim" not in json.dumps(public)
    assert not [r for r in caplog.records if r.name == "forge.ai.validation"]


@pytest.mark.parametrize("state", ["stale", "revoked", "cancelled"])
def test_server_write_path_preserves_freshness_session_and_cancellation(
    state: str,
) -> None:
    async def evaluate() -> None:
        fake = FakeGroq()
        started = asyncio.Event()
        still_active = True
        inspector = inspect(snapshot(), "a" * 32)

        async def read() -> CadInspector:
            nonlocal still_active
            started.set()
            if state == "cancelled":
                await asyncio.sleep(60)
            if state == "stale":
                inspector.freshness = "stale"
            if state == "revoked":
                still_active = False
            return inspector

        async def active() -> None:
            if not still_active:
                raise AiError("session_expired")

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(fake.handle)
        ) as client:
            adapter = GroqProvider(
                Settings(_env_file=None, groq_api_key=SecretStr("synthetic-groq-key")),
                client,
            )

            async def collect() -> list[dict[str, object]]:
                return [
                    event
                    async for event in run_agent(
                        AiRequest.model_validate(request(prompt=WRITE)),
                        adapter,
                        read,
                        active,
                        "a" * 32,
                    )
                ]

            if state == "cancelled":
                task = asyncio.create_task(collect())
                await asyncio.wait_for(started.wait(), 1)
                task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await task
            else:
                with pytest.raises(AiError) as caught:
                    await collect()
                assert caught.value.code == (
                    "evidence_unavailable" if state == "stale" else "session_expired"
                )
        assert not fake.calls

    asyncio.run(evaluate())


def test_nonwrite_empty_answer_still_fails_closed_with_grounding_diagnostic(
    harness: Harness, caplog: pytest.LogCaptureFixture
) -> None:
    harness.login()
    fake = FakeGroq(outputs=[inspection(), answer([])])
    with (
        transport(harness, CadProvider()),
        groq_transport(harness, fake),
        caplog.at_level(logging.WARNING),
    ):
        harness.runtime.settings.environment = "development"
        result = events(harness)[-1]
    assert result["code"] == "invalid_response"
    assert '"reason":"empty_canonical_answer"' in caplog.text
    assert '"stage":"grounding"' in caplog.text


@pytest.mark.parametrize("provider", ["groq", "openai"])
@pytest.mark.parametrize(
    "prompt", ["What is in this Part Studio?", "What does the Extrude feature do?"]
)
def test_normal_read_questions_still_require_validated_tool_and_grounded_answer(
    harness: Harness, provider: str, prompt: str
) -> None:
    harness.login()
    fake = FakeGroq() if provider == "groq" else FakeOpenAI()
    cad = CadProvider()
    with (
        transport(harness, cad),
        (
            groq_transport(harness, fake)
            if isinstance(fake, FakeGroq)
            else ai_transport(harness, fake)
        ),
    ):
        result = events(harness, request(prompt=prompt))[-1]
    assert result["type"] == "result"
    public = result["result"]
    assert isinstance(public, dict)
    assert "Extrude 1" in public["answer"]
    assert not public["answer"].startswith(WRITE_LIMITATION)
    assert public["capability_state"] == "read_only"
    assert len(fake.calls) == 2 and len(cad.calls) == 4
    assert all(req.method == "GET" for req in cad.calls)


@pytest.mark.parametrize(
    ("content", "reason", "field", "stage"),
    [
        ("not-json-private-text", "provider_malformed_json", None, "final_output"),
        (
            json.dumps({"fact_ids": []}),
            "missing_required_field",
            "suggestion_ids",
            "final_output",
        ),
        (
            json.dumps(
                {
                    **ModelAnswer(
                        fact_ids=[],
                        suggestion_ids=[],
                        assumption_ids=[],
                        question_ids=[],
                        safety="safe",
                    ).model_dump(),
                    "synthetic-private-field-name": "CAD changed",
                }
            ),
            "structured_output_validation_failed",
            None,
            "final_output",
        ),
        (
            json.dumps(
                ModelAnswer(
                    fact_ids=["synthetic-private-unknown-fact"],
                    suggestion_ids=[],
                    assumption_ids=[],
                    question_ids=[],
                    safety="safe",
                ).model_dump()
            ),
            "unknown_fact_id",
            None,
            "grounding",
        ),
        (
            json.dumps(
                ModelAnswer(
                    fact_ids=["capability", "capability"],
                    suggestion_ids=[],
                    assumption_ids=[],
                    question_ids=[],
                    safety="safe",
                ).model_dump()
            ),
            "duplicate_canonical_id",
            None,
            "grounding",
        ),
    ],
)
def test_malformed_model_answers_still_fail_closed_without_content_logging(
    harness: Harness,
    caplog: pytest.LogCaptureFixture,
    content: str,
    reason: str,
    field: str | None,
    stage: str,
) -> None:
    harness.login()
    fake = FakeGroq(
        outputs=[inspection(), completion({"role": "assistant", "content": content})]
    )
    cad = CadProvider()
    with (
        transport(harness, cad),
        groq_transport(harness, fake),
        caplog.at_level(logging.DEBUG),
    ):
        harness.runtime.settings.environment = "development"
        result = events(harness)[-1]
    assert result == {
        "type": "error",
        "code": "invalid_response",
        "retry_after_seconds": None,
    }
    record = next(r for r in caplog.records if r.name == "forge.ai.validation")
    metadata = json.loads(record.getMessage().removeprefix("ai_validation "))
    assert metadata["reason"] == reason and metadata["stage"] == stage
    assert metadata["field"] == field and metadata["provider"] == "groq"
    assert len(metadata["request_id"]) == 32
    for private in (
        content,
        WRITE,
        "Sketch 1",
        "synthetic-private",
        "synthetic-groq-key",
        "synthetic-access",
    ):
        assert private not in caplog.text
    assert len(fake.calls) == 2 and len(cad.calls) == 4


@pytest.mark.parametrize(
    ("status", "error", "expected", "reason"),
    [
        (400, None, "invalid_response", "provider_request_rejected"),
        (200, "timeout", "timeout", "provider_timeout"),
        (503, None, "connection_unavailable", "provider_unavailable"),
    ],
)
def test_transport_failure_stage_is_distinct_and_never_retried(
    harness: Harness,
    caplog: pytest.LogCaptureFixture,
    status: int,
    error: str | None,
    expected: str,
    reason: str,
) -> None:
    harness.login()
    fake = FakeGroq(status=status, error=error)
    cad = CadProvider()
    with (
        transport(harness, cad),
        groq_transport(harness, fake),
        caplog.at_level(logging.WARNING),
    ):
        harness.runtime.settings.environment = "development"
        result = events(harness)[-1]
    assert result["code"] == expected
    assert f'"reason":"{reason}"' in caplog.text
    assert '"stage":"inspection_request"' in caplog.text
    assert WRITE not in caplog.text and "private-provider-body" not in caplog.text
    assert len(fake.calls) == 1 and len(cad.calls) == 0


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        (WRITE, True),
        ("Please change the width to 20 mm.", True),
        ("Remove this selected face.", True),
        ("Create a hole in this part.", True),
        ("Could you please make this model wider?", True),
        ("I want you to modify this design.", True),
        ("Does this model make sense?", False),
        ("What does the Extrude feature do?", False),
        ("Explain how a fillet changes the edge.", False),
        ("Do not modify the model. What features are present?", False),
        ("What is in this Part Studio?", False),
        ("What feature comes after Sketch 1?", False),
    ],
)
def test_write_presentation_routing(prompt: str, expected: bool) -> None:
    assert write_request(prompt) is expected


@pytest.mark.parametrize(
    ("output", "expected", "reason"),
    [
        (
            completion({"role": "assistant", "content": "private-text"}, "length"),
            "incomplete",
            "incomplete_response",
        ),
        (
            completion({"role": "assistant", "refusal": "private-text"}),
            "refused",
            "provider_refusal",
        ),
        (inspection(), "invalid_response", "provider_envelope_invalid"),
    ],
)
def test_read_provider_terminal_states_do_not_become_success_or_retry(
    harness: Harness,
    caplog: pytest.LogCaptureFixture,
    output: dict[str, object],
    expected: str,
    reason: str,
) -> None:
    harness.login()
    fake = FakeGroq(outputs=[inspection(), output])
    with (
        transport(harness, CadProvider()),
        groq_transport(harness, fake),
        caplog.at_level(logging.WARNING),
    ):
        harness.runtime.settings.environment = "development"
        result = events(harness)[-1]
    assert result["code"] == expected
    assert f'"reason":"{reason}"' in caplog.text
    assert '"stage":"final_output"' in caplog.text
    assert "private-text" not in caplog.text
    assert len(fake.calls) == 2


def test_structured_safety_refusal_for_read_question_remains_safe(
    harness: Harness,
) -> None:
    harness.login()
    fake = FakeGroq(outputs=[inspection(), answer([], safety="refuse")])
    cad = CadProvider()
    with transport(harness, cad), groq_transport(harness, fake):
        result = events(harness)[-1]
    assert result["type"] == "result"
    public = result["result"]
    assert isinstance(public, dict)
    assert public["answer"] == REFUSAL
    assert public["capability_state"] == "read_only" and public["evidence"] == []
    assert len(fake.calls) == 2 and all(req.method == "GET" for req in cad.calls)


def test_canonical_public_validation_failure_has_distinct_content_free_diagnostic(
    harness: Harness, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    harness.login()
    monkeypatch.setattr(
        "forge_api.ai.evidence.overview", lambda _: "private-CAD-text" * 3000
    )
    fake = FakeGroq()
    with (
        transport(harness, CadProvider()),
        groq_transport(harness, fake),
        caplog.at_level(logging.WARNING),
    ):
        harness.runtime.settings.environment = "development"
        result = events(harness)[-1]
    assert result["code"] == "invalid_response"
    assert '"reason":"canonical_response_validation_failed"' in caplog.text
    assert '"stage":"grounding"' in caplog.text
    assert "private-CAD-text" not in caplog.text


def test_diagnostic_sanitizes_even_accidental_unsafe_metadata(
    caplog: pytest.LogCaptureFixture,
) -> None:
    private = "synthetic-private-CAD-and-key"
    with caplog.at_level(logging.WARNING):
        emit_diagnostic(
            AiError(
                "invalid_response",
                reason=cast(Reason, private),
                field=private,
                http_status=999,
                provider_error_code=private,
                provider_error_type=private,
                provider_error_param=private,
            ),
            environment="development",
            provider=private,
            stage=Stage.GROUNDING,
            request_id=private,
        )
    assert private not in caplog.text
    metadata = json.loads(caplog.records[0].getMessage().removeprefix("ai_validation "))
    assert metadata == {
        "reason": Reason.PROVIDER_ENVELOPE_INVALID.value,
        "provider": "unknown",
        "stage": "grounding",
        "request_id": None,
        "field": None,
        "http_status": None,
        "provider_error_code": None,
        "provider_error_type": None,
        "provider_error_param": None,
    }


@pytest.mark.parametrize("environment", ["development", "production"])
def test_safe_field_diagnostic_never_logs_invalid_value_or_changes_public_error(
    harness: Harness, caplog: pytest.LogCaptureFixture, environment: str
) -> None:
    harness.login()
    private = "synthetic-private-model-CAD-and-secret-value"
    fake = FakeGroq(
        outputs=[inspection(), answer(["capability"], question_ids=[private])]
    )
    with (
        transport(harness, CadProvider()),
        groq_transport(harness, fake),
        caplog.at_level(logging.DEBUG),
    ):
        harness.runtime.settings.environment = environment  # type: ignore[assignment]
        result = events(harness)[-1]
    assert result == {
        "type": "error",
        "code": "invalid_response",
        "retry_after_seconds": None,
    }
    assert private not in caplog.text and WRITE not in caplog.text
    assert "Sketch 1" not in caplog.text and "synthetic-groq-key" not in caplog.text
    records = [r for r in caplog.records if r.name == "forge.ai.validation"]
    assert len(records) == (1 if environment == "development" else 0)
    if records:
        metadata = json.loads(records[0].getMessage().removeprefix("ai_validation "))
        assert metadata["reason"] == "unsupported_enum_value"
        assert metadata["stage"] == "final_output"
        assert metadata["field"] == "question_ids[]"
        assert set(metadata) == {
            "reason",
            "provider",
            "stage",
            "request_id",
            "field",
            "http_status",
            "provider_error_code",
            "provider_error_type",
            "provider_error_param",
        }


@pytest.mark.parametrize("environment", ["development", "production"])
@pytest.mark.parametrize(
    "code", ["tool_use_failed", "invalid_value", "private-error-code"]
)
def test_groq_400_exposes_only_allowlisted_error_metadata_in_development(
    harness: Harness, caplog: pytest.LogCaptureFixture, environment: str, code: str
) -> None:
    harness.login()
    fake = FakeGroq(
        status=400,
        outputs=[
            {
                "error": {
                    "code": code,
                    "type": "invalid_request_error",
                    "param": "tool_choice",
                    "message": "private-provider-message-with-prompt-and-CAD",
                    "failed_generation": "private-provider-generation-and-instructions",
                }
            }
        ],
    )
    cad = CadProvider()
    with (
        transport(harness, cad),
        groq_transport(harness, fake),
        caplog.at_level(logging.DEBUG),
    ):
        harness.runtime.settings.environment = environment  # type: ignore[assignment]
        result = events(harness)[-1]
    assert result == {
        "type": "error",
        "code": "invalid_response",
        "retry_after_seconds": None,
    }
    assert "private-" not in caplog.text and WRITE not in caplog.text
    records = [r for r in caplog.records if r.name == "forge.ai.validation"]
    assert len(records) == (1 if environment == "development" else 0)
    if records:
        metadata = json.loads(records[0].getMessage().removeprefix("ai_validation "))
        assert metadata["provider_error_code"] == (
            None if code.startswith("private") else code
        )
        assert metadata["provider_error_type"] == "invalid_request_error"
        assert metadata["provider_error_param"] == "tool_choice"
        assert (
            metadata["http_status"] == 400 and metadata["stage"] == "inspection_request"
        )
    assert len(fake.calls) == 1
    assert not cad.calls


def test_inventory_and_write_inspection_requests_differ_only_in_user_content() -> None:
    async def compare() -> None:
        payloads = []
        for prompt in ("What is in this Part Studio?", WRITE):
            fake = FakeGroq()
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(fake.handle)
            ) as client:
                provider = GroqProvider(
                    Settings(
                        _env_file=None, groq_api_key=SecretStr("synthetic-groq-key")
                    ),
                    client,
                )
                await provider.request_inspection(
                    AgentTask(prompt, ()), request_id="a" * 32
                )
            first = fake.calls[0]
            messages = first.pop("messages")
            assert isinstance(messages, list)
            assert [m["role"] for m in messages] == ["system", "user", "user"]
            assert messages[1]["content"].endswith("[]")
            assert messages[2]["content"] == prompt
            payloads.append((first, messages[0], messages[1]))
            assert "response_format" not in first and "temperature" not in first
            assert "max_tokens" not in first and "store" not in first
            assert (
                "reasoning_format" not in first
                and "disable_tool_validation" not in first
            )
        assert payloads[0] == payloads[1]

    asyncio.run(compare())
