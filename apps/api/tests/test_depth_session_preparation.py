"""Exact historical-session preparation on synthetic incidents only."""

import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from typing import Any

import httpx2 as httpx
import pytest
from conftest import Harness
from server_depth_support import ServerCase, review, seed_server
from sqlalchemy import Engine, event, select
from sqlalchemy.orm import SessionTransaction
from test_modify_plan import PlanProvider
from test_modify_plan_postgres import use_postgres
from test_postgres import postgres as postgres
from test_safe_edit import running
from test_server_depth_recovery import case as case

from forge_api.cad_edits import depth_recovery, plan_storage
from forge_api.cad_edits.depth_contracts import DepthRecoveryDenied
from forge_api.cad_edits.depth_recovery import (
    inspect_development_depth_session as inspect_session,
)
from forge_api.cad_edits.depth_recovery import (
    revoke_development_depth_session as revoke_session,
)
from forge_api.cad_edits.domain import fingerprint
from forge_api.db.models import (
    AuditEvent,
    OnshapeAuthorization,
    Session,
    User,
    WriteFence,
    WriteRecord,
    now,
)

PHRASE = "REVOKE HISTORICAL SESSION"


def activate(c: ServerCase) -> None:
    with c.harness.runtime.sessions.begin() as db:
        original = db.get(Session, c.reference.historical.binding.session)
        assert original
        original.expires_at = now() + 3600
        original.revoked_at = None
        original.last_seen_at = now()


def session_state(c: ServerCase) -> tuple[tuple[Any, ...], tuple[Any, ...]]:
    with c.harness.runtime.sessions() as db:
        sessions = tuple(
            (s.token_hash, s.user_id, s.created_at, s.expires_at, s.revoked_at)
            for s in db.scalars(select(Session).order_by(Session.token_hash))
        )
        audits = tuple(
            (a.kind, a.outcome, a.user_id)
            for a in db.scalars(
                select(AuditEvent).where(AuditEvent.kind == "session_revoked")
            )
        )
        return sessions, audits


def test_exact_revocation_preserves_current_session_grant_cache_and_incident(
    case: ServerCase,
) -> None:
    activate(case)
    r = review(case.harness)
    ticket = inspect_session(case.harness.runtime, r)
    assert ticket.active
    before = case.snapshot()
    sessions_before, _ = session_state(case)
    with case.harness.runtime.sessions() as db:
        grant = db.get(OnshapeAuthorization, case.reference.approval.user)
        assert grant
        grant_before = (grant.status, grant.generation, grant.encrypted_refresh_token)
    credential = case.harness.runtime.tokens.cached_read_credential(
        case.reference.approval.user,
        case.reference.review.current_generation,
        "OAuth2Read",
        capture_seconds=30,
    )
    after = revoke_session(case.harness.runtime, r, ticket, PHRASE)
    assert not after.active and after.reference == ticket.reference
    sessions_after, audits = session_state(case)
    assert len(audits) == 1 and audits[0][0:2] == ("session_revoked", "local_only")
    for old, new in zip(sessions_before, sessions_after, strict=True):
        if old[0] == case.reference.historical.binding.session:
            assert old[:-1] == new[:-1] and new[-1] is not None
        else:
            assert old == new
    with case.harness.runtime.sessions() as db:
        grant = db.get(OnshapeAuthorization, case.reference.approval.user)
        assert grant
        grant_after = (grant.status, grant.generation, grant.encrypted_refresh_token)
        assert grant_after == grant_before
    assert credential == case.harness.runtime.tokens.cached_read_credential(
        case.reference.approval.user,
        case.reference.review.current_generation,
        "OAuth2Read",
        capture_seconds=30,
    )
    assert case.snapshot() == before and not case.provider.calls
    assert revoke_session(case.harness.runtime, r, ticket, PHRASE) == after
    assert len(session_state(case)[1]) == 1


