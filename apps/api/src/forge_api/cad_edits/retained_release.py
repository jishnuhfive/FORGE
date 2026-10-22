"""Provider-free exact retained-record closure. No credential or callback input.

Only the internal coordinator invokes this module. All mutations belong to its
single transaction; exceptions must propagate out of that transaction to rollback.
"""

import hashlib
from time import monotonic

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session as DatabaseSession

from forge_api.auth.security import audit
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
from .plans import StoredPlan
from .retained_contracts import (
    HANDOFF_SECONDS,
    AdministrativeRecoveryResult,
    RetainedRecoveryDenied,
    RetainedRecoveryReference,
    VerifiedRetainedRecoveryEvidence,
    _RecoveryRun,
    check_independent,
)

_CLOSED_STATES = (
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
_EXPECTED_AUDITS = (
    "write_proposal_claimed",
    "write_dispatch_started",
    "write_provider_acknowledged",
    "write_uncertain",
)
_NON_EXECUTION_AUDITS = (
    "write_proposal_created",
    "write_proposal_expired",
    "write_proposal_invalidated",
    "write_proposal_cancelled",
)


def _environment(settings: Settings, reference: RetainedRecoveryReference) -> None:
    review = reference.review
    if settings.environment != "development" or settings.forge_cad_writes_enabled:
        raise RetainedRecoveryDenied("development_writes_off_required")
    if not all(
        (
            review.operator_authorized,
            review.independent_receipt_reviewed,
            review.writers_drained,
            review.upstream_settled,
        )
    ):
        raise RetainedRecoveryDenied("operator_review_and_settlement_required")
    if (
        review.stack != str(settings.onshape_api_base_url)
        or review.company_id != settings.onshape_company_id
    ):
        raise RetainedRecoveryDenied("reviewed_configuration_mismatch")


def _audits(db: DatabaseSession, reference: RetainedRecoveryReference, at: int) -> None:
    historical = reference.historical
    events = list(
        db.scalars(
            select(AuditEvent)
            .where(
                AuditEvent.user_id == reference.independent.user,
                AuditEvent.created_at >= historical.created_at,
                AuditEvent.kind.startswith("write_"),
                AuditEvent.kind.not_in(_NON_EXECUTION_AUDITS),
            )
            .with_for_update(read=True)
            .execution_options(populate_existing=True)
        )
    )
    times: list[int] = []
    for kind in _EXPECTED_AUDITS:
        found = [event for event in events if event.kind == kind]
        if len(found) != 1 or found[0].outcome != "ok":
            raise RetainedRecoveryDenied("unique_uncertain_audit_required")
        times.append(found[0].created_at)
    if (
        len(events) != 4
        or times != sorted(times)
        or times[-1] > historical.created_at + 900
        or times[-1] > at
    ):
        raise RetainedRecoveryDenied("unique_uncertain_audit_required")


def _eligible(saved: StoredPlan) -> None:
    plan = saved.plan
    if (
        saved.result.state != "execution_uncertain"
        or saved.result.operations != ("execution_uncertain",)
        or len(plan.operations) != 1
    ):
        raise RetainedRecoveryDenied("explicit_single_uncertain_operation_required")
    op = plan.operations[0]
    desired = op.operation.type == "SET_SUPPRESSED"
    if (
        op.operation.type not in ("SET_SUPPRESSED", "SET_UNSUPPRESSED")
        or op.target.feature_type != "fillet"
        or op.target.feature_id != plan.baseline.feature_id
        or op.target.position != plan.baseline.position
        or plan.baseline.suppressed == desired
        or op.preview.feature_type != "fillet"
        or op.preview.position != plan.baseline.position
        or op.preview.label != plan.baseline.label
        or op.preview.field != "Suppression"
        or op.preview.current != ("Active" if desired else "Suppressed")
        or op.preview.proposed != ("Suppressed" if desired else "Active")
    ):
        raise RetainedRecoveryDenied("unsupported_retained_operation")


def _validate_locked(
    db: DatabaseSession, settings: Settings, reference: RetainedRecoveryReference
) -> tuple[WriteRecord, StoredPlan, OnshapeAuthorization]:
    _environment(settings, reference)
    at = now()
    historical, independent, review = (
        reference.historical,
        reference.independent,
        reference.review,
    )
    user_lock(db, independent.user)
    original = db.scalar(
        select(Session)
        .where(
            Session.token_hash == historical.binding.session,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if (
        original is None
        or original.user_id != independent.user
        or original.created_at > historical.created_at
        or (
            original.expires_at > at
            and (original.revoked_at is None or original.revoked_at > at)
        )
    ):
        raise RetainedRecoveryDenied("historical_inactive_identity_required")
    grant = db.scalar(
        select(OnshapeAuthorization)
        .where(
            OnshapeAuthorization.user_id == independent.user,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if (
        grant is None
        or grant.status != "connected"
        or grant.stack != review.stack
        or grant.company_id != review.company_id
        or grant.generation != review.current_generation
        or not grant.granted_scope
        or "OAuth2Read" not in grant.granted_scope.split()
        or (grant.retry_after is not None and grant.retry_after > at)
    ):
        raise RetainedRecoveryDenied("current_connected_read_grant_required")
    workspace_key = hashlib.sha256(
        (
            "forge.workspace-fence.v1:"
            + review.stack
            + ":"
            + independent.context.documentId
            + ":"
            + independent.context.workspaceId
        ).encode()
    ).hexdigest()
    if historical.binding.workspace_key != workspace_key:
        raise RetainedRecoveryDenied("workspace_reference_mismatch")
    related = list(
        db.scalars(
            select(WriteFence)
            .where(
                (WriteFence.user_id == independent.user)
                | (WriteFence.workspace_key == workspace_key)
                | (WriteFence.record_id == historical.record_id)
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    )
    if len(related) != 1 or (
        related[0].user_id != independent.user
        or related[0].workspace_key != workspace_key
        or related[0].record_id != historical.record_id
    ):
        raise RetainedRecoveryDenied("exact_single_fence_required")
    record = db.scalar(
        select(WriteRecord)
        .where(
            WriteRecord.id == historical.record_id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if (
        record is None
        or record.state != "execution_uncertain"
        or record.user_id != independent.user
        or record.session_hash != historical.binding.session
        or record.digest != historical.plan_digest
        or record.created_at != historical.created_at
        or record.expires_at != historical.expires_at
        or record.payload is None
        or len(record.payload.encode()) > 65536
        or record.created_at + 900 > at
        or record.expires_at > at
    ):
        raise RetainedRecoveryDenied("exact_aged_uncertain_record_required")
    try:
        saved = plan_storage.load(record)
    except EditError:
        raise RetainedRecoveryDenied("retained_payload_invalid") from None
    if (
        saved.plan.binding != historical.binding
        or fingerprint(saved.model_dump(mode="json")) != historical.payload_fingerprint
    ):
        raise RetainedRecoveryDenied("retained_payload_changed")
    check_independent(independent, saved)
    _eligible(saved)
    # Same-user admission/claim holds user_lock. This is not a global phantom lock.
    if (
        db.scalar(
            select(WriteRecord.id)
            .where(
                WriteRecord.user_id == independent.user,
                WriteRecord.id != historical.record_id,
                WriteRecord.state.not_in(_CLOSED_STATES),
            )
            .limit(1)
        )
        is not None
    ):
        raise RetainedRecoveryDenied("conflicting_user_operation")
    _audits(db, reference, at)
    return record, saved, grant


def lock_retained_record(
    db: DatabaseSession,
    settings: Settings,
    reference: RetainedRecoveryReference,
    *,
    started: float,
) -> tuple[_RecoveryRun, str | None]:
    transaction = db.get_transaction()
    if transaction is None or db.in_nested_transaction():
        raise RetainedRecoveryDenied("recovery_transaction_required")
    record, saved, grant = _validate_locked(db, settings, reference)
    assert record.payload is not None
    return _RecoveryRun(
        db,
        transaction,
        reference,
        record.payload,
        saved,
        started,
    ), grant.granted_scope


def release_retained_record(
    db: DatabaseSession,
    settings: Settings,
    run: _RecoveryRun,
    evidence: VerifiedRetainedRecoveryEvidence,
) -> AdministrativeRecoveryResult:
    """One exact redacted closure + deletion + fixed audit, or outer rollback.

    No transport, token manager, mutation client, or provider callback is accepted.
    """
    run.consume(db, evidence)
    reference = run.reference
    record, saved, _ = _validate_locked(db, settings, reference)
    if record.payload != run.raw_payload or saved != run.saved:
        raise RetainedRecoveryDenied("retained_payload_changed")
    excluded = {"microversion", "fingerprint", "suppressed"}
    if (
        saved.plan.baseline.model_dump(exclude=excluded)
        != evidence.baseline.model_dump(exclude=excluded)
        or evidence.baseline.suppressed != reference.independent.desired_suppressed
    ):
        raise RetainedRecoveryDenied("current_state_does_not_match")
    # Revalidation is bounded too; never mutate after the handoff/run expires.
    run._current(db)
    if monotonic() - evidence.finished_monotonic > HANDOFF_SECONDS:
        raise RetainedRecoveryDenied("evidence_handoff_expired")
    result = AdministrativeRecoveryResult(recovered_at=now())
    historical = reference.historical
    updated = list(
        db.scalars(
            update(WriteRecord)
            .where(
                WriteRecord.id == historical.record_id,
                WriteRecord.user_id == reference.independent.user,
                WriteRecord.session_hash == historical.binding.session,
                WriteRecord.digest == historical.plan_digest,
                WriteRecord.created_at == historical.created_at,
                WriteRecord.expires_at == historical.expires_at,
                WriteRecord.state == "execution_uncertain",
                WriteRecord.payload == run.raw_payload,
            )
            .values(
                state="operator_recovered",
                payload=result.model_dump_json(),
                purge_at=result.recovered_at + 900,
            )
            .returning(WriteRecord.id)
        )
    )
    if len(updated) != 1:
        raise RetainedRecoveryDenied("exact_record_update_required")
    removed = list(
        db.scalars(
            delete(WriteFence)
            .where(
                WriteFence.user_id == reference.independent.user,
                WriteFence.workspace_key == historical.binding.workspace_key,
                WriteFence.record_id == historical.record_id,
            )
            .returning(WriteFence.workspace_key)
        )
    )
    if len(removed) != 1:
        raise RetainedRecoveryDenied("exact_single_fence_required")
    audit(
        db, "write_retained_operator_recovery", "local_only", reference.independent.user
    )
    db.flush()
    return result
