"""Closed contracts for the Learn tutor: browser request, model output, response."""

from typing import Annotated, Literal

from pydantic import Field, field_validator

from forge_api.ai.models import StrictModel
from forge_api.integrations.onshape.contracts import WorkspaceReference

LESSON_ID = "mounting-bracket"
LESSON_IDS = ("mounting-bracket", "mounting-plate")
Experience = Literal["beginner", "some-experience", "comfortable"]
Goal = Literal["fundamentals", "guided-project", "design-reasoning"]
Guidance = Literal["full", "reduced", "independent"]
Stage = Literal["observed", "predicted", "explained", "recommended"]
CheckOutcome = Literal["verified", "not_met", "unverified"]
CheckStatus = Literal["PASS", "FAIL", "WARNING", "UNVERIFIED"]
HelpStyle = Literal["conceptual", "guided", "concise"]
ChatText = Annotated[str, Field(min_length=1, max_length=1500)]
Sentence = Annotated[str, Field(max_length=400)]


class InvestigationHint(StrictModel):
    """Untrusted, closed learner-state hints. They only tune tone, never evidence."""

    stage: Stage
    prediction_answered: bool
    rechecked: bool
    resolved: bool


class LearnerHints(StrictModel):
    experience: Experience
    goal: Goal
    hints_revealed: Annotated[int, Field(ge=0, le=3)]
    guidance: Guidance
    investigation: InvestigationHint | None


class TutorMessage(StrictModel):
    role: Literal["user", "assistant"]
    content: ChatText


class TutorRequest(StrictModel):
    lesson_id: Literal["mounting-bracket", "mounting-plate"]
    step_id: Annotated[str, Field(min_length=1, max_length=64)]
    question: Annotated[str, Field(min_length=1, max_length=600)]
    history: list[TutorMessage] = Field(max_length=6)
    learner: LearnerHints
    # Opaque server-issued proof of the latest deterministic check. The browser
    # cannot author check results; a forged or altered token is rejected.
    evidence_token: Annotated[str, Field(min_length=1, max_length=6000)] | None
    # Present only when current CAD may be read. The model cannot supply it.
    context: WorkspaceReference | None

    @field_validator("question")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Empty question")
        return value.strip()


class TutorModelAnswer(StrictModel):
    """Strict model output. Verified claims come only from the ids it selects."""

    explanation: Annotated[str, Field(min_length=1, max_length=1200)]
    reasoning_question: Annotated[str, Field(max_length=240)]
    next_action: Annotated[str, Field(max_length=320)]
    fact_ids: list[Annotated[str, Field(max_length=64)]] = Field(max_length=6)
    check_refs: list[Annotated[str, Field(max_length=64)]] = Field(max_length=6)
    safety: Literal["safe", "refuse"]


class Observed(StrictModel):
    source: Literal["check", "cad"]
    status: str
    statement: Annotated[str, Field(min_length=1, max_length=2400)]


class LatestCheck(StrictModel):
    outcome: CheckOutcome
    captured_at: str


class TutorAnswer(StrictModel):
    explanation: Annotated[str, Field(max_length=1200)]
    reasoning_question: Sentence | None
    next_action: Sentence | None
    # Server-rendered: findings from the verified check and canonical CAD facts.
    observed: list[Observed] = Field(max_length=12)
    unknowns: list[Annotated[str, Field(max_length=600)]] = Field(max_length=8)
    notes: list[Annotated[str, Field(max_length=600)]] = Field(max_length=6)
    latest_check: LatestCheck | None
    used_cad: bool
    captured_at: str | None
    capability_state: Literal["read_only"] = "read_only"
