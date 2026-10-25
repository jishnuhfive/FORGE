"""Creation-specific whole-plan approval, shared durable claim/fence primitives."""

from time import monotonic
from typing import Any, Literal, cast

import httpx2 as httpx
from fastapi import Request
from sqlalchemy import delete

from forge_api.auth.runtime import AuthRuntime
from forge_api.auth.security import AuditKind, AuditOutcome, audit, random_token
from forge_api.cad_edits import service as authority
from forge_api.cad_edits import storage
from forge_api.cad_edits.domain import (
    Binding,
    Closed,
    Digest,
    EditError,
    Handle,
    fingerprint,
)
from forge_api.db.models import WriteFence, WriteRecord, now
from forge_api.integrations.onshape.client import ReadError
from forge_api.integrations.onshape.contracts import WorkspaceReference

from .compile import compile_brief
from .evidence import CreationEvidence
from .execution import ExecutionResult, execute
from .explain import explain_plan
from .models import CreationPlan, PlateWithHolesBrief
from .provider import CreationClient, feature


class BaselineParts(Closed):
    """Category digests of the approved baseline; no raw CAD data or identities."""

    marker: Digest
    inventory: Digest
    configuration: Digest
    bodies: Digest


class Approval(Closed):
    kind: Literal["creation-approval-v1"] = "creation-approval-v1"
    proposal_id: Handle
    binding: Binding
    brief: PlateWithHolesBrief
    plan: CreationPlan
    baseline: Digest
    baseline_parts: BaselineParts
    created_at: int
    expires_at: int


class StoredCreation(Closed):
    approval: Approval
    steps: tuple[
        Literal[
            "pending",
            "executing",
            "verifying",
            "verified_success",
            "execution_uncertain",
            "rejected",
            "skipped",
        ],
        ...,
    ]


def load(row: WriteRecord) -> Approval:
    try:
        stored = StoredCreation.model_validate_json(row.payload or "")
        approval = stored.approval
        if len(stored.steps) != len(approval.plan.steps):
            raise ValueError
        if (
            approval.kind != "creation-approval-v1"
            or fingerprint(approval.model_dump(mode="json")) != row.digest
            or approval.proposal_id != row.id
            or approval.binding.user != row.user_id
            or approval.binding.session != row.session_hash
            or approval.created_at != row.created_at
            or approval.expires_at != row.expires_at
        ):
            raise ValueError
        return approval
    except ValueError:
        raise EditError("proposal_tampered") from None


def require_supported(plan: CreationPlan) -> None:
    virtual: dict[str, dict[str, Any]] = {}
    for step in plan.steps:
        built = feature(step, virtual)
        if built["featureType"] == "extrude":
            from forge_api.integrations.onshape.edit_registry import quantity_parameter

            quantity_parameter(built, "SET_EXTRUDE_DEPTH")
        virtual[step.id] = {**built, "featureId": f"verified-{step.id}"}


def prepare(
    request: Request,
    auth: AuthRuntime,
    context: WorkspaceReference,
    brief: PlateWithHolesBrief,
) -> dict[str, Any]:
    plan = compile_brief(brief)
    require_supported(plan)  # Entire plan preflight: no partial execution of holes.
    with auth.sessions.begin() as db:
        binding = authority.authority(request, auth, db, context, lock=True)
        authority.admit(db, binding)
    provider = CreationClient(authority.client(request, auth), context)
    baseline = provider.capture()
    baseline.require_empty()
    approval = Approval(
        proposal_id=random_token(),
        binding=binding,
        brief=brief,
        plan=plan,
        baseline=baseline.digest,
        baseline_parts=BaselineParts(**baseline.parts),
        created_at=now(),
        expires_at=now() + 120,
    )
    digest = fingerprint(approval.model_dump(mode="json"))
    with auth.sessions.begin() as db:
        if authority.authority(request, auth, db, context, lock=True) != binding:
            raise EditError("context_changed")
        storage.unfenced(db, binding)
        storage.invalidate(db, binding.user, binding.session)
        db.add(
            WriteRecord(
                id=approval.proposal_id,
                user_id=binding.user,
                session_hash=binding.session,
                state="pending",
                digest=digest,
                payload=StoredCreation(
                    approval=approval, steps=tuple("pending" for _ in plan.steps)
                ).model_dump_json(),
                created_at=approval.created_at,
                expires_at=approval.expires_at,
                purge_at=approval.created_at + 900,
            )
        )
        audit(db, "write_proposal_created", user_id=binding.user)
    return {
        "proposal_id": approval.proposal_id,
        "digest": digest,
        "expires_at": approval.expires_at,
        "brief": brief.model_dump(mode="json"),
        "plan": plan.model_dump(mode="json"),
        "explanations": [e.model_dump(mode="json") for e in explain_plan(plan)],
        "limitations": [
            (
                "Top-plane rectangle and circle, additive blind Extrude only. "
                "REMOVE and face references await live contract confirmation."
            ),
            (
                "Sketch coordinates are editable; "
                "geometric dimension constraints are not created."
            ),
        ],
    }


