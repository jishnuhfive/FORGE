"""Temporary, closed administrative contracts; never browser/approval authority.

Identity is deliberately trusted to the retained database. Review identifiers and
digests identify privately retained evidence; they are not signatures, and cannot
authenticate a dishonest privileged operator process.
"""

from dataclasses import dataclass, field
from time import monotonic
from typing import Annotated, Any, Literal, get_args, get_origin

from pydantic import Field, model_validator
from sqlalchemy.orm import Session, SessionTransaction

from forge_api.integrations.onshape.contracts import CadId, WorkspaceReference

from .domain import Baseline, Binding, Closed, Digest, Handle, fingerprint
from .plans import StoredPlan

CAPTURE_SECONDS = 30
HANDOFF_SECONDS = 5
TRANSACTION_SECONDS = 40
REVIEW_SECONDS = 900
PrivateText = Annotated[str, Field(min_length=1, max_length=200, repr=False)]
CaseId = Literal["oct20-terminal-fillet-reactivation"]


class LegacyRecoveryDenied(Exception):
    """Fixed codes only, without private identifiers or exception contents."""


class _LegacyClosed(Closed):
    @model_validator(mode="before")
    @classmethod
    def exact_literal_types(cls, value: Any) -> Any:
        # Pydantic's Literal[True]/Literal[int] otherwise accept equal 1/float.
        if isinstance(value, dict):
            for name, field_info in cls.model_fields.items():
                if name in value and get_origin(field_info.annotation) is Literal:
                    choices = get_args(field_info.annotation)
                    if (
                        choices
                        and type(choices[0]) in (bool, int)
                        and type(value[name]) is not type(choices[0])
                    ):
                        raise ValueError("legacy literal type mismatch")
        return value


class LegacyContext(WorkspaceReference):
    documentId: Literal["616f4c98dfb6deed0a0c40e6"]
    workspaceId: Literal["75018163dba1b8c05d651a5b"]
    elementId: Literal["6dfea845bb52ec251a31af43"]


class LegacyCasePolicy(_LegacyClosed):
    case_id: CaseId = "oct20-terminal-fillet-reactivation"
    environment: Literal["development"] = "development"
    adoption_boundary: Literal[1792540800] = 1792540800
    proposal_created_at: Literal[1792513443] = 1792513443
    execution_start: Literal[1792513486] = 1792513486
    execution_end_exclusive: Literal[1792513490] = 1792513490
    sunset: Literal[1792713600] = 1792713600
    context: LegacyContext
    operation: Literal["SET_UNSUPPRESSED"] = "SET_UNSUPPRESSED"
    original_suppressed: Literal[True] = True
    intended_suppressed: Literal[False] = False
    terminal_fillet: Literal[True] = True


class LegacyEnrollment(_LegacyClosed):
    """Separately reviewed pins, not an independent historical receipt.

    No constructor from DB discovery is provided. Only the static private policy
    slot can supply an enrollment to the coordinator; callers cannot select one.
    """

    schema_version: Literal["legacy-enrollment-v1"] = "legacy-enrollment-v1"
    case_id: CaseId = "oct20-terminal-fillet-reactivation"
    identity_basis: Literal["trusted_retained_database"] = "trusted_retained_database"
    history_source: Literal["preserved_october20_conversation"]
    history_evidence_digest: Digest = Field(repr=False)
    reviewer: PrivateText
    review_id: PrivateText
    reviewed_at: int = Field(ge=1792540800, lt=1792713600)
    binding: Binding = Field(repr=False)
    record_id: Handle = Field(repr=False)
    fence_user: PrivateText
    fence_workspace_key: Digest = Field(repr=False)
    fence_record_id: Handle = Field(repr=False)
    plan_digest: Digest = Field(repr=False)
    payload_fingerprint: Digest = Field(repr=False)
    created_at: Literal[1792513443]
    expires_at: Literal[1792513563]
    feature_id: PrivateText
    target_position: int = Field(ge=1, le=20)
    stack: Literal["https://cad.onshape.com/api"]
    company_id: None
    current_generation: PrivateText

    @model_validator(mode="after")
    def exact_relationship(self) -> LegacyEnrollment:
        if (
            self.binding.user != self.fence_user
            or self.binding.workspace_key != self.fence_workspace_key
            or self.record_id != self.fence_record_id
            or self.binding.context.model_dump()
            != LegacyContext.model_validate(
                self.binding.context.model_dump()
            ).model_dump()
        ):
            raise ValueError("invalid legacy enrollment relationship")
        return self


class ProviderSettlementEvidence(_LegacyClosed):
    """A provider-issued confirmation reviewed out of band, NOT an API predicate.

    No current Onshape history/head/ack field is asserted to supply this guarantee.
    The operator must retain the actual confirmation and verify its semantics.
    """

    category: Literal["provider_issued_terminal_confirmation"]
    issuer: PrivateText
    evidence_reference: PrivateText
    evidence_digest: Digest = Field(repr=False)
    user: PrivateText
    context: LegacyContext
    execution_start: Literal[1792513486]
    execution_end_exclusive: Literal[1792513490]
    issued_at: int = Field(ge=1792513490)
    disposition: Literal["terminated_no_outstanding_activity_can_later_apply"]


