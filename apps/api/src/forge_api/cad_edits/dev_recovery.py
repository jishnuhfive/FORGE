"""Internal operator-only orphan recovery; no route, CLI or provider transport.

Explicit operator authorization and independently established upstream settlement
are prerequisites. Supply the exact reference from trusted preserved evidence in
memory, never by guessing from the current fence. This deliberately requires a
quiescent operational table and cannot recover a retained/possibly live claim.
"""

from pydantic import Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session as DatabaseSession
from sqlalchemy.orm import sessionmaker

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

from .domain import Closed, Digest, Handle


class RecoveryReference(Closed):
    user: str = Field(min_length=1, max_length=36, repr=False)
    session: Digest = Field(repr=False)
    workspace_key: Digest = Field(repr=False)
    record_id: Handle = Field(repr=False)
    created_at: int = Field(ge=0)
    settled: bool


class RecoveryDenied(Exception):
    """Fixed reasons only; never attach private reference or database contents."""


def recover_orphaned_fence(
    sessions: sessionmaker[DatabaseSession],
    settings: Settings,
    reference: RecoveryReference,
) -> None:
    """Commit exactly one deletion plus a sanitized audit, or roll back everything.

    This is database administration, not browser/session write authority. The
    original session may have expired; it must still identify the preserved user.
    No session is revived, token refreshed, proposal restored or CAD contacted.
    """
    if settings.environment != "development" or settings.forge_cad_writes_enabled:
        raise RecoveryDenied("development_writes_off_required")
    if reference.settled is not True:
        raise RecoveryDenied("operator_settlement_required")

    with sessions.begin() as db:
        user_lock(db, reference.user)
        original_session = db.scalar(
            select(Session)
            .where(Session.token_hash == reference.session)
            .with_for_update()
        )
        if original_session is None or original_session.user_id != reference.user:
            raise RecoveryDenied("original_identity_mismatch")
        grant = db.scalar(
            select(OnshapeAuthorization)
            .where(OnshapeAuthorization.user_id == reference.user)
            .with_for_update()
        )
        if (
            grant is None
            or grant.status != "connected"
            or grant.stack != str(settings.onshape_api_base_url)
            or grant.company_id != settings.onshape_company_id
        ):
            raise RecoveryDenied("original_identity_mismatch")

        related = list(
            db.scalars(
                select(WriteFence)
                .where(
                    (WriteFence.user_id == reference.user)
                    | (WriteFence.workspace_key == reference.workspace_key)
                    | (WriteFence.record_id == reference.record_id)
                )
                .with_for_update()
            )
        )
        if len(related) != 1 or (
            related[0].user_id != reference.user
            or related[0].workspace_key != reference.workspace_key
            or related[0].record_id != reference.record_id
        ):
            raise RecoveryDenied("exact_single_fence_required")
        if db.get(WriteRecord, reference.record_id) is not None:
            raise RecoveryDenied("referenced_record_present")
        if reference.created_at + 900 > now():
            raise RecoveryDenied("retention_not_elapsed")
        # Stronger than pending/claimed only: do not recover around ANY retained
        # operational record, including unknown states or another uncertainty.
        if db.scalar(select(WriteRecord.id).limit(1)) is not None:
            raise RecoveryDenied("operational_records_remain")

        kinds = (
            "write_proposal_claimed",
            "write_dispatch_started",
            "write_provider_acknowledged",
            "write_uncertain",
        )
        events = list(
            db.scalars(
                select(AuditEvent).where(
                    AuditEvent.user_id == reference.user,
                    AuditEvent.created_at >= reference.created_at,
                    AuditEvent.kind.in_((*kinds, "write_operator_recovery")),
                )
            )
        )
        # Audits have no operation identifier. Require a unique four-event window;
        # ambiguity/later execution/repeated recovery must leave the fence intact.
        times: list[int] = []
        for kind in kinds:
            found = [event for event in events if event.kind == kind]
            if len(found) != 1 or found[0].outcome != "ok":
                raise RecoveryDenied("unique_uncertain_audit_required")
            times.append(found[0].created_at)
        if (
            len(events) != 4
            or times != sorted(times)
            or times[-1] > reference.created_at + 900
            or times[-1] > now()
        ):
            raise RecoveryDenied("unique_uncertain_audit_required")

        removed = list(
            db.scalars(
                delete(WriteFence)
                .where(
                    WriteFence.user_id == reference.user,
                    WriteFence.workspace_key == reference.workspace_key,
                    WriteFence.record_id == reference.record_id,
                )
                .returning(WriteFence.workspace_key)
            )
        )
        if len(removed) != 1:
            raise RecoveryDenied("exact_single_fence_required")
        audit(db, "write_operator_recovery", "local_only", reference.user)
