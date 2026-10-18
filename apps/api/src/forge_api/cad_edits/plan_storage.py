"""A1 serialized records on Phase 9 tables, claims, fences and retention."""

from sqlalchemy import update
from sqlalchemy.orm import Session

from forge_api.auth.security import audit
from forge_api.db.models import WriteFence, WriteRecord, now

from . import storage
from .domain import EditError
from .plans import ModifyPlan, OperationState, PlanResult, StoredPlan, TargetCatalog


def pending(plan: ModifyPlan) -> PlanResult:
    states: tuple[OperationState, ...] = tuple("pending" for _ in plan.operations)
    return PlanResult(state="pending", operations=states)


def catalog(record: WriteRecord) -> TargetCatalog:
    if record.state != "candidate" or record.payload is None:
        raise EditError("proposal_used")
    try:
        value = TargetCatalog.model_validate_json(record.payload)
        storage.verify_record(record, value)
    except ValueError:
        raise EditError("proposal_tampered") from None
    if now() >= value.expires_at:
        raise EditError("proposal_expired")
    return value


def load(record: WriteRecord) -> StoredPlan:
    if record.payload is None:
        raise EditError("proposal_used")
    try:
        value = StoredPlan.model_validate_json(record.payload)
        storage.verify_record(record, value.plan)
        return value
    except ValueError:
        raise EditError("proposal_tampered") from None


def store(db: Session, plan: ModifyPlan) -> None:
    storage.store(db, plan, "pending")
    db.flush()
    record = db.get(WriteRecord, plan.proposal_id)
    assert record is not None
    record.payload = StoredPlan(
        plan=plan,
        result=pending(plan),
    ).model_dump_json()


def claim(db: Session, handle: str, user: str, session: str, digest: str) -> ModifyPlan:
    record = storage.owned(db, handle, user, session)
    if record.state != "pending":
        raise EditError("proposal_used")
    saved = load(record)
    if saved.result != pending(saved.plan):
        raise EditError("proposal_tampered")
    storage.claim_record(db, record, saved.plan.binding, digest)
    record.payload = StoredPlan(
        plan=saved.plan,
        result=PlanResult(state="claimed", operations=saved.result.operations),
    ).model_dump_json()
    return saved.plan


def cancel(db: Session, handle: str, user: str, session: str) -> PlanResult:
    record = storage.owned(db, handle, user, session)
    if record.state != "pending":
        raise EditError("proposal_used")
    saved = load(record)
    if saved.result != pending(saved.plan):
        raise EditError("proposal_tampered")
    if now() >= saved.plan.expires_at:
        raise EditError("proposal_expired")
    result = PlanResult(
        state="cancelled", operations=tuple("skipped" for _ in saved.plan.operations)
    )
    winner = db.scalar(
        update(WriteRecord)
        .where(
            WriteRecord.id == handle,
            WriteRecord.user_id == user,
            WriteRecord.session_hash == session,
            WriteRecord.state == "pending",
            WriteRecord.expires_at > now(),
        )
        .values(state="cancelled", payload=result.model_dump_json())
        .returning(WriteRecord.id)
    )
    if winner is None:
        raise EditError("proposal_used")
    audit(db, "write_proposal_cancelled", user_id=user)
    return result


def journal(db: Session, plan: ModifyPlan, result: PlanResult) -> None:
    record = storage.owned(
        db, plan.proposal_id, plan.binding.user, plan.binding.session
    )
    fence = db.get(WriteFence, plan.binding.workspace_key)
    if (
        record.state not in ("claimed", "verifying")
        or fence is None
        or fence.record_id != plan.proposal_id
        or fence.user_id != plan.binding.user
        or load(record).plan != plan
    ):
        raise EditError("workspace_fenced")
    record.state = result.state
    record.payload = StoredPlan(plan=plan, result=result).model_dump_json()


def finish(db: Session, plan: ModifyPlan, result: PlanResult) -> None:
    safe = result.state != "execution_uncertain"
    storage.finish(db, plan, result.state, safe_to_release=safe)
    record = db.get(WriteRecord, plan.proposal_id)
    if record is not None:
        # Safe finishes retain only closed statuses, not CAD bindings or labels.
        record.payload = (
            result.model_dump_json()
            if safe
            else StoredPlan(plan=plan, result=result).model_dump_json()
        )


def result(record: WriteRecord) -> PlanResult:
    if record.payload is None:
        raise EditError("proposal_used")
    if record.state in (
        "verified_success",
        "partial_failure",
        "write_failed",
        "rejected_stale",
        "cancelled",
    ):
        try:
            return PlanResult.model_validate_json(record.payload)
        except ValueError:
            raise EditError("proposal_tampered") from None
    saved = load(record)
    if (
        record.state == "execution_uncertain"
        and saved.result.state != "execution_uncertain"
    ):
        # A crashed/expired claimed worker is never resumed. Preserve already
        # verified prefixes; unknown in-flight work remains uncertain and fenced.
        states = list(saved.result.operations)
        for i, state in enumerate(states):
            if state != "verified_success":
                states[i] = "execution_uncertain"
                for j in range(i + 1, len(states)):
                    states[j] = "skipped"
                break
        return PlanResult(state="execution_uncertain", operations=tuple(states))
    return saved.result
