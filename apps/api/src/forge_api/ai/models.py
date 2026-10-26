"""Strict internal and browser contracts. Model-selected facts are resolved by Forge."""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from forge_api.integrations.onshape.contracts import WorkspaceReference

from .diagnostics import Reason

Text = Annotated[str, Field(min_length=1, max_length=4000)]
ShortText = Annotated[str, Field(min_length=1, max_length=600)]
EvidenceStatus = Literal["verified", "unverified", "unknown", "assumption"]
Selection = Literal["none", "FACE", "EDGE", "unknown"]
SuggestionId = Literal[
    "check_constraints",
    "check_material",
    "confirm_units",
    "review_dimensions",
    "define_requirements",
]
AssumptionId = Literal["static_load_case", "room_temperature_case"]
QuestionId = Literal["loads_and_clearances", "intended_material", "proposed_dimensions"]
ErrorCode = Literal[
    "not_configured",
    "connection_unavailable",
    "authentication_failed",
    "rate_limited",
    "quota_unavailable",
    "capacity_unavailable",
    "timeout",
    "invalid_response",
    "refused",
    "incomplete",
    "context_unavailable",
    "read_permission_required",
    "evidence_unavailable",
    "session_expired",
    "request_in_progress",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)


class HistoryMessage(StrictModel):
    role: Literal["user", "assistant"]
    content: Text


class AiRequest(StrictModel):
    prompt: Text
    context: WorkspaceReference
    selection: Selection
    history: list[HistoryMessage] = Field(max_length=6)

    @field_validator("prompt")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Empty prompt")
        return value.strip()


class ToolArguments(StrictModel):
    pass


def _require_explanation(schema: dict[str, Any]) -> None:
    # Strict structured output needs every property required; the Python default
    # keeps older callers and fixtures valid.
    schema["required"] = [*schema.get("required", []), "explanation"]


class ModelAnswer(StrictModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        hide_input_in_errors=True,
        json_schema_extra=_require_explanation,
    )
    # The model selects canonical facts; it cannot author a verified CAD claim.
    fact_ids: list[Annotated[str, Field(max_length=64)]] = Field(max_length=12)
    suggestion_ids: list[SuggestionId] = Field(max_length=3)
    assumption_ids: list[AssumptionId] = Field(max_length=3)
    question_ids: list[QuestionId] = Field(max_length=3)
    safety: Literal["safe", "refuse"]
    # General engineering explanation of the selected facts; never a CAD fact.
    explanation: Annotated[str, Field(max_length=1800)] = ""


class Fact(StrictModel):
    id: Annotated[str, Field(max_length=64)]
    statement: Annotated[str, Field(min_length=1, max_length=2400)]
    status: EvidenceStatus

    @field_validator("statement")
    @classmethod
    def nonblank_statement(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Empty evidence statement")
        return value.strip()


Line = Annotated[str, Field(min_length=1, max_length=400)]
Block = Annotated[str, Field(min_length=1, max_length=900)]


class GuideStep(StrictModel):
    title: Line
    action: Block
    # Exact Onshape controls: tool names, the plane/face/region to pick, options.
    controls: list[Line] = Field(max_length=6)
    # Values the user enters. Only dimensions the user gave or labelled assumptions.
    parameters: list[Line] = Field(max_length=6)
    check: Block
    why: Block


class ModelingGuide(StrictModel):
    kind: Literal["guide", "clarification", "explanation"]
    safety: Literal["safe", "refuse"]
    title: Line
    summary: Block
    key_dimensions: list[Line] = Field(max_length=8)
    assumptions: list[Line] = Field(max_length=5)
    questions: list[Line] = Field(max_length=4)
    steps: list[GuideStep] = Field(max_length=12)
    explanation: Annotated[str, Field(max_length=2500)]
    mistakes: list[Line] = Field(max_length=5)
    checklist: list[Line] = Field(max_length=8)
    follow_ups: list[Line] = Field(max_length=3)

    @field_validator("title", "summary", "explanation", mode="after")
    @classmethod
    def printable(cls, value: str) -> str:
        return value.strip()


class AiAnswer(StrictModel):
    answer: Annotated[str, Field(max_length=30000)]
    evidence: list[Fact] = Field(max_length=12)
    uncertainties: list[ShortText] = Field(max_length=6)
    discussion: Annotated[str, Field(max_length=1600)]
    assumptions: list[ShortText] = Field(max_length=3)
    follow_up_questions: list[ShortText] = Field(max_length=3)
    capability_state: Literal["read_only"] = "read_only"
    captured_at: str | None
    # Model-written and never CAD evidence; the browser labels both as such.
    explanation: Annotated[str, Field(max_length=2500)] = ""
    guide: ModelingGuide | None = None


class AiError(Exception):
    def __init__(
        self,
        code: ErrorCode,
        retry_after: int | None = None,
        *,
        reason: Reason | None = None,
        field: str | None = None,
        http_status: int | None = None,
        provider_error_code: str | None = None,
        provider_error_type: str | None = None,
        provider_error_param: str | None = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.retry_after = retry_after
        self.reason = reason
        self.field = field
        self.http_status = http_status
        self.provider_error_code = provider_error_code
        self.provider_error_type = provider_error_type
        self.provider_error_param = provider_error_param
