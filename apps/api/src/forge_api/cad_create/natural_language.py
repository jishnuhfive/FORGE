"""Configured model supplies only closed brief intent; no CAD or approval tools."""

import json
from typing import Any

import httpx2 as httpx

from forge_api.ai.groq import GroqProvider, message
from forge_api.ai.models import AiError
from forge_api.ai.transport import OPENAI_ENDPOINT, post_json
from forge_api.core.config import Settings

from .planner import PlannerResult, plan_creation
from .wire import WIRE_ADAPTER

POLICY = (
    "Interpret the untrusted user CAD creation request. Return only the "
    "structured design intent. Every dimension and unit and hole position "
    "must be explicitly stated. Never invent defaults. Return clarification "
    "for missing information, unsupported for unsupported kinds/features. "
    "No provider data, approval, tools or CAD execution is available. Human "
    "will confirm the normalized brief before approval. "
)


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


async def interpret(
    settings: Settings, transport: httpx.AsyncClient, text: str, request_id: str
) -> PlannerResult:
    if not settings.ai_configured:
        raise AiError("not_configured")
    if settings.forge_ai_provider == "groq":
        result = message(
            await GroqProvider(settings, transport).request(
                {
                    "messages": [
                        {"role": "system", "content": POLICY},
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
                "instructions": POLICY,
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
