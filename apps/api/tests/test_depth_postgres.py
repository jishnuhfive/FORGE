"""Random isolated PostgreSQL schemas; every provider transport is synthetic."""

import hashlib
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from typing import Any

import pytest
from conftest import Harness
from depth_support import DepthCase, seed_depth
from sqlalchemy import Engine, event, select, text
from test_modify_plan import PlanProvider, request_for
from test_modify_plan_postgres import use_postgres
from test_postgres import postgres as postgres
from test_safe_edit import running

from forge_api.auth.security import digest
from forge_api.cad_edits import (
    depth_recovery,
    depth_release,
    plan_recovery,
    plan_storage,
    service,
    storage,
)
from forge_api.cad_edits.depth_contracts import DepthRecoveryDenied
from forge_api.cad_edits.domain import EditError
from forge_api.db.coordination import user_lock
from forge_api.db.models import (
    AuditEvent,
    OnshapeAuthorization,
    Session,
    WriteFence,
    WriteRecord,
    now,
)


def outcome(c: DepthCase) -> str:
    try:
        c.recover()
        return "closed"
    except DepthRecoveryDenied:
        return "denied"


def assert_closed(c: DepthCase) -> None:
    with c.harness.runtime.sessions() as db:
        row = db.get(WriteRecord, c.reference.historical.record_id)
        assert row and row.state == "operator_recovered" and row.purge_at > now()
        assert db.scalar(select(WriteFence)) is None
        assert (
            len(
                list(
                    db.scalars(
                        select(AuditEvent).where(
                            AuditEvent.kind == "write_depth_operator_recovery"
                        )
                    )
                )
            )
            == 1
        )
    assert c.provider.writes == 0
    assert len(c.provider.calls) == 8


def test_duplicate_recovery_has_one_atomic_closure(
    postgres: Engine, harness: Harness
) -> None:
    use_postgres(harness, postgres)
    provider = PlanProvider()
    with running(harness, provider):
        c = seed_depth(harness, provider)
        barrier = Barrier(2)

        def attempt() -> str:
            barrier.wait(timeout=5)
            return outcome(c)

        with ThreadPoolExecutor(max_workers=2) as pool:
            a, b = pool.submit(attempt), pool.submit(attempt)
            assert sorted((a.result(timeout=10), b.result(timeout=10))) == [
                "closed",
                "denied",
            ]
        assert len(provider.calls) == 8
        assert_closed(c)


@pytest.mark.parametrize(
    "competitor", ["cleanup", "admission", "claim", "rotate", "disconnect", "browser"]
)
def test_capture_serializes_same_user_activity_without_global_barrier(
    postgres: Engine, harness: Harness, competitor: str
) -> None:
    use_postgres(harness, postgres)
    provider = PlanProvider()
    with running(harness, provider):
        c = seed_depth(harness, provider)
        entered, proceed, competing = Event(), Event(), Event()
        handler = provider.handle

        def gated(request: Any) -> Any:
            if not entered.is_set():
                entered.set()
                assert proceed.wait(timeout=5)
            return handler(request)

        provider.handle = gated  # type: ignore[method-assign]

        def other() -> str:
            if competitor == "browser":
                # An active replacement session gets no ownership of old handle.
                raw = "N" * 43
                with harness.runtime.sessions.begin() as db:
                    db.add(
                        Session(
                            token_hash=digest(raw),
                            user_id=c.reference.independent.user,
                            expires_at=now() + 10000,
                        )
                    )
                harness.client.cookies.clear()
                harness.client.cookies.set(harness.runtime.settings.session_cookie, raw)
                competing.set()
                try:
                    plan_recovery.reconcile(
                        request_for(harness),
                        harness.runtime,
                        c.reference.historical.record_id,
                    )
                except EditError:
                    return "denied"
                raise AssertionError("new browser inherited authority")
            with harness.runtime.sessions.begin() as db:
                competing.set()
                if competitor == "cleanup":
                    storage.cleanup(db)
                    return "cleaned"
                user_lock(db, c.reference.independent.user)
                if competitor in ("rotate", "disconnect"):
                    grant = db.get(
                        OnshapeAuthorization,
                        c.reference.independent.user,
                        with_for_update=True,
                    )
                    assert grant
                    grant.generation = "synthetic-after-closure"
                    if competitor == "disconnect":
                        grant.status = "disconnected"
                    return "rotated"
                if competitor == "claim":
                    try:
                        h = c.reference.historical
                        plan_storage.claim(
                            db,
                            h.record_id,
                            c.reference.independent.user,
                            h.binding.session,
                            h.plan_digest,
                        )
                    except EditError:
                        return "denied"
                    raise AssertionError("consumed approval replayed")
                storage.unfenced(db, c.reference.historical.binding)
                service.admit(db, c.reference.historical.binding)
                return "admitted_after_closure"

        with ThreadPoolExecutor(max_workers=2) as pool:
            recovery = pool.submit(outcome, c)
            assert entered.wait(timeout=5)
            with harness.runtime.sessions.begin() as probe:
                # Lock scope is the user; no table barrier and no global lock.
                assert (
                    probe.scalar(
                        text(
                            "SELECT count(*) FROM pg_locks "
                            "WHERE mode = 'ShareRowExclusiveLock'"
                        )
                    )
                    == 0
                )
                assert (
                    probe.scalar(text("SELECT pg_try_advisory_xact_lock(891234567890)"))
                    is True
                )
                lock_key = int.from_bytes(
                    hashlib.sha256(
                        ("forge.user.v1:" + c.reference.independent.user).encode()
                    ).digest()[:8],
                    "big",
                    signed=True,
                )
                assert (
                    probe.scalar(
                        text("SELECT pg_try_advisory_xact_lock(:key)"),
                        {"key": lock_key},
                    )
                    is False
                )
            competing_future = pool.submit(other)
            assert competing.wait(timeout=5)
            # Same-user operations wait while capture holds the user lock.
            if competitor in ("rotate", "disconnect", "claim", "admission"):
                assert not competing_future.done()
            proceed.set()
            assert recovery.result(timeout=10) == "closed"
            assert competing_future.result(timeout=10) in (
                "cleaned",
                "rotated",
                "denied",
                "admitted_after_closure",
            )
        assert_closed(c)


