"""Session-owned orchestration. Approval is the sole path to one guarded dispatch."""

import hashlib
from collections.abc import Callable
from contextlib import suppress
from time import monotonic, sleep
from typing import cast

import httpx2 as httpx
from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DatabaseSession

from forge_api.auth.provider import ProviderError
from forge_api.auth.routes import active_session
from forge_api.auth.runtime import AuthRuntime
from forge_api.auth.security import audit, random_token
from forge_api.db.coordination import user_lock
from forge_api.db.models import (
    OnshapeAuthorization,
    Session,
    WriteFence,
    WriteRecord,
    now,
)
from forge_api.integrations.onshape.contracts import WorkspaceReference
from forge_api.integrations.onshape.service import ReadGate
from forge_api.integrations.onshape.write_client import SafeEditClient

from . import storage
from .domain import (
    Baseline,
    Binding,
    EditError,
    Proposal,
    State,
    preview,
    require_current,
)


def authority(
    request: Request,
    auth: AuthRuntime,
    db: DatabaseSession,
    context: WorkspaceReference,
    *,
    lock: bool = False,
) -> Binding:
    current = active_session(request, auth, db)
    if current is None:
        raise EditError("session_expired", 401)
    if lock:
        user_lock(db, current.user_id)
        db.expire_all()
        current = db.scalar(
            select(Session)
            .where(Session.token_hash == current.token_hash)
            .with_for_update()
        )
        if current is None or active_session(request, auth, db) is None:
            raise EditError("session_expired", 401)
    grant = (
        db.scalar(
            select(OnshapeAuthorization)
            .where(OnshapeAuthorization.user_id == current.user_id)
            .with_for_update()
        )
        if lock
        else db.get(OnshapeAuthorization, current.user_id)
    )
    if grant is None or grant.status != "connected":
        raise EditError("reconsent_required", 403)
    scopes = set(grant.granted_scope.split()) if grant.granted_scope else set()
    if "OAuth2Write" not in scopes:
        known = {
            "OAuth2Read",
            "OAuth2ReadPII",
            "OAuth2Delete",
            "OAuth2Share",
            "OAuth2Purchase",
        }
        raise EditError(
            "write_permission_required"
            if scopes and scopes <= known
            else "authorization_unknown",
            403,
        )
    if "OAuth2Read" not in scopes:
        raise EditError("reconsent_required", 403)
    # Stable digest of high-entropy opaque CAD identities. Unlike a MAC keyed
    # by the rotating token-encryption key, this denial survives key rotation.
    key = hashlib.sha256(
        (
            "forge.workspace-fence.v1:"
            + f"{grant.stack}:{context.documentId}:{context.workspaceId}"
        ).encode()
    ).hexdigest()
    return Binding(
        user=current.user_id,
        session=current.token_hash,
        generation=grant.generation,
        context=context,
        workspace_key=key,
    )


def client(request: Request, auth: AuthRuntime) -> SafeEditClient:
    with auth.sessions() as db:
        current = active_session(request, auth, db)
        if current is None:
            raise EditError("session_expired", 401)
        user = current.user_id
    try:
        token = auth.tokens.get_valid_onshape_access_token(user)
    except ProviderError:
        raise EditError("reconsent_required", 403) from None
    return SafeEditClient(
        auth.settings, cast(httpx.Client, request.app.state.cad_transport), token
    )


def capture(
    request: Request, binding: Binding, provider: SafeEditClient, *, after: bool = False
) -> Baseline:
    gate = cast(ReadGate, request.app.state.cad_gate)
    try:
        with gate.enter(binding.user):
            return provider.evidence(binding.context, after=after)
    except Exception as error:
        from forge_api.integrations.onshape.client import ReadError

        if isinstance(error, ReadError):
            raise EditError("rate_limited", 429) from None
        raise


def create(
    request: Request,
    auth: AuthRuntime,
    context: WorkspaceReference,
    candidate: str | None = None,
) -> dict[str, object]:
    provider = client(request, auth)
    with auth.sessions.begin() as db:
        binding = authority(request, auth, db, context, lock=True)
        storage.cleanup(db)
        storage.unfenced(db, binding)
        recent = db.scalar(
            select(func.count())
            .select_from(WriteRecord)
            .where(
                WriteRecord.user_id == binding.user,
                WriteRecord.state == "admission",
                WriteRecord.created_at > now() - 60,
            )
        )
        if recent is not None and recent >= 6:
            raise EditError("rate_limited", 429)
        db.add(
            WriteRecord(
                id=random_token(),
                user_id=binding.user,
                session_hash=binding.session,
                state="admission",
                digest="0" * 64,
                payload=None,
                created_at=now(),
                expires_at=now() + 60,
                purge_at=now() + 60,
            )
        )
        old = None
        if candidate:
            record = storage.owned(db, candidate, binding.user, binding.session)
            if record.state != "candidate":
                raise EditError("proposal_used")
            old = storage.decode(record)
            if old.binding != binding or now() >= old.expires_at:
                raise EditError("proposal_expired")
    baseline = capture(request, binding, provider)
    if old and old.baseline != baseline:
        raise EditError("model_changed")
    created = now()
    proposal = Proposal(
        proposal_id=random_token(),
        binding=binding,
        baseline=baseline,
        created_at=created,
        expires_at=created + 120,
    )
    with auth.sessions.begin() as db:
        if authority(request, auth, db, context, lock=True) != binding:
            raise EditError("context_changed")
        storage.unfenced(db, binding)
        storage.store(db, proposal, "pending" if candidate else "candidate")
    if candidate:
        return {"proposal": preview(proposal).model_dump(mode="json")}
    return {
        "candidates": [
            {
                "handle": proposal.proposal_id,
                "label": baseline.label,
                "position": baseline.position,
                "expires_at": proposal.expires_at,
            }
        ]
    }