def _budget(plan: CreationPlan) -> int:
    """Seconds for the whole approval: 30 per step plus one, under the UI's 120."""
    return min(110, 30 * (len(plan.steps) + 1))


def _cause(error: Exception) -> AuditOutcome:
    """Closed category for a pre-dispatch stop; never exception text or CAD data."""
    if isinstance(error, EditError):
        return cast(
            AuditOutcome,
            {
                "model_changed": "pre_head_moved",
                "unsupported_target": "pre_unsupported",
                "context_changed": "pre_context",
                "verification_failed": "pre_gate",
                "onshape_unavailable": "pre_read_failed",
                "invalid_provider_response": "pre_read_failed",
                "rate_limited": "pre_read_failed",
                "permission_or_access_required": "pre_read_failed",
            }.get(error.code, "pre_other"),
        )
    if isinstance(error, (ReadError, httpx.HTTPError, TimeoutError, OSError)):
        return "pre_read_failed"
    return "pre_other"


def _difference(approved: BaselineParts, now_: CreationEvidence) -> AuditOutcome:
    """First differing category, marker first: a moved revision is a real change."""
    current = now_.parts
    for name, outcome in (
        ("marker", "baseline_marker"),
        ("inventory", "baseline_inventory"),
        ("configuration", "baseline_configuration"),
        ("bodies", "baseline_bodies"),
    ):
        if getattr(approved, name) != current[name]:
            return cast(AuditOutcome, outcome)
    return "pre_other"


def status(request: Request, auth: AuthRuntime, handle: str) -> dict[str, Any]:
    from forge_api.auth.routes import active_session

    with auth.sessions() as db:
        current = active_session(request, auth, db)
        if current is None:
            raise EditError("session_expired", 401)
        row = storage.owned(db, handle, current.user_id, current.token_hash)
        load(row)
        return {
            "state": row.state,
            "steps": list(StoredCreation.model_validate_json(row.payload or "").steps),
        }


