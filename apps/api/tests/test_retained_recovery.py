"""Synthetic retained administrative recovery, never a live operator invocation."""

from collections.abc import Iterator
from typing import Any

import pytest
from conftest import Harness
from pydantic import ValidationError
from retained_support import RetainedCase, seed_retained
from sqlalchemy import event, select
from sqlalchemy.orm import SessionTransaction
from test_modify_plan import PlanProvider
from test_safe_edit import running

from forge_api.cad_edits import (
    dev_recovery,
    plan_storage,
    retained_recovery,
    retained_release,
    storage,
)
from forge_api.cad_edits.domain import EditError, fingerprint
from forge_api.cad_edits.plans import StoredPlan
from forge_api.cad_edits.retained_contracts import (
    AdministrativeRecoveryResult,
    IndependentOperationEvidence,
    PreservedApproval,
    RetainedRecoveryDenied,
    build_retained_reference,
)
from forge_api.db.models import (
    AuditEvent,
    OnshapeAuthorization,
    Session,
    User,
    WriteFence,
    WriteRecord,
    now,
)
from forge_api.integrations.onshape.retained_reader import RetainedEvidenceReader


@pytest.fixture
def case(harness: Harness) -> Iterator[RetainedCase]:
    provider = PlanProvider()
    with running(harness, provider):
        yield seed_retained(harness, provider)


@pytest.mark.parametrize("unsuppress", [False, True])
def test_exact_closure_is_redacted_consumed_and_not_execution_success(
    harness: Harness, unsuppress: bool
) -> None:
    provider = PlanProvider()
    with running(harness, provider):
        c = seed_retained(harness, provider, unsuppress=unsuppress)
        ref = c.reference
        before = c.snapshot()
        result = c.recover()
        assert isinstance(result, AdministrativeRecoveryResult)
        assert result.original_execution_outcome == "execution_uncertain"
        assert result.state == "operator_recovered"
        assert len(provider.calls) == 5 and all(
            r.method == "GET" for r in provider.calls
        )
        assert provider.writes == 0
        with harness.runtime.sessions.begin() as db:
            row = db.get(WriteRecord, ref.historical.record_id)
            assert row and row.payload == result.model_dump_json()
            assert row.purge_at == result.recovered_at + 900
            assert row.session_hash == ref.historical.binding.session
            assert row.digest == ref.historical.plan_digest
            assert db.scalar(select(WriteFence)) is None
            assert "baseline" not in row.payload and "binding" not in row.payload
            for read in (plan_storage.load, plan_storage.result):
                with pytest.raises(EditError, match="proposal_used"):
                    read(row)
            with pytest.raises(EditError, match="proposal_used"):
                plan_storage.claim(
                    db, row.id, row.user_id, row.session_hash, row.digest
                )
            events = list(
                db.scalars(
                    select(AuditEvent).where(
                        AuditEvent.kind == "write_retained_operator_recovery"
                    )
                )
            )
            assert len(events) == 1 and events[0].outcome == "local_only"
            original = db.get(Session, ref.historical.binding.session)
            grant = db.get(OnshapeAuthorization, ref.independent.user)
            assert original and original.expires_at < now()
            assert grant and grant.generation == ref.review.current_generation
        committed = c.snapshot()
        with pytest.raises(RetainedRecoveryDenied):
            c.recover()
        assert c.snapshot() == committed != before
        assert len(provider.calls) == 5
        with harness.runtime.sessions.begin() as db:
            row = db.get(WriteRecord, ref.historical.record_id)
            assert row
            row.purge_at = now() - 1
            db.flush()
            storage.cleanup(db)
            assert db.get(WriteRecord, ref.historical.record_id) is None