class SettlementReview(_LegacyClosed):
    case_id: CaseId
    enrollment_fingerprint: Digest = Field(repr=False)
    reviewer: PrivateText
    review_id: PrivateText
    reviewed_at: int = Field(ge=0)
    valid_until: int = Field(ge=0)
    evidence: ProviderSettlementEvidence = Field(repr=False)
    disposition: Literal["approved_for_exact_legacy_retirement"]


class QuiescenceReview(_LegacyClosed):
    case_id: CaseId
    enrollment_fingerprint: Digest = Field(repr=False)
    reviewer: PrivateText
    review_id: PrivateText
    reviewed_at: int = Field(ge=0)
    valid_until: int = Field(ge=0)
    deployment_inventory_digest: Digest = Field(repr=False)
    write_admission_evidence_digest: Digest = Field(repr=False)
    worker_drain_evidence_digest: Digest = Field(repr=False)
    queue_inspection_digest: Digest = Field(repr=False)
    approval_inspection_digest: Digest = Field(repr=False)
    recovery_exclusion_digest: Digest = Field(repr=False)
    effective_writes_off: Literal[True]
    workers_drained: Literal[True]
    no_queued_same_user_write: Literal[True]
    no_resumable_historical_approval: Literal[True]
    original_session_hard_inactive: Literal[True]
    no_competing_recovery: Literal[True]


class LegacyReview(_LegacyClosed):
    settlement: SettlementReview = Field(repr=False)
    quiescence: QuiescenceReview = Field(repr=False)


class LegacyEvidence(Closed):
    schema_version: Literal["legacy-pinned-evidence-v1"] = "legacy-pinned-evidence-v1"
    projection_version: Literal["terminal-fillet-6"] = "terminal-fillet-6"
    enrollment_fingerprint: Digest = Field(repr=False)
    review_fingerprint: Digest = Field(repr=False)
    context: LegacyContext = Field(repr=False)
    baseline: Baseline = Field(repr=False)
    head_before: CadId = Field(repr=False)
    head_after: CadId = Field(repr=False)
    started_monotonic: float = Field(ge=0, allow_inf_nan=False)
    finished_monotonic: float = Field(ge=0, allow_inf_nan=False)


class LegacyResult(_LegacyClosed):
    schema_version: Literal["legacy-administrative-result-v1"] = (
        "legacy-administrative-result-v1"
    )
    state: Literal["operator_recovered"] = "operator_recovered"
    original_execution_outcome: Literal["execution_uncertain"] = "execution_uncertain"
    identity_basis: Literal["trusted_retained_database"] = "trusted_retained_database"
    disposition: Literal["legacy_administrative_retirement"] = (
        "legacy_administrative_retirement"
    )
    recovered_at: int = Field(ge=0)


def enrollment_fingerprint(enrollment: LegacyEnrollment) -> str:
    return fingerprint(enrollment.model_dump(mode="json"))


def review_fingerprint(review: LegacyReview) -> str:
    return fingerprint(review.model_dump(mode="json"))


@dataclass(eq=False, repr=False)
class _LegacyRun:
    db: Session
    transaction: SessionTransaction
    enrollment: LegacyEnrollment
    review: LegacyReview
    saved: StoredPlan
    raw_payload: str
    started: float
    evidence: LegacyEvidence | None = field(default=None)
    consumed: bool = False

    def current(self, db: Session) -> None:
        if (
            db is not self.db
            or db.get_transaction() is not self.transaction
            or not self.transaction.is_active
            or db.in_nested_transaction()
            or not 0 <= monotonic() - self.started <= TRANSACTION_SECONDS
        ):
            raise LegacyRecoveryDenied("legacy_run_invalid")

    def register(self, evidence: LegacyEvidence) -> None:
        self.current(self.db)
        if (
            type(evidence) is not LegacyEvidence
            or self.evidence is not None
            or self.consumed
            or evidence.enrollment_fingerprint
            != enrollment_fingerprint(self.enrollment)
            or evidence.review_fingerprint != review_fingerprint(self.review)
            or evidence.context.model_dump()
            != self.enrollment.binding.context.model_dump()
            or evidence.baseline.context.model_dump() != evidence.context.model_dump()
            or evidence.head_before != evidence.head_after
            or evidence.baseline.microversion != evidence.head_before
            or evidence.started_monotonic < self.started
            or not 0
            <= evidence.finished_monotonic - evidence.started_monotonic
            <= CAPTURE_SECONDS
        ):
            raise LegacyRecoveryDenied("legacy_evidence_invalid")
        self.evidence = evidence

    def consume(self, db: Session, evidence: LegacyEvidence) -> None:
        used = self.consumed
        self.consumed = True
        self.current(db)
        if used or evidence is not self.evidence:
            raise LegacyRecoveryDenied("legacy_evidence_unregistered_or_used")
        if not 0 <= monotonic() - evidence.finished_monotonic <= HANDOFF_SECONDS:
            raise LegacyRecoveryDenied("legacy_evidence_expired")
