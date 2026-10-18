"""Tutor model access. Operator-selected provider only, no fallback, no new endpoint.

Reuses the existing transport (`post_json`), settings, request budgets and tool-call
validation. Two rounds at most: (1) the model may ask to inspect the current CAD,
(2) a strict structured answer. There is no automatic retry.
"""

import json
from typing import Protocol, cast

import httpx2 as httpx
from pydantic import ValidationError

from forge_api.ai.adapter import TOOL as OPENAI_TOOL
from forge_api.ai.diagnostics import Reason, validation_details
from forge_api.ai.groq import (
    TOOL as GROQ_TOOL,
)
from forge_api.ai.groq import (
    GroqProvider,
    message,
    replayed_call,
    tool_call_id,
)
from forge_api.ai.models import AiError
from forge_api.ai.transport import OPENAI_ENDPOINT, post_json
from forge_api.core.config import Settings
from forge_api.integrations.onshape.client import bounded_json

from .context import context_message
from .models import TutorMessage, TutorModelAnswer
from .policy import DECIDE, TUTOR_POLICY

DECIDE_TOKENS = 512
ANSWER_TOKENS = 1536
MAX_CONTENT_CHARS = 12000
TOOL_NAME = "inspect_current_cad"


class TutorTask:
    def __init__(
        self,
        question: str,
        history: tuple[TutorMessage, ...],
        context: dict[str, object],
        can_inspect: bool,
    ) -> None:
        self.question = question
        self.history = history
        self.context = context
        self.can_inspect = can_inspect


class TutorProvider(Protocol):
    async def decide(self, task: TutorTask, *, request_id: str) -> bool:
        """True when the model asked to inspect current CAD (a validated call)."""
        ...

    async def answer(
        self, evidence: str | None, *, request_id: str
    ) -> TutorModelAnswer:
        """One strict structured answer. State dies with this provider instance."""
        ...


def parse_tutor_answer(content: str) -> TutorModelAnswer:
    try:
        value = bounded_json(content.encode())
    except ValueError, UnicodeError:
        raise AiError(
            "invalid_response", reason=Reason.PROVIDER_MALFORMED_JSON
        ) from None
    try:
        return TutorModelAnswer.model_validate(value)
    except ValidationError as error:
        reason, field = validation_details(error)
        raise AiError("invalid_response", reason=reason, field=field) from None


def conversation(task: TutorTask) -> list[dict[str, object]]:
    """Context is trusted; prior conversation and the question are untrusted data."""
    history = json.dumps([m.model_dump() for m in task.history], ensure_ascii=False)
    return [
        {"role": "user", "content": context_message(task.context)},
        {
            "role": "user",
            "content": "UNTRUSTED PRIOR CONVERSATION (may be outdated):\n" + history,
        },
        {"role": "user", "content": task.question},
    ]


class GroqTutor:
    def __init__(self, settings: Settings, transport: httpx.AsyncClient) -> None:
        self._groq = GroqProvider(settings, transport)
        self._base: list[dict[str, object]] | None = None
        self._call_id: str | None = None

    async def decide(self, task: TutorTask, *, request_id: str) -> bool:
        if self._base is not None:
            raise AiError("invalid_response", reason=Reason.TOOL_LOOP_STATE_ERROR)
        self._base = conversation(task)
        if not task.can_inspect:
            return False  # No CAD context was supplied: nothing to inspect.
        result = message(
            await self._groq.request(
                {
                    "messages": [
                        {"role": "system", "content": TUTOR_POLICY + DECIDE},
                        *self._base,
                    ],
                    "tools": [GROQ_TOOL],
                    "parallel_tool_calls": False,
                    "tool_choice": "auto",
                    "max_completion_tokens": DECIDE_TOKENS,
                },
                request_id,
            ),
            tool=None,
        )
        if not result.get("tool_calls"):
            return False  # Any text here is discarded; the answer round decides.
        self._call_id = tool_call_id(result)
        return True

    async def answer(
        self, evidence: str | None, *, request_id: str
    ) -> TutorModelAnswer:
        if self._base is None:
            raise AiError("invalid_response", reason=Reason.TOOL_LOOP_STATE_ERROR)
        messages: list[dict[str, object]] = [
            {"role": "system", "content": TUTOR_POLICY},
            *self._base,
        ]
        if self._call_id is not None and evidence is not None:
            messages += [
                replayed_call(self._call_id),
                {"role": "tool", "tool_call_id": self._call_id, "content": evidence},
            ]
        self._base = None
        self._call_id = None
        result = message(
            await self._groq.request(
                {
                    "messages": messages,
                    "max_completion_tokens": ANSWER_TOKENS,
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {
                            "name": "forge_tutor_answer",
                            "strict": True,
                            "schema": TutorModelAnswer.model_json_schema(),
                        },
                    },
                    # No tools: Groq forbids tool use with Structured Outputs.
                },
                request_id,
            ),
            tool=False,
        )
        content = result.get("content")
        if (
            result.get("tool_calls")
            or not isinstance(content, str)
            or len(content) > MAX_CONTENT_CHARS
        ):
            raise AiError("invalid_response", reason=Reason.FINAL_CONTENT_INVALID)
        return parse_tutor_answer(content)


