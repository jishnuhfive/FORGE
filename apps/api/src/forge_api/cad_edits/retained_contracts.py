"""Private operator contracts and transaction-local provenance; no provider I/O.

Independent evidence is a human-reviewed trust input, not a browser credential.
No Python model can establish that an operator really preserved an external receipt.
The trusted operator must do that review before constructing these contracts.
"""

from dataclasses import dataclass, field
from time import monotonic
from typing import Annotated, Literal

from pydantic import Field
from sqlalchemy.orm import Session, SessionTransaction

from forge_api.integrations.onshape.contracts import CadId, WorkspaceReference

from .domain import Baseline, Binding, Closed, Digest, Handle, fingerprint
from .plans import StoredPlan

CAPTURE_SECONDS = 30
HANDOFF_SECONDS = 5
TRANSACTION_SECONDS = 40


class RetainedRecoveryDenied(Exception):
    """Fixed reasons only. Never include provider errors or private identifiers."""


class PreservedHandle(Closed):
    kind: Literal["preserved_record_handle"]
    value: Handle = Field(repr=False)


class PreservedApproval(Closed):
    kind: Literal["preserved_approval_digest"]
    value: Digest = Field(repr=False)


class IndependentOperationEvidence(Closed):
    """A: reviewed, previously preserved evidence, independent of current DB rows."""

    source: Literal["previously_preserved_operation_receipt"]
    receipt_digest: Digest = Field(repr=False)
    user: str = Field(min_length=1, max_length=36, repr=False)
    context: WorkspaceReference = Field(repr=False)
    operation: Literal["SET_SUPPRESSED", "SET_UNSUPPRESSED"]
    desired_suppressed: bool
    anchor: Annotated[
        PreservedHandle | PreservedApproval, Field(discriminator="kind", repr=False)
    ]


class OperatorReview(Closed):
    """C: explicit human review before entering the bounded transaction."""

    operator_authorized: bool
    independent_receipt_reviewed: bool
    writers_drained: bool
    upstream_settled: bool
    stack: str = Field(min_length=1, max_length=255, repr=False)
    company_id: CadId | None = Field(repr=False)
    current_generation: str = Field(min_length=1, max_length=36, repr=False)


class HistoricalPlanReference(Closed):
    """B: integrity/TOCTOU pins; these are not independent authority."""

    record_id: Handle = Field(repr=False)
    binding: Binding = Field(repr=False)
    plan_digest: Digest = Field(repr=False)
    payload_fingerprint: Digest = Field(repr=False)
    created_at: int = Field(ge=0)
    expires_at: int = Field(ge=0)


class RetainedRecoveryReference(Closed):
    independent: IndependentOperationEvidence = Field(repr=False)
    historical: HistoricalPlanReference = Field(repr=False)
    review: OperatorReview = Field(repr=False)


def reference_fingerprint(reference: RetainedRecoveryReference) -> str:
    return fingerprint(reference.model_dump(mode="json"))


def check_independent(
    independent: IndependentOperationEvidence, saved: StoredPlan
) -> None:
    plan = saved.plan
    anchor = independent.anchor
    if (
        independent.user != plan.binding.user
        or independent.context != plan.binding.context
        or len(plan.operations) != 1
        or independent.operation != plan.operations[0].operation.type
        or independent.desired_suppressed != (independent.operation == "SET_SUPPRESSED")
        or (isinstance(anchor, PreservedHandle) and anchor.value != plan.proposal_id)
        or (
            isinstance(anchor, PreservedApproval)
            and anchor.value != fingerprint(plan.model_dump(mode="json"))
        )
    ):
        raise RetainedRecoveryDenied("independent_reference_mismatch")


def build_retained_reference(
    independent: IndependentOperationEvidence,
    saved: StoredPlan,
    review: OperatorReview,
) -> RetainedRecoveryReference:
    """A → B → C. Never derive A from the supplied retained plan."""
    check_independent(independent, saved)
    plan = saved.plan
    return RetainedRecoveryReference(
        independent=independent,
        historical=HistoricalPlanReference(
            record_id=plan.proposal_id,
            binding=plan.binding,
            plan_digest=fingerprint(plan.model_dump(mode="json")),
            payload_fingerprint=fingerprint(saved.model_dump(mode="json")),
            created_at=plan.created_at,
            expires_at=plan.expires_at,
        ),
        review=review,
    )


