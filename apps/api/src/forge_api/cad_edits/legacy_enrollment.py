"""Locked validation of separately enrolled pins; never discover/enroll a row.

Only the fixed private policy supplies identity. DB identity is trusted explicitly;
the unique user audit sequence is a consistency check, not an independent receipt.
No provider, credential, runtime, or mutation client capability belongs here.
"""

import hashlib

from sqlalchemy import or_, select
from sqlalchemy.orm import Session as DatabaseSession

from forge_api.core.config import Settings
from forge_api.db.coordination import user_lock
from forge_api.db.models import (
    AuditEvent,
    OnshapeAuthorization,
    Session,
    WriteFence,
    WriteRecord,
    now,
)

from . import plan_storage
from .domain import EditError, fingerprint
from .legacy_contracts import LegacyEnrollment, LegacyRecoveryDenied, LegacyReview
from .legacy_policy import CASE, require_enrollment
from .plans import StoredPlan

_CLOSED = (
    "cancelled",
    "expired",
    "invalidated",
    "rejected_stale",
    "write_failed",
    "verified_success",
    "partial_failure",
    "reconciled_current_state",
    "operator_recovered",
)
_SEQUENCE = (
    "write_proposal_claimed",
    "write_dispatch_started",
    "write_provider_acknowledged",
    "write_uncertain",
)
_NON_EXECUTION = (
    "write_proposal_created",
    "write_proposal_expired",
    "write_proposal_invalidated",
    "write_proposal_cancelled",
)


def _plan(saved: StoredPlan, enrollment: LegacyEnrollment) -> None:
    plan = saved.plan
    if (
        saved.result.state != "execution_uncertain"
        or saved.result.operations != ("execution_uncertain",)
        or len(plan.operations) != 1
    ):
        raise LegacyRecoveryDenied("legacy_single_uncertain_journal_required")
    op = plan.operations[0]
    if (
        plan.binding != enrollment.binding
        or plan.proposal_id != enrollment.record_id
        or plan.created_at != CASE.proposal_created_at
        or plan.created_at >= CASE.adoption_boundary
        or plan.expires_at != enrollment.expires_at
        or op.operation.type != CASE.operation
        or op.target.feature_type != "fillet"
        or op.target.feature_id != enrollment.feature_id
        or op.target.feature_id != plan.baseline.feature_id
        or op.target.position != enrollment.target_position
        or op.target.position != plan.baseline.position
        or plan.baseline.suppressed is not True
        or op.preview.type != CASE.operation
        or op.preview.feature_type != "fillet"
        or op.preview.position != plan.baseline.position
        or op.preview.label != plan.baseline.label
        or op.preview.field != "Suppression"
        or op.preview.current != "Suppressed"
        or op.preview.proposed != "Active"
    ):
        raise LegacyRecoveryDenied("legacy_plan_scope_mismatch")


def _audits(db: DatabaseSession, enrollment: LegacyEnrollment, at: int) -> None:
    events = list(
        db.scalars(
            select(AuditEvent)
            .where(
                AuditEvent.user_id == enrollment.binding.user,
                or_(
                    AuditEvent.created_at >= CASE.proposal_created_at,
                    AuditEvent.kind == "write_legacy_retained_retirement",
                ),
                AuditEvent.kind.startswith("write_"),
                AuditEvent.kind.not_in(_NON_EXECUTION),
            )
            .with_for_update(read=True)
            .execution_options(populate_existing=True)
        )
    )
    times: list[int] = []
    for kind in _SEQUENCE:
        found = [event for event in events if event.kind == kind]
        if len(found) != 1 or found[0].outcome != "ok":
            raise LegacyRecoveryDenied("legacy_unique_audit_required")
        times.append(found[0].created_at)
    if (
        len(events) != 4
        or times != sorted(times)
        or times[0] != CASE.execution_start
        or not all(
            CASE.execution_start <= stamp < CASE.execution_end_exclusive and stamp <= at
            for stamp in times
        )
    ):
        raise LegacyRecoveryDenied("legacy_unique_audit_required")