def identity(
    request: Request, auth: AuthRuntime, db: DatabaseSession
) -> tuple[str, str]:
    current = active_session(request, auth, db)
    if current is None:
        raise EditError("session_expired", 401)
    return current.user_id, current.token_hash


def status(request: Request, auth: AuthRuntime, handle: str) -> dict[str, object]:
    with auth.sessions.begin() as db:
        user, session = identity(request, auth, db)
        storage.cleanup(db)
        row = storage.owned(db, handle, user, session)
        state = row.state
        if state in ("claimed", "verifying") and row.created_at + 150 <= now():
            state = "execution_uncertain"
        return {"state": state}


def cancel(request: Request, auth: AuthRuntime, handle: str) -> dict[str, object]:
    with auth.sessions.begin() as db:
        user, session = identity(request, auth, db)
        user_lock(db, user)
        row = storage.owned(db, handle, user, session)
        if row.state != "pending":
            raise EditError("proposal_used")
        row.state, row.payload = "cancelled", None
        audit(db, "write_proposal_cancelled", user_id=user)
    return {"state": "cancelled"}


def approve(
    request: Request,
    auth: AuthRuntime,
    handle: str,
    supplied: str,
    progress: Callable[[str], None] = lambda _: None,
) -> dict[str, object]:
    # Claim and durable fence are committed even if the process crashes next.
    with auth.sessions.begin() as db:
        user, session = identity(request, auth, db)
        user_lock(db, user)
        proposal = storage.claim(db, handle, user, session, supplied)
    progress("checking")
    started = monotonic()
    dispatched = False
    state: State = "write_failed"
    failure: EditError | None = None
    try:
        provider = client(request, auth)  # Refresh precedes final authorization locks.
        baseline = provider.evidence(proposal.binding.context)
        with auth.sessions.begin() as db:
            binding = authority(request, auth, db, proposal.binding.context, lock=True)
            require_current(proposal, binding, baseline, now())
            if monotonic() - started > 25:
                raise EditError("model_changed")
            fence = db.get(WriteFence, binding.workspace_key)
            if (
                fence is None
                or fence.record_id != handle
                or not auth.settings.forge_cad_writes_enabled
            ):
                raise EditError("workspace_fenced")
            # Final head while user/session/grant are locked; provider guard closes
            # collaborator race. Dispatch bookkeeping already durable via claim.
            if provider.head(binding.context) != baseline.microversion:
                raise EditError("model_changed")
            pause = auth.settings.forge_cad_write_conformance_pause_seconds
            if pause:
                if auth.settings.environment != "development":
                    raise EditError("invalid_request", 400)
                progress("conformance_wait")
                sleep(pause)
                if now() >= proposal.expires_at:
                    raise EditError("proposal_expired")
            audit(db, "write_dispatch_started", user_id=user)
            progress("executing")
            dispatched = True
            marker = provider.suppress_terminal_fillet(proposal)
            audit(db, "write_provider_acknowledged", user_id=user)
            row = db.get(WriteRecord, handle)
            if row is not None:
                row.state = "verifying"
        progress("verifying")
        after = provider.evidence(proposal.binding.context, after=True)
        if (
            after.serialization != baseline.serialization
            or after.library != baseline.library
            or after.feature_id != baseline.feature_id
            or after.microversion != marker
            or after.definitions != baseline.definitions
            or after.parent_suppression_evidence != baseline.parent_suppression_evidence
            or after.configured_suppression_evidence
            != baseline.configured_suppression_evidence
            or monotonic() - started > 30
        ):
            raise EditError("verification_failed")
        with auth.sessions() as db:
            if (
                authority(request, auth, db, proposal.binding.context)
                != proposal.binding
            ):
                raise EditError("session_expired", 401)
        state = "verified_success"
    except EditError as error:
        failure = error
        state = (
            "execution_uncertain"
            if dispatched
            else "rejected_stale"
            if error.code in ("model_changed", "context_changed")
            else "write_failed"
        )
    except Exception:
        # Never include DB/provider exceptions or reset a consumed claim. Crashes
        # before this handler leave a durable fence for status/reconciliation.
        state = "execution_uncertain" if dispatched else "write_failed"
        failure = EditError(
            "execution_uncertain" if dispatched else "onshape_unavailable", 503
        )
    with auth.sessions.begin() as db:
        storage.finish(
            db,
            proposal,
            state,
            safe_to_release=not dispatched or state == "verified_success",
        )
    if failure and not dispatched:
        raise failure
    return {"state": state}


def reconcile(request: Request, auth: AuthRuntime, handle: str) -> dict[str, object]:
    # Never retries a mutation. No automatic success attribution after lost ack.
    provider = client(request, auth)
    with auth.sessions() as db:
        user, session = identity(request, auth, db)
        row = storage.owned(db, handle, user, session)
        if row.state not in (
            "execution_uncertain",
            "unverified_result",
            "recovery_required",
        ):
            raise EditError("proposal_used")
        proposal = storage.decode(row)
        binding = authority(request, auth, db, proposal.binding.context)
    # Unknown, unchanged or mismatched state never releases an uncertainty
    # fence. Re-authenticate below before returning recovery guidance.
    with suppress(EditError):
        capture(request, binding, provider, after=True)
    with auth.sessions.begin() as db:
        if authority(request, auth, db, binding.context) != binding:
            raise EditError("context_changed")
        row = storage.owned(db, handle, user, session)
        row.state = "recovery_required"
        audit(db, "write_reconciliation_required", user_id=user)
    return {"state": "recovery_required"}
