"""Only a disposable PostgreSQL service/random schemas; all CAD is synthetic."""

import hashlib
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from typing import Any

import httpx2 as httpx
import pytest
from conftest import Harness
from legacy_support import LegacyCase, saved, seed_legacy
from sqlalchemy import Engine, event, select, text
from test_modify_plan import PlanProvider, request_for
from test_modify_plan_postgres import use_postgres
from test_postgres import postgres as postgres

from forge_api.auth.security import digest
from forge_api.cad_edits import (
    legacy_enrollment,
    legacy_recovery,
    plan_recovery,
    plan_storage,
    service,
    storage,
)
from forge_api.cad_edits.domain import EditError
from forge_api.cad_edits.legacy_contracts import LegacyRecoveryDenied
from forge_api.cad_edits.retained_contracts import (
    IndependentOperationEvidence,
    OperatorReview,
    PreservedHandle,
    RetainedRecoveryDenied,
    build_retained_reference,
)
from forge_api.cad_edits.retained_recovery import recover_retained_record
from forge_api.db.coordination import user_lock
from forge_api.db.models import (
    AuditEvent,
    OnshapeAuthorization,
    Session,
    WriteFence,
    WriteRecord,
    now,
)


def outcome(case: LegacyCase) -> str:
    try:
        case.recover()
        return "closed"
    except LegacyRecoveryDenied:
        return "denied"


def assert_closed(case: LegacyCase, *, legacy: bool = True) -> None:
    with case.harness.runtime.sessions() as db:
        row = db.get(WriteRecord, case.enrollment.record_id)
        assert row and row.state == "operator_recovered"
        assert db.scalar(select(WriteFence)) is None
        audits = list(
            db.scalars(
                select(AuditEvent).where(
                    AuditEvent.kind.in_(
                        (
                            "write_legacy_retained_retirement",
                            "write_retained_operator_recovery",
                        )
                    )
                )
            )
        )
        assert len(audits) == 1 and audits[0].outcome == "local_only"
        if legacy:
            assert audits[0].kind == "write_legacy_retained_retirement"
    assert len(case.provider.calls) == 5 and case.provider.writes == 0