def approve(
    request: Request, auth: AuthRuntime, handle: str, digest: str
) -> dict[str, Any]:
    from forge_api.auth.routes import active_session

    if not auth.settings.forge_cad_writes_enabled:
        raise EditError("write_disabled", 403)
    started = monotonic()
    with auth.sessions.begin() as db:
        current = active_session(request, auth, db)
        if current is None:
            raise EditError("session_expired", 401)
        row = storage.owned(db, handle, current.user_id, current.token_hash)
        saved = load(row)
        if (
            authority.authority(request, auth, db, saved.binding.context, lock=True)
            != saved.binding
        ):
            raise EditError("context_changed")
        storage.claim_record(db, row, saved.binding, digest)
    provider = CreationClient(authority.client(request, auth), saved.binding.context)

    attempted = False
    result: ExecutionResult | None = None
    cause: AuditOutcome | None = None
    budget = _budget(saved.plan)

    def journal(states: tuple[str, ...], dispatched: bool) -> None:
        nonlocal attempted
        if "executing" in states:
            attempted = True
        with auth.sessions.begin() as db:
            if (
                authority.authority(request, auth, db, saved.binding.context, lock=True)
                != saved.binding
            ):
                raise EditError("context_changed")
            row = storage.owned(db, handle, saved.binding.user, saved.binding.session)
            if load(row) != saved or row.state not in ("claimed", "verifying"):
                raise EditError("proposal_used")
            if (
                not auth.settings.forge_cad_writes_enabled
                or monotonic() - started > budget
            ):
                raise EditError("verification_failed")
            row.state = "verifying"
            row.payload = StoredCreation.model_validate(
                {"approval": saved, "steps": states}
            ).model_dump_json()
            kind: AuditKind = (
                "write_dispatch_started"
                if "executing" in states
                else "write_provider_acknowledged"
                if "verifying" in states
                else "write_uncertain"
                if "execution_uncertain" in states
                else "write_failed"
                if "rejected" in states
                else "write_verified"
            )
            # The closed label of the first failed check, set by the kernel hook.
            stopped = kind in ("write_uncertain", "write_failed")
            audit(
                db,
                kind,
                cast(AuditOutcome, provider.last_rejection)
                if stopped and provider.last_rejection
                else "ok",
                user_id=saved.binding.user,
            )

    try:
        baseline = provider.capture()
        if baseline.digest != saved.baseline:
            cause = _difference(saved.baseline_parts, baseline)
            raise EditError("model_changed")
        result = execute(saved.plan, baseline, provider, journal)
        with auth.sessions.begin() as db:
            if (
                authority.authority(request, auth, db, saved.binding.context, lock=True)
                != saved.binding
            ):
                raise EditError("context_changed")
            row = storage.owned(db, handle, saved.binding.user, saved.binding.session)
            if load(row) != saved:
                raise EditError("proposal_tampered") from None
            safe = result.state != "execution_uncertain"
            row.state = result.state
            row.payload = StoredCreation.model_validate(
                {"approval": saved, "steps": result.steps}
            ).model_dump_json()
            if (
                not auth.settings.forge_cad_writes_enabled
                or monotonic() - started > budget
            ):
                raise EditError("verification_failed")
            if safe:
                db.execute(
                    delete(WriteFence).where(
                        WriteFence.record_id == handle,
                        WriteFence.user_id == saved.binding.user,
                    )
                )
        return {"state": result.state, "steps": list(result.steps)}
    except Exception as error:
        # Fail closed; never delete a fence on an unconfirmed transaction/result.
        with auth.sessions.begin() as db:
            from forge_api.db.coordination import user_lock

            user_lock(db, saved.binding.user)
            row = storage.owned(db, handle, saved.binding.user, saved.binding.session)
            if load(row) != saved:
                raise EditError("proposal_tampered") from None
            fence = db.get(WriteFence, saved.binding.workspace_key)
            if (
                result is not None
                and row.state == result.state
                and row.state in ("verified_success", "rejected")
                and StoredCreation.model_validate_json(row.payload or "").steps
                == result.steps
                and (fence is None or fence.record_id != handle)
            ):
                # Read-only confirmation of this run's already verified, committed
                # terminal state after a lost commit reply. No CAD/dispatch retry.
                return {"state": result.state, "steps": list(result.steps)}
            if attempted and (
                fence is None
                or fence.record_id != handle
                or fence.user_id != saved.binding.user
            ):
                raise EditError("recovery_required") from None
            steps = list(StoredCreation.model_validate_json(row.payload or "").steps)
            row.state = "execution_uncertain" if attempted else "rejected_stale"
            if not attempted:
                audit(
                    db,
                    "write_rejected_stale",
                    cause or _cause(error),
                    user_id=saved.binding.user,
                )
                db.execute(
                    delete(WriteFence).where(
                        WriteFence.record_id == handle,
                        WriteFence.user_id == saved.binding.user,
                    )
                )
        return {
            "state": "execution_uncertain" if attempted else "rejected_stale",
            "steps": steps,
        }
