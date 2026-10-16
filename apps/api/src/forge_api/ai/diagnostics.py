"""Development-only fixed metadata. Never format exceptions or provider content."""

import json
import logging
import re
from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import ValidationError

if TYPE_CHECKING:
    from .models import AiError


class Reason(StrEnum):
    PROVIDER_REQUEST_REJECTED = "provider_request_rejected"
    PROVIDER_TOOL_GENERATION_FAILED = "provider_tool_generation_failed"
    PROVIDER_ENVELOPE_INVALID = "provider_envelope_invalid"
    PROVIDER_MALFORMED_JSON = "provider_malformed_json"
    STRUCTURED_OUTPUT_VALIDATION_FAILED = "structured_output_validation_failed"
    MISSING_REQUIRED_FIELD = "missing_required_field"
    UNSUPPORTED_ENUM_VALUE = "unsupported_enum_value"
    INCOMPLETE_RESPONSE = "incomplete_response"
    PROVIDER_REFUSAL = "provider_refusal"
    TOOL_CALL_SHAPE_INVALID = "tool_call_shape_invalid"
    TOOL_ARGUMENTS_INVALID = "tool_arguments_invalid"
    TOOL_LOOP_STATE_ERROR = "tool_loop_state_error"
    FINAL_CONTENT_INVALID = "final_content_invalid"
    UNKNOWN_FACT_ID = "unknown_fact_id"
    DUPLICATE_CANONICAL_ID = "duplicate_canonical_id"
    EMPTY_CANONICAL_ANSWER = "empty_canonical_answer"
    GROUNDING_REWRITE_FAILED = "grounding_rewrite_failed"
    CANONICAL_RESPONSE_VALIDATION_FAILED = "canonical_response_validation_failed"
    PROVIDER_TIMEOUT = "provider_timeout"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    EVIDENCE_UNAVAILABLE = "evidence_unavailable"


class Stage(StrEnum):
    INSPECTION_REQUEST = "inspection_request"
    CAD_INSPECTION = "cad_inspection"
    FINAL_OUTPUT = "final_output"
    GROUNDING = "grounding"


FIELDS = frozenset(
    {
        "fact_ids",
        "suggestion_ids",
        "assumption_ids",
        "question_ids",
        "safety",
        "answer",
        "evidence",
        "uncertainties",
        "discussion",
        "assumptions",
        "follow_up_questions",
        "capability_state",
        "captured_at",
    }
)

# Exact literals only. Even an error's code/type/param may contain private text;
# never use a general character/length regex to declare them safe.
ERROR_CODES = frozenset(
    {
        "tool_use_failed",
        "json_validate_failed",
        "invalid_request_error",
        "context_length_exceeded",
        "invalid_value",
        "unsupported_parameter",
        "model_not_found",
        "invalid_api_key",
        "rate_limit_exceeded",
    }
)
ERROR_TYPES = frozenset(
    {
        "invalid_request_error",
        "invalid_request",
        "validation_error",
        "authentication_error",
        "rate_limit_error",
        "server_error",
    }
)
ERROR_PARAMS = frozenset(
    {
        "model",
        "messages",
        "tools",
        "tool_choice",
        "parallel_tool_calls",
        "reasoning_effort",
        "include_reasoning",
        "reasoning_format",
        "max_completion_tokens",
        "max_tokens",
        "temperature",
        "response_format",
        "stream",
        "store",
        "n",
    }
)


def safe_literal(value: object, allowed: frozenset[str]) -> str | None:
    return value if isinstance(value, str) and value in allowed else None


def provider_details(value: object) -> tuple[str | None, str | None, str | None]:
    error = value.get("error") if isinstance(value, dict) else None
    if not isinstance(error, dict):
        return None, None, None
    return (
        safe_literal(error.get("code"), ERROR_CODES),
        safe_literal(error.get("type"), ERROR_TYPES),
        safe_literal(error.get("param"), ERROR_PARAMS),
    )


def validation_details(error: ValidationError) -> tuple[Reason, str | None]:
    first = error.errors(include_input=False, include_context=False, include_url=False)[
        0
    ]
    loc = first["loc"]
    # Unknown field names can themselves contain private model text. Never log them.
    field = loc[0] if loc and loc[0] in FIELDS else None
    if field and len(loc) > 1 and isinstance(loc[1], int):
        field += "[]"
    reason = {
        "missing": Reason.MISSING_REQUIRED_FIELD,
        "literal_error": Reason.UNSUPPORTED_ENUM_VALUE,
    }.get(first["type"], Reason.STRUCTURED_OUTPUT_VALIDATION_FAILED)
    return reason, field


def emit_diagnostic(
    error: AiError, *, environment: str, provider: str, stage: Stage, request_id: str
) -> None:
    if environment != "development":
        return
    reason = error.reason or {
        "incomplete": Reason.INCOMPLETE_RESPONSE,
        "refused": Reason.PROVIDER_REFUSAL,
        "timeout": Reason.PROVIDER_TIMEOUT,
        "evidence_unavailable": Reason.EVIDENCE_UNAVAILABLE,
        "invalid_response": Reason.PROVIDER_ENVELOPE_INVALID,
    }.get(error.code, Reason.PROVIDER_UNAVAILABLE)
    # Defense in depth against an accidental future caller passing arbitrary strings.
    if not isinstance(reason, Reason):
        reason = Reason.PROVIDER_ENVELOPE_INVALID
    field = error.field
    if field not in FIELDS and field not in {f + "[]" for f in FIELDS}:
        field = None
    payload = {
        "reason": reason.value,
        "provider": provider if provider in ("groq", "openai") else "unknown",
        "stage": stage.value,
        "request_id": request_id if re.fullmatch(r"[a-f0-9]{32}", request_id) else None,
        "field": field,
        "http_status": error.http_status
        if isinstance(error.http_status, int) and 100 <= error.http_status <= 599
        else None,
        "provider_error_code": safe_literal(error.provider_error_code, ERROR_CODES),
        "provider_error_type": safe_literal(error.provider_error_type, ERROR_TYPES),
        "provider_error_param": safe_literal(error.provider_error_param, ERROR_PARAMS),
    }
    logging.getLogger("forge.ai.validation").warning(
        "ai_validation %s", json.dumps(payload, separators=(",", ":"))
    )