@pytest.mark.parametrize(
    "change",
    [
        "missing_session",
        "active_session",
        "idle_only",
        "wrong_session_user",
        "missing_grant",
        "disconnected",
        "revoked",
        "error",
        "stack",
        "company",
        "generation",
        "no_read_scope",
        "bitmask_scope",
        "retry_after",
        "missing_record",
        "missing_payload",
        "malformed",
        "shape",
        "digest",
        "record_user",
        "record_session",
        "record_created",
        "record_expiry",
        "binding",
        "state_pending",
        "state_claimed",
        "state_verifying",
        "state_verified",
        "journal_claimed",
        "journal_verifying",
        "journal_all_verified",
        "journal_skipped",
        "fence_missing",
        "fence_user",
        "fence_workspace",
        "fence_record",
        "young",
        "conflict",
        "unknown_conflict",
        "env_test",
        "env_production",
        "writes_on",
        "authorized",
        "independent_receipt_reviewed",
        "writers_drained",
        "upstream_settled",
        "review_stack",
        "review_company",
        "anchor",
        "receipt_user",
        "receipt_context",
        "desired",
    ],
)
def test_preflight_denies_without_provider_calls_or_mutations(
    case: RetainedCase, change: str
) -> None:
    c, h, ref = case, case.harness, case.reference
    with h.runtime.sessions.begin() as db:
        row = db.get(WriteRecord, ref.historical.record_id)
        session = db.get(Session, ref.historical.binding.session)
        grant = db.get(OnshapeAuthorization, ref.independent.user)
        fence = db.scalar(select(WriteFence))
        assert row and session and grant and fence
        if change == "missing_session":
            db.delete(session)
        elif change in ("active_session", "idle_only"):
            session.expires_at = now() + 10000
            session.last_seen_at = (
                now() - h.runtime.settings.session_idle_seconds - 1
                if change == "idle_only"
                else now()
            )
        elif change in ("wrong_session_user", "record_user", "fence_user"):
            other = User(
                stack=grant.stack,
                onshape_user_id="synthetic-other",
                display_name="Other",
            )
            db.add(other)
            db.flush()
            if change == "wrong_session_user":
                session.user_id = other.id
            elif change == "record_user":
                row.user_id = other.id
            else:
                fence.user_id = other.id
        elif change == "missing_grant":
            db.delete(grant)
        elif change in ("disconnected", "revoked", "error"):
            grant.status = change
        elif change == "stack":
            grant.stack = "https://enterprise.onshape.com/api"
        elif change == "company":
            grant.company_id = "f" * 24
        elif change == "generation":
            grant.generation = "synthetic-rotated"
        elif change in ("no_read_scope", "bitmask_scope"):
            grant.granted_scope = (
                "OAuth2Write" if change == "no_read_scope" else "onshape_bitmask:7"
            )
        elif change == "retry_after":
            grant.retry_after = now() + 60
        elif change == "missing_record":
            db.delete(row)
        elif change == "missing_payload":
            row.payload = None
        elif change == "malformed":
            row.payload = "{invalid"
        elif change == "shape":
            row.payload = "{}"
        elif change == "digest":
            row.digest = "0" * 64
        elif change == "record_session":
            row.session_hash = "f" * 64
        elif change == "record_created":
            row.created_at -= 1
        elif change == "record_expiry":
            row.expires_at -= 1
        elif change.startswith("state_"):
            row.state = change.removeprefix("state_")
        elif change in ("binding", "young") or change.startswith("journal_"):
            saved = plan_storage.load(row)
            value = saved.model_dump(mode="json")
            if change == "binding":
                value["plan"]["binding"]["generation"] = "synthetic-corrupt"
            elif change == "young":
                value["plan"]["created_at"] = now() - 100
                value["plan"]["expires_at"] = now() + 20
            else:
                value["result"] = {
                    "state": "claimed"
                    if change == "journal_claimed"
                    else "verifying"
                    if change == "journal_verifying"
                    else "execution_uncertain",
                    "operations": [
                        "verified_success"
                        if change == "journal_all_verified"
                        else "skipped"
                        if change == "journal_skipped"
                        else "executing"
                    ],
                }
            altered = StoredPlan.model_validate_json(__import__("json").dumps(value))
            row.payload = altered.model_dump_json()
            row.digest = fingerprint(altered.plan.model_dump(mode="json"))
            if change == "young":
                row.created_at, row.expires_at = (
                    altered.plan.created_at,
                    altered.plan.expires_at,
                )
                c.reference = build_retained_reference(
                    ref.independent, altered, ref.review
                )
            elif change.startswith("journal_"):
                c.reference = build_retained_reference(
                    ref.independent, altered, ref.review
                )
        elif change == "fence_missing":
            db.delete(fence)
        elif change == "fence_workspace":
            fence.workspace_key = "f" * 64
        elif change == "fence_record":
            fence.record_id = "f" * 43
        elif change in ("conflict", "unknown_conflict"):
            db.add(
                WriteRecord(
                    id="z" * 43,
                    user_id=row.user_id,
                    session_hash=row.session_hash,
                    state="pending" if change == "conflict" else "unknown",
                    digest="f" * 64,
                    payload=None,
                    created_at=now(),
                    expires_at=now() + 120,
                    purge_at=now() + 900,
                )
            )
    if change in ("env_test", "env_production"):
        h.runtime.settings.environment = change.removeprefix("env_")  # type: ignore[assignment]
    elif change == "writes_on":
        h.runtime.settings.forge_cad_writes_enabled = True
    elif change in (
        "authorized",
        "independent_receipt_reviewed",
        "writers_drained",
        "upstream_settled",
        "review_stack",
        "review_company",
    ):
        field = (
            "operator_authorized"
            if change == "authorized"
            else "company_id"
            if change == "review_company"
            else change.removeprefix("review_")
            if change.startswith("review_")
            else change
        )
        review = ref.review.model_copy(
            update={
                field: "https://enterprise.onshape.com/api"
                if change == "review_stack"
                else "f" * 24
                if change == "review_company"
                else False
            }
        )
        c.reference = ref.model_copy(update={"review": review})
    elif change in ("anchor", "receipt_user", "receipt_context", "desired"):
        update: dict[str, Any] = {}
        if change == "anchor":
            update["anchor"] = ref.independent.anchor.model_copy(
                update={"value": "f" * 43}
            )
        elif change == "receipt_user":
            update["user"] = "synthetic-wrong"
        elif change == "receipt_context":
            update["context"] = ref.independent.context.model_copy(
                update={"elementId": "f" * 24}
            )
        else:
            update["desired_suppressed"] = False
        c.reference = ref.model_copy(
            update={"independent": ref.independent.model_copy(update=update)}
        )
    before = c.snapshot()
    with pytest.raises(RetainedRecoveryDenied):
        c.recover()
    assert c.snapshot() == before
    assert c.provider.calls == [] and c.provider.writes == 0


