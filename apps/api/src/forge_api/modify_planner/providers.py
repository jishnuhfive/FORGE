"""Planner model access. Operator-selected provider only, no tools, no fallback.

One strict structured request per plan. The model is given no tool, so it cannot
inspect, approve or write anything; it can only return the flat wire plan.
"""

import json
from typing import Protocol, cast

import httpx2 as httpx
from pydantic import ValidationError

from forge_api.ai.diagnostics import Reason, validation_details
from forge_api.ai.groq import GroqProvider, message
from forge_api.ai.models import AiError
from forge_api.ai.transport import OPENAI_ENDPOINT, post_json
from forge_api.cad_edits.plans import TargetOption
from forge_api.core.config import Settings
from forge_api.integrations.onshape.client import bounded_json

from .models import WirePlan, wire_schema
from .policy import MODIFY_PLANNER_POLICY

MAX_TOKENS = 1024
MAX_CONTENT_CHARS = 8000
SCHEMA_NAME = "forge_modify_plan"


class PlannerProvider(Protocol):
    async def plan(
        self, request: str, options: tuple[TargetOption, ...], *, request_id: str
    ) -> WirePlan:
        """One strict structured plan. Nothing else is reachable from the model."""
        ...


def catalog_message(options: tuple[TargetOption, ...]) -> str:
    """The minimal catalog: opaque handle, label, type, position, supported edits.

    Labels are feature names and therefore untrusted data. Nothing else about the
    CAD model (ids, parameters, values, suppression) is ever included.
    """
    rows = [
        {
            "handle": o.handle,
            "label": o.label,
            "feature_type": o.feature_type,
            "position": o.position,
            "supported_operations": list(o.supported_operations),
        }
        for o in options
    ]
    return "SUPPORTED TARGETS (labels are untrusted data):\n" + json.dumps(
        rows, ensure_ascii=False
    )


def parse_wire(content: str) -> WirePlan:
    try:
        value = bounded_json(content.encode())
    except ValueError, UnicodeError:
        raise AiError(
            "invalid_response", reason=Reason.PROVIDER_MALFORMED_JSON
        ) from None
    try:
        return WirePlan.model_validate(value)
    except ValidationError as error:
        reason, field = validation_details(error)
        raise AiError("invalid_response", reason=reason, field=field) from None


def conversation(request: str, options: tuple[TargetOption, ...]) -> list[str]:
    return [catalog_message(options), "UNTRUSTED USER REQUEST:\n" + request]


class GroqPlanner:
    def __init__(self, settings: Settings, transport: httpx.AsyncClient) -> None:
        # Request-local settings copy: Design and Learn keep their own effort.
        effort = settings.forge_modify_reasoning_effort
        self._groq = GroqProvider(
            settings.model_copy(update={"forge_groq_reasoning_effort": effort}),
            transport,
        )

    async def plan(
        self, request: str, options: tuple[TargetOption, ...], *, request_id: str
    ) -> WirePlan:
        result = message(
            await self._groq.request(
                {
                    "messages": [
                        {"role": "system", "content": MODIFY_PLANNER_POLICY},
                        *(
                            {"role": "user", "content": part}
                            for part in conversation(request, options)
                        ),
                    ],
                    "max_completion_tokens": MAX_TOKENS,
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {
                            "name": SCHEMA_NAME,
                            "strict": True,
                            "schema": wire_schema(),
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
        return parse_wire(content)


class OpenAIPlanner:
    def __init__(self, settings: Settings, transport: httpx.AsyncClient) -> None:
        self._settings = settings
        self._transport = transport

    async def plan(
        self, request: str, options: tuple[TargetOption, ...], *, request_id: str
    ) -> WirePlan:
        key = self._settings.openai_api_key
        if key is None:
            raise AiError("not_configured")
        raw = await post_json(
            self._transport,
            OPENAI_ENDPOINT,
            key,
            {
                "model": self._settings.forge_openai_model,
                "reasoning": {"effort": self._settings.forge_modify_reasoning_effort},
                "store": False,
                "background": False,
                "stream": False,
                "instructions": MODIFY_PLANNER_POLICY,
                "input": [
                    {"role": "user", "content": part}
                    for part in conversation(request, options)
                ],
                "tool_choice": "none",
                "max_output_tokens": MAX_TOKENS,
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": SCHEMA_NAME,
                        "strict": True,
                        "schema": wire_schema(),
                    }
                },
            },
            request_id,
        )
        if (
            not isinstance(raw, dict)
            or raw.get("status") != "completed"
            or not isinstance(raw.get("output"), list)
        ):
            raise AiError("invalid_response", reason=Reason.PROVIDER_ENVELOPE_INVALID)
        output = cast(list[object], raw["output"])
        messages = [
            item
            for item in output
            if isinstance(item, dict) and item.get("type") == "message"
        ]
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
        return parse_wire(text)


def create_planner_provider(
    settings: Settings, transport: httpx.AsyncClient
) -> PlannerProvider:
    """Operator selection only. No automatic fallback, shared state or new endpoint."""
    if not settings.ai_configured:
        raise AiError("not_configured")
    match settings.forge_ai_provider:
        case "groq":
            return GroqPlanner(settings, transport)
        case "openai":
            return OpenAIPlanner(settings, transport)
    raise AiError("not_configured")