def validate_locked(
    db: DatabaseSession,
    settings: Settings,
    enrollment: LegacyEnrollment,
    review: LegacyReview,
) -> tuple[WriteRecord, StoredPlan, str]:
    if require_enrollment(settings, review) != enrollment:
        raise LegacyRecoveryDenied("legacy_enrollment_changed")
    at, binding = now(), enrollment.binding
    user_lock(db, binding.user)
    original = db.scalar(
        select(Session)
        .where(Session.token_hash == binding.session)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if (
        original is None
        or original.user_id != binding.user
        or original.created_at > CASE.proposal_created_at
        or (
            original.expires_at > at
            and (original.revoked_at is None or original.revoked_at > at)
        )
    ):
        raise LegacyRecoveryDenied("legacy_hard_inactive_identity_required")
    grant = db.scalar(
        select(OnshapeAuthorization)
        .where(OnshapeAuthorization.user_id == binding.user)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if (
        grant is None
        or grant.status != "connected"
        or grant.stack != enrollment.stack
        or grant.company_id != enrollment.company_id
        or grant.generation != enrollment.current_generation
        or not grant.granted_scope
        or "OAuth2Read" not in grant.granted_scope.split()
        or (grant.retry_after is not None and grant.retry_after > at)
    ):
        raise LegacyRecoveryDenied("legacy_current_read_grant_required")
    key = hashlib.sha256(
        (
            "forge.workspace-fence.v1:"
            + enrollment.stack
            + ":"
            + CASE.context.documentId
            + ":"
            + CASE.context.workspaceId
        ).encode()
    ).hexdigest()
    if binding.workspace_key != key:
        raise LegacyRecoveryDenied("legacy_workspace_mismatch")
    related = list(
        db.scalars(
            select(WriteFence)
            .where(
                (WriteFence.user_id == binding.user)
                | (WriteFence.workspace_key == key)
                | (WriteFence.record_id == enrollment.record_id)
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    )
    if len(related) != 1 or (
        related[0].user_id != enrollment.fence_user
        or related[0].workspace_key != enrollment.fence_workspace_key
        or related[0].record_id != enrollment.fence_record_id
    ):
        raise LegacyRecoveryDenied("legacy_exact_fence_required")
    record = db.scalar(
        select(WriteRecord)
        .where(WriteRecord.id == enrollment.record_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if (
        record is None
        or record.state != "execution_uncertain"
        or record.user_id != binding.user
        or record.session_hash != binding.session
        or record.digest != enrollment.plan_digest
        or record.created_at != enrollment.created_at
        or record.expires_at != enrollment.expires_at
        or record.created_at + 900 > at
        or record.expires_at > at
        or record.payload is None
        or len(record.payload.encode()) > 65536
    ):
        raise LegacyRecoveryDenied("legacy_exact_uncertain_record_required")
    try:
        saved = plan_storage.load(record)
    except EditError:
        raise LegacyRecoveryDenied("legacy_payload_invalid") from None
    if fingerprint(saved.model_dump(mode="json")) != enrollment.payload_fingerprint:
        raise LegacyRecoveryDenied("legacy_payload_changed")
    _plan(saved, enrollment)
    # Shared user lock serializes admission/claims. Counts do not prove global drain.
    if (
        db.scalar(
            select(WriteRecord.id)
            .where(
                WriteRecord.user_id == binding.user,
                WriteRecord.id != enrollment.record_id,
                WriteRecord.state.not_in(_CLOSED),
            )
            .limit(1)
        )
        is not None
    ):
        raise LegacyRecoveryDenied("legacy_conflicting_operation")
    _audits(db, enrollment, at)
    # Lock acquisition/validation may outlive a proof or cross the fixed sunset.
    if require_enrollment(settings, review) != enrollment:
        raise LegacyRecoveryDenied("legacy_enrollment_changed")
    return record, saved, grant.granted_scope