def test_revoked_historical_session_and_preserved_approval_anchor(
    case: RetainedCase,
) -> None:
    ref = case.reference
    with case.harness.runtime.sessions.begin() as db:
        session = db.get(Session, ref.historical.binding.session)
        row = db.get(WriteRecord, ref.historical.record_id)
        assert session and row
        session.expires_at, session.revoked_at = now() + 10000, now() - 1
        independent = ref.independent.model_copy(
            update={
                "anchor": PreservedApproval(
                    kind="preserved_approval_digest", value=ref.historical.plan_digest
                )
            }
        )
        case.reference = build_retained_reference(
            independent, plan_storage.load(row), ref.review
        )
    case.recover()


@pytest.mark.parametrize(
    "change",
    [
        "missing",
        "duplicate",
        "order",
        "conflict",
        "wrong_user",
        "prior_recovery",
        "outcome",
        "late",
        "future",
    ],
)
def test_audit_ambiguity_denies_before_capture(case: RetainedCase, change: str) -> None:
    ref = case.reference
    with case.harness.runtime.sessions.begin() as db:
        ack = db.scalar(
            select(AuditEvent).where(AuditEvent.kind == "write_provider_acknowledged")
        )
        assert ack
        if change == "missing":
            db.delete(ack)
        elif change == "duplicate":
            db.add(
                AuditEvent(
                    user_id=ack.user_id,
                    kind=ack.kind,
                    outcome="ok",
                    created_at=ack.created_at,
                )
            )
        elif change == "order":
            ack.created_at = ref.historical.created_at
        elif change == "wrong_user":
            ack.user_id = None
        elif change == "outcome":
            ack.outcome = "denied"
        elif change == "late":
            ack.created_at = ref.historical.created_at + 901
        elif change == "future":
            ack.created_at = now() + 1
        else:
            db.add(
                AuditEvent(
                    user_id=ack.user_id,
                    kind="write_retained_operator_recovery"
                    if change == "prior_recovery"
                    else "write_verified",
                    outcome="local_only" if change == "prior_recovery" else "ok",
                    created_at=now(),
                )
            )
    before = case.snapshot()
    with pytest.raises(RetainedRecoveryDenied):
        case.recover()
    assert case.snapshot() == before and case.provider.calls == []