class VerifiedRetainedRecoveryEvidence(Closed):
    """D: closed projection only; trusted only when registered by this run."""

    schema_version: Literal["retained-recovery-evidence-v1"] = (
        "retained-recovery-evidence-v1"
    )
    projection_version: Literal["terminal-fillet-6"] = "terminal-fillet-6"
    reference_fingerprint: Digest = Field(repr=False)
    record_id: Handle = Field(repr=False)
    plan_digest: Digest = Field(repr=False)
    payload_fingerprint: Digest = Field(repr=False)
    user: str = Field(min_length=1, max_length=36, repr=False)
    current_generation: str = Field(min_length=1, max_length=36, repr=False)
    context: WorkspaceReference = Field(repr=False)
    baseline: Baseline = Field(repr=False)
    head_before: CadId = Field(repr=False)
    head_after: CadId = Field(repr=False)
    started_monotonic: float = Field(ge=0, allow_inf_nan=False)
    finished_monotonic: float = Field(ge=0, allow_inf_nan=False)


class AdministrativeRecoveryResult(Closed):
    schema_version: Literal["retained-operator-result-v1"] = (
        "retained-operator-result-v1"
    )
    state: Literal["operator_recovered"] = "operator_recovered"
    original_execution_outcome: Literal["execution_uncertain"] = "execution_uncertain"
    disposition: Literal["independently_settled_current_state_matches"] = (
        "independently_settled_current_state_matches"
    )
    recovered_at: int = Field(ge=0)


def check_evidence(
    reference: RetainedRecoveryReference, evidence: VerifiedRetainedRecoveryEvidence
) -> None:
    historical = reference.historical
    if (
        evidence.reference_fingerprint != reference_fingerprint(reference)
        or evidence.record_id != historical.record_id
        or evidence.plan_digest != historical.plan_digest
        or evidence.payload_fingerprint != historical.payload_fingerprint
        or evidence.user != reference.independent.user
        or evidence.current_generation != reference.review.current_generation
        or evidence.context != reference.independent.context
        or evidence.baseline.context != evidence.context
        or evidence.head_before != evidence.head_after
        or evidence.baseline.microversion != evidence.head_before
        or not 0
        <= evidence.finished_monotonic - evidence.started_monotonic
        <= CAPTURE_SECONDS
    ):
        raise RetainedRecoveryDenied("evidence_reference_mismatch")


@dataclass(eq=False, repr=False)
class _RecoveryRun:
    """Private same-process capability, not serializable operator input.

    Only the coordinator registers the exact object after closing the reader.
    This is a trusted-process boundary, not a sandbox against hostile Python code.
    """

    db: Session
    transaction: SessionTransaction
    reference: RetainedRecoveryReference
    raw_payload: str
    saved: StoredPlan
    started: float
    evidence: VerifiedRetainedRecoveryEvidence | None = field(default=None)
    consumed: bool = False

    def _current(self, db: Session) -> None:
        if (
            db is not self.db
            or db.get_transaction() is not self.transaction
            or not self.transaction.is_active
            or db.in_nested_transaction()
            or monotonic() - self.started > TRANSACTION_SECONDS
        ):
            raise RetainedRecoveryDenied("recovery_run_invalid")

    def register(self, evidence: VerifiedRetainedRecoveryEvidence) -> None:
        self._current(self.db)
        if self.evidence is not None or self.consumed:
            raise RetainedRecoveryDenied("evidence_already_registered")
        check_evidence(self.reference, evidence)
        if evidence.started_monotonic < self.started:
            raise RetainedRecoveryDenied("evidence_predates_run")
        self.evidence = evidence

    def consume(self, db: Session, evidence: VerifiedRetainedRecoveryEvidence) -> None:
        used = self.consumed
        self.consumed = True  # Every release attempt consumes the handoff.
        self._current(db)
        if used or evidence is not self.evidence:
            raise RetainedRecoveryDenied("unregistered_or_used_evidence")
        check_evidence(self.reference, evidence)
        if not 0 <= monotonic() - evidence.finished_monotonic <= HANDOFF_SECONDS:
            raise RetainedRecoveryDenied("evidence_handoff_expired")
