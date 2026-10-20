"""Session-owned discovery and read-only final-state reconciliation.

A consumed handle is a status reference, never renewed approval authority. No
mutation method, model, retry or rollback is reachable from this module.
"""

from typing import Annotated, Literal

from fastapi import Request
from pydantic import Field
from sqlalchemy import delete
from sqlalchemy.orm import Session

from forge_api.auth.runtime import AuthRuntime
from forge_api.auth.security import audit
from forge_api.db.models import WriteFence, WriteRecord, now
from forge_api.integrations.onshape.contracts import WorkspaceReference

from . import plan_service, plan_storage, service, storage
from .domain import Binding, Closed, EditError, Handle
from .plans import ModifyPlan, OperationPreview, OperationState, PlanResult


class NoRecovery(Closed):
    state: Literal["none"] = "none"


class RecoveryView(Closed):
    state: Literal["execution_uncertain", "claimed", "verifying", "recovery_required"]
    plan: Handle | None
    operations: Annotated[tuple[OperationPreview, ...], Field(max_length=5)] = ()
    operation_states: Annotated[tuple[OperationState, ...], Field(max_length=5)] = ()
    reconciliation: Literal["available", "manual_required"] = "manual_required"


def _record(db: Session, binding: Binding) -> WriteRecord | None:
    fence = db.get(WriteFence, binding.workspace_key)
    if fence is None or fence.user_id != binding.user:
        return None
    record = db.get(WriteRecord, fence.record_id)
    if record is None:
        # Legacy purged fences have no session proof. Expose no handle or plan.
        return None
    if record.user_id != binding.user or record.session_hash != binding.session:
        return None
    return record


def _eligible(plan: ModifyPlan) -> bool:
    if len(plan.operations) != 1:
        return False
    op = plan.operations[0]
    return (
        op.operation.type in ("SET_SUPPRESSED", "SET_UNSUPPRESSED")
        and op.target.feature_type == "fillet"
        and op.target.feature_id == plan.baseline.feature_id
        and op.target.position == plan.baseline.position
        and plan.baseline.suppressed == (op.operation.type == "SET_UNSUPPRESSED")
    )


def discover(
    request: Request, auth: AuthRuntime, context: WorkspaceReference
) -> NoRecovery | RecoveryView:
    with auth.sessions.begin() as db:
        binding = service.authority(request, auth, db, context, lock=True)
        storage.cleanup(db)
        record = _record(db, binding)
        if record is None:
            # A legacy orphan still presents a safe manual path, with no private
            # plan/session data. New records never become orphaned by cleanup.
            fence = db.get(WriteFence, binding.workspace_key)
            if (
                fence is not None
                and fence.user_id == binding.user
                and db.get(WriteRecord, fence.record_id) is None
            ):
                return RecoveryView(state="recovery_required", plan=None)
            return NoRecovery()
        if record.payload is None:
            return RecoveryView(state="recovery_required", plan=None)
        try:
            saved = plan_storage.load(record)
        except EditError:
            # Legacy Phase 9 or corrupt records cannot be interpreted as A2.
            return RecoveryView(state="recovery_required", plan=None)
        if saved.plan.binding != binding:
            return NoRecovery()
        result = plan_storage.result(record)
        if result.state not in ("execution_uncertain", "claimed", "verifying"):
            return RecoveryView(state="recovery_required", plan=None)
        return RecoveryView(
            state=result.state,
            plan=record.id,
            operations=tuple(op.preview for op in saved.plan.operations),
            operation_states=result.operations,
            reconciliation="available"
            if result.state == "execution_uncertain" and _eligible(saved.plan)
            else "manual_required",
        )


def reconcile(request: Request, auth: AuthRuntime, handle: str) -> PlanResult:
    with auth.sessions.begin() as db:
        user, session = service.identity(request, auth, db)
        record = storage.owned(db, handle, user, session)
        saved = plan_storage.load(record)
        binding = service.authority(
            request, auth, db, saved.plan.binding.context, lock=True
        )
        if binding != saved.plan.binding or _record(db, binding) != record:
            raise EditError("context_changed")
        storage.cleanup(db)
        if (
            record.payload is None
            or record.state != "execution_uncertain"
            or not _eligible(saved.plan)
        ):
            raise EditError("recovery_required")
        plan = saved.plan
    try:
        # Fresh authenticated head-bracketed pinned reads. The dispatch path is
        # never entered, even if writes are enabled or the state does not match.
        provider = service.client(request, auth)
        current = plan_service._capture(request, binding, provider)
        excluded = {"microversion", "fingerprint", "suppressed"}
        before = plan.baseline.model_dump(exclude=excluded)
        after = current.baseline.model_dump(exclude=excluded)
        desired = plan.operations[0].operation.type == "SET_SUPPRESSED"
        if before != after or current.baseline.suppressed != desired:
            raise EditError("recovery_required")
    except Exception:
        raise EditError("recovery_required") from None
    with auth.sessions.begin() as db:
        # Serialize against other workers and recheck all authority/fence/record
        # predicates after the read. One transaction closes only this fence.
        if service.authority(request, auth, db, binding.context, lock=True) != binding:
            raise EditError("context_changed")
        try:
            if provider.head(binding.context) != current.baseline.microversion:
                raise EditError("recovery_required")
        except Exception:
            raise EditError("recovery_required") from None
        final_record = _record(db, binding)
        if (
            final_record is None
            or final_record.id != handle
            or final_record.state != "execution_uncertain"
        ):
            raise EditError("recovery_required")
        storage.cleanup(db)
        if final_record.payload is None or plan_storage.load(final_record).plan != plan:
            raise EditError("recovery_required")
        result = PlanResult(
            state="reconciled_current_state",
            operations=plan_storage.result(final_record).operations,
        )
        final_record.state = result.state
        final_record.payload = result.model_dump_json()
        final_record.purge_at = now() + 900
        db.execute(
            delete(WriteFence).where(
                WriteFence.workspace_key == binding.workspace_key,
                WriteFence.user_id == binding.user,
                WriteFence.record_id == handle,
            )
        )
        audit(db, "write_current_state_reconciled", user_id=binding.user)
        return result
