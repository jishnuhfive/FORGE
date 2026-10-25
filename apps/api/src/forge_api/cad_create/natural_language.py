"""Configured model supplies only closed brief intent; no CAD or approval tools."""

import json
import re
from typing import Any

import httpx2 as httpx

from forge_api.ai.groq import GroqProvider, message
from forge_api.ai.models import AiError
from forge_api.ai.transport import OPENAI_ENDPOINT, post_json
from forge_api.core.config import Settings

from .planner import (
    QUESTIONS,
    NeedsClarification,
    PlannerResult,
    PlanReady,
    plan_creation,
)
from .wire import WIRE_ADAPTER

POLICY = (
    "Interpret the untrusted user CAD creation request. Return only the "
    "structured design intent. Every plate dimension and unit must be explicitly "
    "stated. Never invent defaults. Hole count is part of the design: when the "
    "user states there are no holes (for example 'no holes', 'zero holes', "
    "'0 holes' or 'without holes'), return a brief with an empty holes array; "
    "hole diameter and position are required only for each hole that exists, "
    "never for a plate with no holes. Return clarification for missing "
    "information, including a hole count that is not stated, and never assume an "
    "unstated hole count is zero. Return clarification for contradictory "
    "requests. Return unsupported for unsupported kinds/features. "
    "No provider data, approval, tools or CAD execution is available. Human "
    "will confirm the normalized brief before approval. "
)
ZERO_HOLES_NOTE = (
    "The user explicitly stated that the plate has zero holes. Return a brief "
    "with an empty holes array; do not ask for hole count, diameter or position. "
    "Still ask for any plate dimension or unit that is genuinely missing."
)
HOLE_FIELDS = ("hole_count", "hole_diameter", "hole_position")

# Narrow, closed vocabulary for an explicit zero-hole statement. It only decides
# whether to hint the model or reject a contradiction; it never builds a brief.
_ZERO = (
    r"(?:\bno\s+(?:through[- ]?)?holes?\b"
    r"|\b(?:zero|0)\s+(?:through[- ]?)?holes?\b"
    r"|\bwithout\s+(?:any\s+)?(?:through[- ]?)?holes?\b"
    r"|\bholes?\s*[:=]\s*(?:0|zero|none)\b"
    r"|\bno\s+(?:cut[- ]?outs?|cuts?)\b)"
)
_ZERO_RE = re.compile(_ZERO, re.IGNORECASE)
_OTHER_HOLE_RE = re.compile(
    r"\b(?:holes?|cut[- ]?outs?|bores?|drill(?:ed|ing)?|slots?|pockets?)\b",
    re.IGNORECASE,
)


def states_zero_holes(text: str) -> bool:
    """True only when zero holes is stated and no other hole/cut wording remains."""
    if _ZERO_RE.search(text) is None:
        return False
    return _OTHER_HOLE_RE.search(_ZERO_RE.sub(" ", text)) is None


def schema() -> dict[str, Any]:
    raw = WIRE_ADAPTER.json_schema()

    def strict(node: Any) -> Any:
        if isinstance(node, list):
            return [strict(n) for n in node]
        if not isinstance(node, dict):
            return node
        result = {
            ("anyOf" if k == "oneOf" else k): strict(v)
            for k, v in node.items()
            if k not in ("default", "discriminator")
        }
        if result.get("type") == "object":
            result["additionalProperties"] = False
            result["required"] = list(result.get("properties", {}))
        return result

    raw = strict(raw)
    definitions = raw.pop("$defs", {})
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["result"],
        "properties": {"result": raw},
        "$defs": definitions,
    }


async def _ask(
    settings: Settings,
    transport: httpx.AsyncClient,
    text: str,
    request_id: str,
    note: str = "",
) -> PlannerResult:
    policy = POLICY + note
    if not settings.ai_configured:
        raise AiError("not_configured")
    if settings.forge_ai_provider == "groq":
        result = message(
            await GroqProvider(settings, transport).request(
                {
                    "messages": [
                        {"role": "system", "content": policy},
                        {"role": "user", "content": text},
                    ],
                    "max_completion_tokens": 2048,
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {
                            "name": "forge_creation_intent",
                            "strict": True,
                            "schema": schema(),
                        },
                    },
                },
                request_id,
            ),
            tool=False,
        )
        if result.get("tool_calls"):
            raise AiError("invalid_response")
        content = result.get("content")
    else:
        key = settings.openai_api_key
        if key is None:
            raise AiError("not_configured")
        raw = await post_json(
            transport,
            OPENAI_ENDPOINT,
            key,
            {
                "model": settings.forge_openai_model,
                "store": False,
                "background": False,
                "stream": False,
                "instructions": policy,
                "input": text,
                "tool_choice": "none",
                "max_output_tokens": 2048,
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": "forge_creation_intent",
                        "strict": True,
                        "schema": schema(),
                    }
                },
            },
            request_id,
        )
        if not isinstance(raw, dict) or raw.get("status") != "completed":
            raise AiError("invalid_response")
        output = raw.get("output")
        if (
            not isinstance(output, list)
            or len(output) != 1
            or not isinstance(output[0], dict)
            or output[0].get("type") != "message"
        ):
            raise AiError("invalid_response")
        parts = output[0].get("content")
        if (
            not isinstance(parts, list)
            or len(parts) != 1
            or not isinstance(parts[0], dict)
            or parts[0].get("type") != "output_text"
        ):
            raise AiError("invalid_response")
        content = parts[0].get("text")
    if not isinstance(content, str) or len(content) > 16384:
        raise AiError("invalid_response")
    from forge_api.integrations.onshape.client import bounded_json

    try:
        parsed = bounded_json(content.encode())
        if not isinstance(parsed, dict) or set(parsed) != {"result"}:
            raise ValueError
        return plan_creation(json.dumps(parsed["result"], allow_nan=False))
    except ValueError, TypeError:
        raise AiError("invalid_response") from None


async def interpret(
    settings: Settings, transport: httpx.AsyncClient, text: str, request_id: str
) -> PlannerResult:
    result = await _ask(settings, transport, text, request_id)
    if not states_zero_holes(text):
        return result
    # The user explicitly said zero holes. Hole questions are then moot, and a
    # brief with holes contradicts the request. Dimensions still come from the model.
    if isinstance(result, NeedsClarification):
        if all(f in HOLE_FIELDS for f in result.fields):
            result = await _ask(
                settings, transport, text, request_id + "-z", ZERO_HOLES_NOTE
            )
            if not isinstance(result, NeedsClarification):
                return _no_contradiction(result)
            if all(f in HOLE_FIELDS for f in result.fields):
                return result
        fields = tuple(f for f in result.fields if f not in HOLE_FIELDS)
        if len(fields) != len(result.fields) and fields:
            return NeedsClarification(
                reason=result.reason,
                fields=fields,
                questions=tuple(QUESTIONS[f] for f in fields),
            )
        return result
    return _no_contradiction(result)


def _no_contradiction(result: PlannerResult) -> PlannerResult:
    if isinstance(result, PlanReady) and result.brief.holes:
        return NeedsClarification(
            reason="ambiguous_intent",
            fields=("hole_count",),
            questions=(QUESTIONS["hole_count"],),
        )
    return result