@pytest.mark.parametrize(
    "stage", ["before_update", "after_update", "after_delete", "audit", "commit"]
)
def test_atomic_failure_restores_original_fence_and_record(
    case: RetainedCase, monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    before = case.snapshot()
    engine = case.harness.runtime.sessions.kw["bind"]

    def before_sql(
        conn: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        if stage == "before_update" and statement.startswith(
            "UPDATE write_records SET state="
        ):
            raise RuntimeError("synthetic failure")

    def after_sql(
        conn: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        if (
            stage == "after_update"
            and statement.startswith("UPDATE write_records SET state=")
        ) or (
            stage == "after_delete" and statement.startswith("DELETE FROM write_fences")
        ):
            raise RuntimeError("synthetic failure")

    def fail(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("synthetic failure")

    event.listen(engine, "before_cursor_execute", before_sql)
    event.listen(engine, "after_cursor_execute", after_sql)
    if stage == "audit":
        monkeypatch.setattr(retained_release, "audit", fail)
    if stage == "commit":
        event.listen(engine, "commit", fail)
    try:
        with pytest.raises(RuntimeError, match="synthetic failure"):
            case.recover()
    finally:
        event.remove(engine, "before_cursor_execute", before_sql)
        event.remove(engine, "after_cursor_execute", after_sql)
        if stage == "commit":
            event.remove(engine, "commit", fail)
    assert case.snapshot() == before
    assert case.provider.writes == 0


def test_missing_or_database_only_independent_evidence_is_invalid(
    case: RetainedCase,
) -> None:
    data = case.reference.independent.model_dump(mode="json")
    for field in ("anchor", "receipt_digest", "source"):
        with pytest.raises(ValidationError):
            IndependentOperationEvidence.model_validate_json(
                __import__("json").dumps({k: v for k, v in data.items() if k != field})
            )
    data["source"] = "current_database_row"
    with pytest.raises(ValidationError):
        IndependentOperationEvidence.model_validate_json(__import__("json").dumps(data))


def test_existing_orphan_helper_still_rejects_retained_record(
    case: RetainedCase,
) -> None:
    ref = case.reference
    with pytest.raises(dev_recovery.RecoveryDenied, match="referenced_record_present"):
        dev_recovery.recover_orphaned_fence(
            case.harness.runtime.sessions,
            case.harness.runtime.settings,
            dev_recovery.RecoveryReference(
                user=ref.independent.user,
                session=ref.historical.binding.session,
                workspace_key=ref.historical.binding.workspace_key,
                record_id=ref.historical.record_id,
                created_at=ref.historical.created_at,
                settled=True,
            ),
        )


def test_reader_is_closed_before_provider_free_release(
    case: RetainedCase, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = retained_release.release_retained_record

    def release(*args: Any, **kwargs: Any) -> Any:
        def forbidden(*a: Any, **kw: Any) -> None:
            raise AssertionError("provider capability used in release")

        monkeypatch.setattr(RetainedEvidenceReader, "capture", forbidden)
        monkeypatch.setattr(
            case.harness.runtime.tokens, "cached_read_credential", forbidden
        )
        monkeypatch.setattr(case.harness.runtime.provider, "refresh", forbidden)
        assert all(r.method == "GET" for r in case.provider.calls)
        return original(*args, **kwargs)

    monkeypatch.setattr(retained_recovery, "release_retained_record", release)
    case.recover()


def test_lost_commit_response_never_retries_or_returns_false_success(
    case: RetainedCase, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = SessionTransaction.__exit__

    def exit_after_commit(self: Any, *args: Any, **kwargs: Any) -> Any:
        result = original(self, *args, **kwargs)
        if len(case.provider.calls) == 5 and not self.nested:
            raise RuntimeError("synthetic lost commit response")
        return result

    with monkeypatch.context() as patch:
        patch.setattr(SessionTransaction, "__exit__", exit_after_commit)
        with pytest.raises(RuntimeError, match="lost commit response"):
            case.recover()
    committed = case.snapshot()
    assert committed[0] is not None and committed[0][0] == "operator_recovered"  # type: ignore[index]
    with pytest.raises(RetainedRecoveryDenied):
        case.recover()
    assert case.snapshot() == committed and len(case.provider.calls) == 5
