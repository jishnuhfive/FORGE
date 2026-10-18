"""Closed presentation-only events. No private plan or provider data."""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from .domain import Closed
from .plans import PlanResult

MAX_EVENTS = 21  # Three stages + one outcome for each of five operations + result.
MAX_EVENT_BYTES = 512  # Includes the terminating newline.
MAX_STREAM_BYTES = 8192

OperationNumber = Annotated[int, Field(ge=1, le=5)]
ProgressStage = Literal["checking", "executing", "verifying"]
OperationOutcome = Literal[
    "verified_success",
    "rejected_stale",
    "write_failed",
    "execution_uncertain",
    "skipped",
]


class OperationEvent(Closed):
    operation: OperationNumber
    total: OperationNumber

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.operation > self.total:
            raise ValueError("invalid operation index")
        return self


class ProgressEvent(OperationEvent):
    type: Literal["progress"] = "progress"
    stage: ProgressStage


class OperationResultEvent(OperationEvent):
    type: Literal["operation_result"] = "operation_result"
    state: OperationOutcome


class ResultEvent(PlanResult):
    type: Literal["result"] = "result"


class ErrorEvent(Closed):
    # Only for a transport/persistence failure without a conclusive final result.
    # Never implies a write failed before dispatch. Retrieve owner-scoped status.
    type: Literal["error"] = "error"
    code: Literal["execution_uncertain"] = "execution_uncertain"


Progress = ProgressEvent | OperationResultEvent
StreamEvent = Progress | ResultEvent | ErrorEvent
