"""Database claims commit before dispatch; uncertain fences never expire open."""

import hmac

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from forge_api.auth.security import audit
from forge_api.db.models import WriteFence, WriteRecord, now

from .domain import Binding, EditError, Proposal, State, fingerprint


def invalidate(db: Session, user: str, session: str | None = None) -> None:
    query = update(WriteRecord).where(
        WriteRecord.user_id == user, WriteRecord.state.in_(("pending", "candidate"))
    )
    if session is not None:
        query = query.where(WriteRecord.session_hash == session)
    for owner in db.scalars(
        query.values(state="invalidated", payload=None).returning(WriteRecord.user_id)
    ):
        audit(db, "write_proposal_invalidated", user_id=owner)


def cleanup(db: Session) -> None:
    # No TTL ever deletes a fence. Orphaned claims become recovery-only.
    for owner in db.scalars(
        update(WriteRecord)
        .where(
            WriteRecord.state.in_(("candidate", "pending")),
            WriteRecord.expires_at <= now(),
        )
        .values(state="expired", payload=None)
        .returning(WriteRecord.user_id)
    ):
        audit(db, "write_proposal_expired", user_id=owner)
    db.execute(
        update(WriteRecord)
        .where(
            WriteRecord.state.in_(("claimed", "verifying")),
            WriteRecord.created_at + 150 <= now(),
        )
        .values(state="execution_uncertain")
    )
    db.execute(
        update(WriteRecord).where(WriteRecord.purge_at <= now()).values(payload=None)
    )
    db.execute(delete(WriteRecord).where(WriteRecord.purge_at <= now()))


def store(db: Session, proposal: Proposal, state: State) -> None:
    invalidate(db, proposal.binding.user, proposal.binding.session)
    db.add(
        WriteRecord(
            id=proposal.proposal_id,
            user_id=proposal.binding.user,
            session_hash=proposal.binding.session,
            state=state,
            digest=fingerprint(proposal.model_dump(mode="json")),
            payload=proposal.model_dump_json(),
            created_at=proposal.created_at,
            expires_at=proposal.expires_at,
            purge_at=proposal.created_at + 900,
        )
    )
    audit(db, "write_proposal_created", user_id=proposal.binding.user)


def owned(db: Session, handle: str, user: str, session: str) -> WriteRecord:
    record = db.get(WriteRecord, handle)
    if record is None or record.user_id != user or record.session_hash != session:
        raise EditError("proposal_unavailable", 404)
    return record


def decode(record: WriteRecord) -> Proposal:
    if record.payload is None:
        raise EditError(
            "proposal_expired" if record.state == "expired" else "proposal_used"
        )
    try:
        proposal = Proposal.model_validate_json(record.payload)
        if not hmac.compare_digest(
            record.digest, fingerprint(proposal.model_dump(mode="json"))
        ):
            raise EditError("proposal_tampered")
        if (
            proposal.proposal_id != record.id
            or proposal.binding.user != record.user_id
            or proposal.binding.session != record.session_hash
            or proposal.created_at != record.created_at
            or proposal.expires_at != record.expires_at
        ):
            raise EditError("proposal_tampered")
        return proposal
    except ValueError:
        raise EditError("proposal_tampered") from None


def claim(db: Session, handle: str, user: str, session: str, supplied: str) -> Proposal:
    record = owned(db, handle, user, session)
    if record.state != "pending":
        raise EditError(
            "proposal_expired" if record.state == "expired" else "proposal_used"
        )
    proposal = decode(record)
    if not hmac.compare_digest(record.digest, supplied):
        raise EditError("proposal_tampered")
    if now() >= record.expires_at:
        raise EditError("proposal_expired")
    winner = db.scalar(
        update(WriteRecord)
        .where(
            WriteRecord.id == handle,
            WriteRecord.state == "pending",
            WriteRecord.expires_at > now(),
            WriteRecord.digest == supplied,
        )
        .values(state="claimed")
        .returning(WriteRecord.id)
    )
    if winner is None:
        raise EditError("proposal_used")
    try:
        db.add(
            WriteFence(
                workspace_key=proposal.binding.workspace_key,
                user_id=user,
                record_id=handle,
            )
        )
        db.flush()
    except IntegrityError:
        db.rollback()
        raise EditError("workspace_fenced") from None
    audit(db, "write_proposal_claimed", user_id=user)
    # Caller commits this transaction BEFORE touching the provider.
    return proposal


def finish(
    db: Session, proposal: Proposal, state: State, *, safe_to_release: bool
) -> None:
    record = db.get(WriteRecord, proposal.proposal_id)
    if record is None:
        return
    record.state = state
    if safe_to_release:
        record.payload = None
        db.execute(
            delete(WriteFence).where(
                WriteFence.workspace_key == proposal.binding.workspace_key,
                WriteFence.record_id == proposal.proposal_id,
            )
        )
    audit(
        db,
        "write_rejected_stale"
        if state == "rejected_stale"
        else "write_verified"
        if state == "verified_success"
        else "write_uncertain"
        if not safe_to_release
        else "write_failed",
        user_id=record.user_id,
    )


def unfenced(db: Session, binding: Binding) -> None:
    if (
        db.scalar(
            select(WriteFence.workspace_key).where(
                (WriteFence.workspace_key == binding.workspace_key)
                | (WriteFence.user_id == binding.user)
            )
        )
        is not None
    ):
        raise EditError("workspace_fenced")