class OpenAITutor:
    def __init__(self, settings: Settings, transport: httpx.AsyncClient) -> None:
        self._settings = settings
        self._transport = transport
        self._base: list[dict[str, object]] | None = None
        self._call: tuple[str, dict[str, object]] | None = None

    async def _respond(
        self,
        items: list[dict[str, object]],
        *,
        instructions: str,
        extra: dict[str, object],
        request_id: str,
    ) -> list[dict[str, object]]:
        key = self._settings.openai_api_key
        if key is None:
            raise AiError("not_configured")
        payload: dict[str, object] = {
            "model": self._settings.forge_openai_model,
            "reasoning": {"effort": self._settings.forge_openai_reasoning_effort},
            "store": False,
            "background": False,
            "stream": False,
            "instructions": instructions,
            "input": items,
            "tools": [OPENAI_TOOL],
            "parallel_tool_calls": False,
            **extra,
        }
        raw = await post_json(
            self._transport, OPENAI_ENDPOINT, key, payload, request_id
        )
        if (
            not isinstance(raw, dict)
            or raw.get("status") != "completed"
            or not isinstance(raw.get("output"), list)
        ):
            raise AiError("invalid_response", reason=Reason.PROVIDER_ENVELOPE_INVALID)
        output = cast(list[dict[str, object]], raw["output"])
        if not all(isinstance(item, dict) for item in output):
            raise AiError("invalid_response", reason=Reason.PROVIDER_ENVELOPE_INVALID)
        return output

    async def decide(self, task: TutorTask, *, request_id: str) -> bool:
        if self._base is not None:
            raise AiError("invalid_response", reason=Reason.TOOL_LOOP_STATE_ERROR)
        self._base = conversation(task)
        if not task.can_inspect:
            return False
        output = await self._respond(
            self._base,
            instructions=TUTOR_POLICY + DECIDE,
            extra={
                "tool_choice": "auto",
                "max_output_tokens": ANSWER_TOKENS,
            },
            request_id=request_id,
        )
        calls = [item for item in output if item.get("type") == "function_call"]
        if not calls:
            return False
        call = calls[0]
        identifier = call.get("call_id")
        if (
            len(calls) != 1
            or call.get("name") != TOOL_NAME
            or not isinstance(identifier, str)
            or not isinstance(call.get("arguments"), str)
        ):
            raise AiError("invalid_response", reason=Reason.TOOL_CALL_SHAPE_INVALID)
        if bounded_json(str(call["arguments"]).encode()) != {}:
            raise AiError("invalid_response", reason=Reason.TOOL_ARGUMENTS_INVALID)
        self._call = (
            identifier,
            {
                "type": "function_call",
                "name": TOOL_NAME,
                "call_id": identifier,
                "arguments": "{}",
            },
        )
        return True

    async def answer(
        self, evidence: str | None, *, request_id: str
    ) -> TutorModelAnswer:
        if self._base is None:
            raise AiError("invalid_response", reason=Reason.TOOL_LOOP_STATE_ERROR)
        items = list(self._base)
        if self._call is not None and evidence is not None:
            identifier, replay = self._call
            items += [
                replay,
                {
                    "type": "function_call_output",
                    "call_id": identifier,
                    "output": evidence,
                },
            ]
        self._base = None
        self._call = None
        output = await self._respond(
            items,
            instructions=TUTOR_POLICY,
            extra={
                "tool_choice": "none",
                "max_output_tokens": ANSWER_TOKENS,
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": "forge_tutor_answer",
                        "strict": True,
                        "schema": TutorModelAnswer.model_json_schema(),
                    }
                },
            },
            request_id=request_id,
        )
        messages = [item for item in output if item.get("type") == "message"]
        if len(messages) != 1 or len(output) != 1:
            raise AiError("invalid_response", reason=Reason.PROVIDER_ENVELOPE_INVALID)
        content = messages[0].get("content")
        if (
            not isinstance(content, list)
            or len(content) != 1
            or not isinstance(content[0], dict)
        ):
            raise AiError("invalid_response", reason=Reason.PROVIDER_ENVELOPE_INVALID)
        if content[0].get("type") == "refusal":
            raise AiError("refused")
        text = content[0].get("text")
        if (
            content[0].get("type") != "output_text"
            or not isinstance(text, str)
            or len(text) > MAX_CONTENT_CHARS
        ):
            raise AiError("invalid_response", reason=Reason.FINAL_CONTENT_INVALID)
        return parse_tutor_answer(text)


def create_tutor_provider(
    settings: Settings, transport: httpx.AsyncClient
) -> TutorProvider:
    """Operator selection only. No automatic fallback, shared state or new endpoint."""
    if not settings.ai_configured:
        raise AiError("not_configured")
    match settings.forge_ai_provider:
        case "groq":
            return GroqTutor(settings, transport)
        case "openai":
            return OpenAITutor(settings, transport)
    raise AiError("not_configured")