@pytest.mark.parametrize(
    "change",
    [
        "session_user",
        "missing_session",
        "missing_fence",
        "fence_user",
        "fence_record",
        "multiple",
        "nondepth",
        "wrong_type",
        "digest",
        "payload",
        "state",
        "production",
        "writes",
        "disposable",
        "drain",
        "settlement",
        "authorization",
    ],
)
def test_invalid_incident_cannot_revoke(case: ServerCase, change: str) -> None:
    activate(case)
    r = review(case.harness)
    ticket = inspect_session(case.harness.runtime, r)
    with case.harness.runtime.sessions.begin() as db:
        original = db.get(Session, case.reference.historical.binding.session)
        row = db.get(WriteRecord, case.reference.historical.record_id)
        fence = db.scalar(select(WriteFence))
        assert original and row and fence
        if change in ("session_user", "fence_user"):
            other = User(
                stack=r.stack,
                onshape_user_id="synthetic-other-revoke",
                display_name="Other",
            )
            db.add(other)
            db.flush()
            if change == "session_user":
                original.user_id = other.id
            else:
                fence.user_id = other.id
        elif change == "missing_session":
            db.delete(original)
        elif change == "missing_fence":
            db.delete(fence)
        elif change == "fence_record":
            fence.record_id = "f" * 43
        elif change == "multiple":
            db.add(
                WriteFence(
                    user_id="synthetic-other",
                    workspace_key="f" * 64,
                    record_id="f" * 43,
                )
            )
        elif change in ("nondepth", "wrong_type"):
            saved = plan_storage.load(row)
            data = saved.model_dump(mode="json")
            if change == "nondepth":
                data["plan"]["operations"][0]["operation"]["type"] = "SET_FILLET_RADIUS"
                data["plan"]["operations"][0]["preview"]["type"] = "SET_FILLET_RADIUS"
            else:
                data["plan"]["operations"][0]["target"]["feature_type"] = "fillet"
            from forge_api.cad_edits.plans import StoredPlan

            saved = StoredPlan.model_validate_json(json.dumps(data))
            row.payload = saved.model_dump_json()
            row.digest = fingerprint(saved.plan.model_dump(mode="json"))
        elif change == "digest":
            row.digest = "f" * 64
        elif change == "payload":
            row.payload = "{}"
        elif change == "state":
            row.state = "claimed"
    if change == "production":
        case.harness.runtime.settings.environment = "production"
    elif change == "writes":
        case.harness.runtime.settings.forge_cad_writes_enabled = True
    elif change in ("disposable", "drain", "settlement", "authorization"):
        field = {
            "disposable": "disposable_fixture",
            "drain": "writers_drained",
            "settlement": "upstream_settled",
            "authorization": "operator_authorized",
        }[change]
        r = r.model_copy(update={field: False})
    before = case.snapshot(), session_state(case)
    with pytest.raises(DepthRecoveryDenied):
        revoke_session(case.harness.runtime, r, ticket, PHRASE)
    assert (case.snapshot(), session_state(case)) == before and not case.provider.calls


@pytest.mark.parametrize("mode", ["revoked", "expired"])
def test_already_inactive_is_noop(case: ServerCase, mode: str) -> None:
    activate(case)
    with case.harness.runtime.sessions.begin() as db:
        original = db.get(Session, case.reference.historical.binding.session)
        assert original
        if mode == "revoked":
            original.revoked_at = now()
        else:
            original.expires_at = now() - 1
    r = review(case.harness)
    ticket = inspect_session(case.harness.runtime, r)
    assert not ticket.active
    before = case.snapshot(), session_state(case)
    assert not revoke_session(case.harness.runtime, r, ticket, PHRASE).active
    assert (case.snapshot(), session_state(case)) == before


def test_confirmation_cannot_be_skipped(case: ServerCase) -> None:
    activate(case)
    r = review(case.harness)
    ticket = inspect_session(case.harness.runtime, r)
    before = session_state(case)
    with pytest.raises(DepthRecoveryDenied, match="confirmation_required"):
        revoke_session(case.harness.runtime, r, ticket, "")
    assert session_state(case) == before


