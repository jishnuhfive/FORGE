"""Requirement contract and result vocabulary for deterministic step checks."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ..integrations.onshape.inspector import CadInspector

# PASS: evidence proves the requirement. FAIL: evidence proves it is not met.
# WARNING: authored, supported condition worth attention (never generic doubt).
# UNVERIFIED: evidence is insufficient or untrusted. Never a synonym for FAIL.
Status = Literal["PASS", "FAIL", "WARNING", "UNVERIFIED"]
StepOutcome = Literal["verified", "not_met", "unverified"]
Reason = Literal[
    "met",
    "met_by_alternative",
    "missing",
    "suppressed",
    "evidence_unavailable",
    "evidence_incomplete",
    "evidence_stale",
    "not_observable",
    "ambiguous_signal",
    "constraint_not_met",
]


class Outcome(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    status: Status
    reason: Reason
    # Fixed server-authored wording keyed by the lesson spec; no provider text.
    finding: str = Field(max_length=300)


@dataclass(frozen=True)
class Requirement:
    id: str
    description: str
    # Evidence fields consulted, for the student-facing method disclosure.
    evidence: tuple[str, ...]
    # Only a blocking requirement's PASS lets a step be called Forge-verified.
    blocking: bool
    evaluate: Callable[[CadInspector], Outcome]


class RequirementResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    requirement_id: str
    description: str
    blocking: bool
    evidence: tuple[str, ...]
    outcome: Outcome


class StepCheckResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    step_id: str
    outcome: StepOutcome
    results: tuple[RequirementResult, ...]


def evaluate(
    step_id: str, requirements: tuple[Requirement, ...], inspector: CadInspector
) -> StepCheckResult:
    results = tuple(
        RequirementResult(
            requirement_id=r.id,
            description=r.description,
            blocking=r.blocking,
            evidence=r.evidence,
            outcome=r.evaluate(inspector),
        )
        for r in requirements
    )
    blocking = [r.outcome.status for r in results if r.blocking]
    # A step is verified only when every blocking requirement is PASS (a WARNING
    # on a blocking requirement is not a PASS). FAIL beats UNVERIFIED.
    if blocking and all(s == "PASS" for s in blocking):
        outcome: StepOutcome = "verified"
    elif "FAIL" in blocking:
        outcome = "not_met"
    else:
        outcome = "unverified"
    return StepCheckResult(step_id=step_id, outcome=outcome, results=results)
