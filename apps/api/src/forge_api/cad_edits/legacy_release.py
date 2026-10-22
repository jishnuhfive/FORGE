"""Provider-free atomic closure of ONLY the static enrolled legacy incident.

No token manager, HTTP, reader, coordinator, runtime, provider callback, or normal
execution finish function is reachable from this module.
"""

from time import monotonic

from sqlalchemy import delete, update
from sqlalchemy.orm import Session

from forge_api.auth.security import audit
from forge_api.core.config import Settings
from forge_api.db.models import WriteFence, WriteRecord, now

from .legacy_contracts import (
    HANDOFF_SECONDS,
    LegacyEvidence,
    LegacyRecoveryDenied,
    LegacyResult,
    _LegacyRun,
)
from .legacy_enrollment import validate_locked
from .legacy_policy import require_enrollment


def release_legacy_record(
    db: Session, settings: Settings, run: _LegacyRun, evidence: LegacyEvidence
) -> LegacyResult:
    run.consume(db, evidence)
    enrollment = run.enrollment
    record, saved, _ = validate_locked(db, settings, enrollment, run.review)
    if record.payload != run.raw_payload or saved != run.saved:
        raise LegacyRecoveryDenied("legacy_payload_changed")
    excluded = {"microversion", "fingerprint", "suppressed"}
    if evidence.baseline.suppressed is not False or saved.plan.baseline.model_dump(
        exclude=excluded
    ) != evidence.baseline.model_dump(exclude=excluded):
        raise LegacyRecoveryDenied("legacy_current_state_mismatch")
    run.current(db)
    if monotonic() - evidence.finished_monotonic > HANDOFF_SECONDS:
        raise LegacyRecoveryDenied("legacy_evidence_expired")
    if require_enrollment(settings, run.review) != enrollment:
        raise LegacyRecoveryDenied("legacy_enrollment_changed")
    result = LegacyResult(recovered_at=now())
    updated = list(
        db.scalars(
            update(WriteRecord)
            .where(
                WriteRecord.id == enrollment.record_id,
                WriteRecord.user_id == enrollment.binding.user,
                WriteRecord.session_hash == enrollment.binding.session,
                WriteRecord.digest == enrollment.plan_digest,
                WriteRecord.created_at == enrollment.created_at,
                WriteRecord.expires_at == enrollment.expires_at,
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
        raise LegacyRecoveryDenied("legacy_exact_update_required")
    removed = list(
        db.scalars(
            delete(WriteFence)
            .where(
                WriteFence.user_id == enrollment.fence_user,
                WriteFence.workspace_key == enrollment.fence_workspace_key,
                WriteFence.record_id == enrollment.fence_record_id,
            )
            .returning(WriteFence.workspace_key)
        )
    )
    if len(removed) != 1:
        raise LegacyRecoveryDenied("legacy_exact_delete_required")
    audit(db, "write_legacy_retained_retirement", "local_only", enrollment.binding.user)
    db.flush()
    return result