@pytest.mark.parametrize("stage", ["audit", "commit"])
def test_failure_rolls_back_exact_revocation(
    case: ServerCase, monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    activate(case)
    r = review(case.harness)
    ticket = inspect_session(case.harness.runtime, r)
    before = case.snapshot(), session_state(case)

    def fail(*_: Any, **__: Any) -> None:
        raise RuntimeError("synthetic failure")

    engine = case.harness.runtime.sessions.kw["bind"]
    if stage == "audit":
        monkeypatch.setattr(depth_recovery, "audit", fail)
    else:
        event.listen(engine, "commit", fail)
    try:
        with pytest.raises(DepthRecoveryDenied, match="unconfirmed_no_retry"):
            revoke_session(case.harness.runtime, r, ticket, PHRASE)
    finally:
        if stage == "commit":
            event.remove(engine, "commit", fail)
    assert (case.snapshot(), session_state(case)) == before


def test_lost_commit_reply_is_not_retried(
    case: ServerCase, monkeypatch: pytest.MonkeyPatch
) -> None:
    activate(case)
    r = review(case.harness)
    ticket = inspect_session(case.harness.runtime, r)
    original = SessionTransaction.__exit__
    raised = False

    def lost(self: Any, *a: Any, **kw: Any) -> Any:
        nonlocal raised
        value = original(self, *a, **kw)
        if self.parent is None and not raised:
            raised = True
            raise RuntimeError("synthetic lost reply")
        return value

    with monkeypatch.context() as patch:
        patch.setattr(SessionTransaction, "__exit__", lost)
        with pytest.raises(DepthRecoveryDenied, match="unconfirmed_no_retry"):
            revoke_session(case.harness.runtime, r, ticket, PHRASE)
    assert not inspect_session(case.harness.runtime, r).active
    assert len(session_state(case)[1]) == 1
    assert not case.provider.calls


def test_recovery_uses_same_incident_after_revocation(case: ServerCase) -> None:
    activate(case)
    r = review(case.harness)
    ticket = inspect_session(case.harness.runtime, r)
    ticket = revoke_session(case.harness.runtime, r, ticket, PHRASE)
    result = depth_recovery.recover_development_depth_incident(
        case.harness.runtime,
        r,
        incident=ticket,
        transport=httpx.MockTransport(case.provider.handle),
    )
    assert result.original_execution_outcome == "execution_uncertain"
    assert case.snapshot()[1] == () and len(case.provider.calls) == 8


def test_postgres_duplicate_revocation_is_one_transition(
    postgres: Engine, harness: Harness
) -> None:
    use_postgres(harness, postgres)
    provider = PlanProvider()
    with running(harness, provider):
        c = seed_server(harness, provider)
        activate(c)
        r = review(harness)
        ticket = inspect_session(harness.runtime, r)
        barrier = Barrier(2)

        def revoke() -> bool:
            barrier.wait(timeout=5)
            return revoke_session(harness.runtime, r, ticket, PHRASE).active

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: revoke(), range(2)))
        assert results == [False, False] and len(session_state(c)[1]) == 1
        assert not provider.calls


@pytest.mark.parametrize("stage", ["revoke", "recover"])
def test_substituted_incident_context_denies_before_action(
    case: ServerCase, stage: str
) -> None:
    from dataclasses import replace

    activate(case)
    r = review(case.harness)
    ticket = inspect_session(case.harness.runtime, r)
    ticket = replace(
        ticket,
        reference=ticket.reference.model_copy(
            update={
                "historical": ticket.reference.historical.model_copy(
                    update={"payload_fingerprint": "f" * 64}
                )
            }
        ),
    )
    before = case.snapshot(), session_state(case)
    with pytest.raises(DepthRecoveryDenied, match="reviewed_incident_changed"):
        if stage == "revoke":
            revoke_session(case.harness.runtime, r, ticket, PHRASE)
        else:
            depth_recovery.recover_development_depth_incident(
                case.harness.runtime,
                r,
                incident=ticket,
                transport=httpx.MockTransport(case.provider.handle),
            )
    assert (case.snapshot(), session_state(case)) == before and not case.provider.calls