@pytest.mark.parametrize("change", ["rotate", "disconnect"])
def test_grant_change_winning_lock_denies_recovery_without_reads(
    postgres: Engine, harness: Harness, change: str
) -> None:
    use_postgres(harness, postgres)
    provider = PlanProvider()
    with running(harness, provider):
        c = seed_depth(harness, provider)
        with harness.runtime.sessions.begin() as db:
            user_lock(db, c.reference.independent.user)
            grant = db.get(
                OnshapeAuthorization, c.reference.independent.user, with_for_update=True
            )
            assert grant
            grant.generation = "synthetic-winning-rotation"
            if change == "disconnect":
                grant.status = "disconnected"
        before = c.snapshot()
        assert outcome(c) == "denied"
        assert c.snapshot() == before and provider.calls == []


def test_cleanup_first_preserves_fenced_payload_for_later_recovery(
    postgres: Engine, harness: Harness
) -> None:
    use_postgres(harness, postgres)
    provider = PlanProvider()
    with running(harness, provider):
        c = seed_depth(harness, provider)
        before = c.snapshot()
        with harness.runtime.sessions.begin() as db:
            storage.cleanup(db)
        assert c.snapshot() == before
        assert outcome(c) == "closed"
        assert_closed(c)


@pytest.mark.parametrize(
    "stage", ["before_update", "after_update", "after_delete", "audit", "commit"]
)
def test_postgres_failure_is_atomic(
    postgres: Engine, harness: Harness, stage: str
) -> None:
    use_postgres(harness, postgres)
    provider = PlanProvider()
    with running(harness, provider):
        c = seed_depth(harness, provider)
        before = c.snapshot()

        def fail_sql(
            conn: Any,
            cursor: Any,
            statement: str,
            parameters: Any,
            context: Any,
            many: bool,
        ) -> None:
            matches = (
                (
                    stage in ("before_update", "after_update")
                    and statement.startswith("UPDATE write_records SET state=")
                )
                or (
                    stage == "after_delete"
                    and statement.startswith("DELETE FROM write_fences")
                )
                or (
                    stage == "audit"
                    and statement.startswith("INSERT INTO audit_events")
                )
            )
            if matches:
                raise RuntimeError("synthetic atomicity failure")

        def fail_commit(*args: Any) -> None:
            raise RuntimeError("synthetic atomicity failure")

        hook = (
            "before_cursor_execute"
            if stage == "before_update"
            else "after_cursor_execute"
        )
        event.listen(postgres, hook, fail_sql)
        if stage == "commit":
            event.listen(postgres, "commit", fail_commit)
        try:
            with pytest.raises(RuntimeError, match="atomicity failure"):
                c.recover()
        finally:
            event.remove(postgres, hook, fail_sql)
            if stage == "commit":
                event.remove(postgres, "commit", fail_commit)
        assert c.snapshot() == before and provider.writes == 0


def test_database_idle_timeout_during_capture_keeps_fence(
    postgres: Engine, harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_postgres(harness, postgres)
    provider = PlanProvider()
    with running(harness, provider):
        c = seed_depth(harness, provider)
        before = c.snapshot()
        lock = depth_release.lock_depth_record

        def shortened(*args: Any, **kwargs: Any) -> Any:
            result = lock(*args, **kwargs)
            args[0].execute(
                text("SET LOCAL idle_in_transaction_session_timeout = '50ms'")
            )
            return result

        handle = provider.handle

        def slow(request: Any) -> Any:
            if not provider.calls:
                Event().wait(0.15)
            return handle(request)

        monkeypatch.setattr(depth_recovery, "lock_depth_record", shortened)
        monkeypatch.setattr(provider, "handle", slow)
        assert outcome(c) == "denied"
        assert c.snapshot() == before and provider.writes == 0