def test_duplicate_legacy_invocation_has_exactly_one_winner(
    postgres: Engine, harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_postgres(harness, postgres)
    c = seed_legacy(harness, PlanProvider(), monkeypatch)
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
    assert_closed(c)


def test_normal_v1_and_legacy_share_exclusion_without_provenance_fallback(
    postgres: Engine, harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_postgres(harness, postgres)
    c = seed_legacy(harness, PlanProvider(), monkeypatch)
    e = c.enrollment
    # An invented independent receipt exists ONLY in this synthetic V1 race.
    reference = build_retained_reference(
        IndependentOperationEvidence(
            source="previously_preserved_operation_receipt",
            receipt_digest="a" * 64,
            user=e.binding.user,
            context=e.binding.context,
            operation="SET_UNSUPPRESSED",
            desired_suppressed=False,
            anchor=PreservedHandle(kind="preserved_record_handle", value="B" * 43),
        ),
        saved(c),
        OperatorReview(
            operator_authorized=True,
            independent_receipt_reviewed=True,
            writers_drained=True,
            upstream_settled=True,
            stack=e.stack,
            company_id=None,
            current_generation=e.current_generation,
        ),
    )
    barrier = Barrier(2)

    def legacy() -> str:
        barrier.wait(timeout=5)
        return outcome(c)

    def v1() -> str:
        barrier.wait(timeout=5)
        try:
            recover_retained_record(
                harness.runtime.sessions,
                harness.runtime.settings,
                harness.runtime.tokens,
                reference,
                transport=httpx.MockTransport(c.provider.handle),
            )
            return "closed"
        except RetainedRecoveryDenied:
            return "denied"

    with ThreadPoolExecutor(max_workers=2) as pool:
        a, b = pool.submit(legacy), pool.submit(v1)
        assert sorted((a.result(timeout=10), b.result(timeout=10))) == [
            "closed",
            "denied",
        ]
    assert_closed(c, legacy=False)


@pytest.mark.parametrize(
    "competitor", ["cleanup", "admission", "claim", "rotate", "disconnect", "browser"]
)
def test_scoped_lock_excludes_competing_same_user_work(
    postgres: Engine, harness: Harness, monkeypatch: pytest.MonkeyPatch, competitor: str
) -> None:
    use_postgres(harness, postgres)
    c = seed_legacy(harness, PlanProvider(), monkeypatch)
    entered, proceed, competing = Event(), Event(), Event()
    handler = c.provider.handle

    def gated(request: Any) -> Any:
        if not entered.is_set():
            entered.set()
            assert proceed.wait(timeout=5)
        return handler(request)

    monkeypatch.setattr(c.provider, "handle", gated)

    def other() -> str:
        e = c.enrollment
        if competitor == "browser":
            raw = "N" * 43
            with harness.runtime.sessions.begin() as db:
                db.add(
                    Session(
                        token_hash=digest(raw),
                        user_id=e.binding.user,
                        expires_at=now() + 10000,
                    )
                )
            harness.client.cookies.clear()
            harness.client.cookies.set(harness.runtime.settings.session_cookie, raw)
            competing.set()
            try:
                plan_recovery.reconcile(
                    request_for(harness), harness.runtime, e.record_id
                )
            except EditError:
                return "denied"
            raise AssertionError("browser inherited authority")
        with harness.runtime.sessions.begin() as db:
            competing.set()
            if competitor == "cleanup":
                storage.cleanup(db)
                return "cleaned"
            user_lock(db, e.binding.user)
            if competitor in ("rotate", "disconnect"):
                grant = db.get(
                    OnshapeAuthorization, e.binding.user, with_for_update=True
                )
                assert grant
                grant.generation = "synthetic-after-retirement"
                if competitor == "disconnect":
                    grant.status = "disconnected"
                return "rotated"
            if competitor == "claim":
                try:
                    plan_storage.claim(
                        db,
                        e.record_id,
                        e.binding.user,
                        e.binding.session,
                        e.plan_digest,
                    )
                except EditError:
                    return "denied"
                raise AssertionError("consumed approval replayed")
            storage.unfenced(db, e.binding)
            service.admit(db, e.binding)
            return "admitted_after_commit"

    with ThreadPoolExecutor(max_workers=2) as pool:
        recovery = pool.submit(outcome, c)
        assert entered.wait(timeout=5)
        with harness.runtime.sessions.begin() as probe:
            assert (
                probe.scalar(
                    text(
                        "SELECT count(*) FROM pg_locks "
                        "WHERE mode = 'ShareRowExclusiveLock'"
                    )
                )
                == 0
            )
            key = int.from_bytes(
                hashlib.sha256(
                    ("forge.user.v1:" + c.enrollment.binding.user).encode()
                ).digest()[:8],
                "big",
                signed=True,
            )
            assert (
                probe.scalar(
                    text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": key}
                )
                is False
            )
            assert (
                probe.scalar(text("SELECT pg_try_advisory_xact_lock(891234567890)"))
                is True
            )
        future = pool.submit(other)
        assert competing.wait(timeout=5)
        if competitor in ("admission", "claim", "rotate", "disconnect"):
            assert not future.done()
        proceed.set()
        assert recovery.result(timeout=10) == "closed"
        assert future.result(timeout=10) in (
            "cleaned",
            "rotated",
            "denied",
            "admitted_after_commit",
        )
    assert_closed(c)


@pytest.mark.parametrize("change", ["rotate", "disconnect"])
def test_grant_winning_lock_denies_before_capture(
    postgres: Engine, harness: Harness, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    use_postgres(harness, postgres)
    c = seed_legacy(harness, PlanProvider(), monkeypatch)
    with harness.runtime.sessions.begin() as db:
        user_lock(db, c.enrollment.binding.user)
        grant = db.get(
            OnshapeAuthorization, c.enrollment.binding.user, with_for_update=True
        )
        assert grant
        grant.generation = "synthetic-changed-before-retirement"
        if change == "disconnect":
            grant.status = "disconnected"
    before = c.snapshot()
    assert outcome(c) == "denied" and c.snapshot() == before and not c.provider.calls


def test_cleanup_before_retirement_preserves_evidence(
    postgres: Engine, harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_postgres(harness, postgres)
    c = seed_legacy(harness, PlanProvider(), monkeypatch)
    before = c.snapshot()
    with harness.runtime.sessions.begin() as db:
        storage.cleanup(db)
    assert c.snapshot() == before
    assert outcome(c) == "closed"
    assert_closed(c)


@pytest.mark.parametrize(
    "stage", ["before_update", "after_update", "after_delete", "audit", "commit"]
)
def test_postgres_atomic_failures_preserve_original_state(
    postgres: Engine, harness: Harness, monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    use_postgres(harness, postgres)
    c = seed_legacy(harness, PlanProvider(), monkeypatch)
    before = c.snapshot()

    def fail_sql(
        conn: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        many: bool,
    ) -> None:
        if (
            (
                stage in ("before_update", "after_update")
                and statement.startswith("UPDATE write_records SET state=")
            )
            or (
                stage == "after_delete"
                and statement.startswith("DELETE FROM write_fences")
            )
            or (stage == "audit" and statement.startswith("INSERT INTO audit_events"))
        ):
            raise RuntimeError("synthetic atomicity failure")

    def fail_commit(*args: Any) -> None:
        raise RuntimeError("synthetic atomicity failure")

    hook = (
        "before_cursor_execute" if stage == "before_update" else "after_cursor_execute"
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
    assert c.snapshot() == before and c.provider.writes == 0


def test_postgres_idle_timeout_during_capture_rolls_back(
    postgres: Engine, harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_postgres(harness, postgres)
    c = seed_legacy(harness, PlanProvider(), monkeypatch)
    before = c.snapshot()
    validate = legacy_enrollment.validate_locked

    def short_timeout(*args: Any, **kwargs: Any) -> Any:
        result = validate(*args, **kwargs)
        args[0].execute(text("SET LOCAL idle_in_transaction_session_timeout = '50ms'"))
        return result

    handler = c.provider.handle

    def slow(request: Any) -> Any:
        if not c.provider.calls:
            Event().wait(0.15)
        return handler(request)

    monkeypatch.setattr(legacy_recovery, "validate_locked", short_timeout)
    monkeypatch.setattr(c.provider, "handle", slow)
    assert outcome(c) == "denied"
    assert c.snapshot() == before
