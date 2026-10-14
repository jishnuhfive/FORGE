"""Exact v17 parameter adapters. Never evaluate expressions or expand queries."""

from typing import Literal

from pydantic import Field, ValidationError

from .models import ParameterValue, ProviderModel, Text


class BooleanParameter(ProviderModel):
    value: bool | None = None


class StringParameter(ProviderModel):
    value: Text | None = None


class QuantityParameter(ProviderModel):
    expression: Text | None = None


class QueryEntry(ProviderModel):
    # Entry presence is evidence of a query, not its result or entity ownership.
    pass


class QueryParameter(ProviderModel):
    queries: list[QueryEntry] | None = Field(default=None, max_length=2000)


# No class-name prefix matching: subclasses require their own contract review.
ADAPTERS: dict[str, tuple[str, type[ProviderModel]]] = {
    "BTMParameterBoolean-144": ("boolean", BooleanParameter),
    "BTMParameterString-149": ("string", StringParameter),
    "BTMParameterEnum-145": ("enum", StringParameter),
    "BTMParameterQuantity-147": ("expression", QuantityParameter),
    "BTMParameterQueryList-148": ("query_count", QueryParameter),
}


def display_text(value: str | None) -> str | None:
    """Omit whole strings outside display bounds; never alter numeric meaning."""
    if value is None:
        return None
    try:
        encoded_length = len(value.encode("utf-8"))
    except UnicodeError:
        return None
    if encoded_length > 256 or any(
        ord(c) < 32
        or ord(c) == 127
        or 0x202A <= ord(c) <= 0x202E
        or 0x2066 <= ord(c) <= 0x2069
        for c in value
    ):
        return None
    return value


def parameter_value(raw: dict[str, object]) -> ParameterValue:
    tag = raw.get("btType")
    adapter = ADAPTERS.get(tag) if isinstance(tag, str) else None
    if adapter is None:
        return ParameterValue(kind="unsupported", state="unsupported")
    kind, model = adapter
    result = ParameterValue.model_validate({"kind": kind, "state": "unavailable"})
    try:
        parsed = model.model_validate(raw)
    except ValidationError:
        return result
    if isinstance(parsed, BooleanParameter) and parsed.value is not None:
        return result.model_copy(update={"state": "available", "boolean": parsed.value})
    if isinstance(parsed, QueryParameter) and parsed.queries is not None:
        return result.model_copy(
            update={"state": "available", "count": len(parsed.queries)}
        )
    value = (
        parsed.expression
        if isinstance(parsed, QuantityParameter)
        else (parsed.value if isinstance(parsed, StringParameter) else None)
    )
    if value is None:
        return result
    text = display_text(value)
    state: Literal["available", "omitted"] = (
        "available" if text is not None else "omitted"
    )
    return result.model_copy(update={"state": state, "text": text})
