"""Synthetic database administration only; never contact a CAD provider."""

from dataclasses import dataclass

import httpx2 as httpx
import pytest
from conftest import Harness
from pydantic import ValidationError
from sqlalchemy import select

from forge_api.auth.security import random_token
from forge_api.cad_edits import dev_recovery, storage
from forge_api.cad_edits.dev_recovery import (
    RecoveryDenied,
    RecoveryReference,
    recover_orphaned_fence,
)
from forge_api.core.config import Settings
from forge_api.db.models import (
    AuditEvent,
    OnshapeAuthorization,
    Session,
    User,
    WriteFence,
    WriteRecord,
    now,
)

KINDS = (
    "write_proposal_claimed",
    "write_dispatch_started",
    "write_provider_acknowledged",
    "write_uncertain",
)


@dataclass
class Case:
    harness: Harness
    reference: RecoveryReference
    settings: Settings

    def recover(self) -> None:
        recover_orphaned_fence(
            self.harness.runtime.sessions, self.settings, self.reference
        )

    def assert_untouched(self) -> None:
        with self.harness.runtime.sessions() as db:
            assert db.get(WriteFence, "1" * 64) is not None
            assert (
                db.scalar(
                    select(AuditEvent).where(
                        AuditEvent.kind == "write_operator_recovery"
                    )
                )
                is None
            )


@pytest.fixture
def case(harness: Harness, monkeypatch: pytest.MonkeyPatch) -> Case:
    user = harness.login()
    with harness.runtime.sessions.begin() as db:
        session = db.scalar(select(Session).where(Session.user_id == user))
        assert session is not None
        reference = RecoveryReference(
            user=user,
            session=session.token_hash,
            workspace_key="1" * 64,
            record_id=random_token(),
            created_at=now() - 1000,
            settled=True,
        )
        db.add(
            WriteFence(
                user_id=user,
                workspace_key=reference.workspace_key,
                record_id=reference.record_id,
            )
        )
        db.add(
            WriteRecord(
                id=reference.record_id,
                user_id=user,
                session_hash=reference.session,
                state="execution_uncertain",
                digest="2" * 64,
                payload=None,
                created_at=reference.created_at,
                expires_at=reference.created_at + 120,
                purge_at=reference.created_at + 900,
            )
        )
        for index, kind in enumerate(KINDS):
            db.add(
                AuditEvent(
                    user_id=user,
                    kind=kind,
                    outcome="ok",
                    created_at=reference.created_at + index,
                )
            )
        db.flush()
        storage.cleanup(db)
        assert db.get(WriteRecord, reference.record_id) is None

    def no_http(*args: object, **kwargs: object) -> None:
        pytest.fail("Operator recovery must not contact a provider")

    monkeypatch.setattr(httpx.Client, "request", no_http)
    return Case(
        harness,
        reference,
        harness.runtime.settings.model_copy(update={"environment": "development"}),
    )


def test_exact_orphan_recovery_is_audited_atomic_and_one_time(case: Case) -> None:
    with case.harness.runtime.sessions.begin() as db:
        session = db.get(Session, case.reference.session)
        assert session
        session.expires_at = now() - 1
    case.recover()
    with case.harness.runtime.sessions() as db:
        assert db.scalar(select(WriteFence)) is None
        assert db.scalar(select(WriteRecord)) is None
        event = db.scalar(
            select(AuditEvent).where(AuditEvent.kind == "write_operator_recovery")
        )
        assert event and event.outcome == "local_only"
        assert event.user_id == case.reference.user
        session = db.get(Session, case.reference.session)
        assert session and session.expires_at < now()  # No session resurrection.
    with pytest.raises(RecoveryDenied, match="exact_single_fence_required"):
        case.recover()
    with case.harness.runtime.sessions() as db:
        assert (
            len(
                list(
                    db.scalars(
                        select(AuditEvent).where(
                            AuditEvent.kind == "write_operator_recovery"
                        )
                    )
                )
            )
            == 1
        )


def test_unrelated_fence_survives_and_ambiguous_candidates_reject(case: Case) -> None:
    with case.harness.runtime.sessions.begin() as db:
        other = User(
            onshape_user_id="synthetic-other",
            stack="https://cad.onshape.com/api",
            display_name="Synthetic",
        )
        db.add(other)
        db.flush()
        db.add(
            WriteFence(
                user_id=other.id, workspace_key="2" * 64, record_id=random_token()
            )
        )
    original = case.reference
    case.reference = original.model_copy(update={"workspace_key": "2" * 64})
    with pytest.raises(RecoveryDenied, match="exact_single_fence_required"):
        case.recover()
    case.assert_untouched()
    case.reference = original
    case.recover()
    with case.harness.runtime.sessions() as db:
        fences = list(db.scalars(select(WriteFence)))
        assert len(fences) == 1 and fences[0].workspace_key == "2" * 64


@pytest.mark.parametrize(
    "field,value",
    [("workspace_key", "3" * 64), ("record_id", "x" * 43), ("session", "4" * 64)],
)
def test_precise_reference_mismatch_rejects(case: Case, field: str, value: str) -> None:
    case.reference = case.reference.model_copy(update={field: value})
    with pytest.raises(RecoveryDenied):
        case.recover()
    case.assert_untouched()


@pytest.mark.parametrize(
    "environment,writes,settled",
    [
        ("production", False, True),
        ("test", False, True),
        ("development", True, True),
        ("development", False, False),
    ],
)
def test_development_off_and_operator_settlement_required(
    case: Case, environment: str, writes: bool, settled: bool
) -> None:
    case.settings = case.settings.model_copy(
        update={"environment": environment, "forge_cad_writes_enabled": writes}
    )
    case.reference = case.reference.model_copy(update={"settled": settled})
    with pytest.raises(RecoveryDenied):
        case.recover()
    case.assert_untouched()


@pytest.mark.parametrize(
    "state",
    [
        "candidate",
        "pending",
        "claimed",
        "verifying",
        "execution_uncertain",
        "unverified_result",
        "recovery_required",
        "expired",
        "admission",
        "unknown",
    ],
)
@pytest.mark.parametrize("referenced", [False, True])
def test_any_retained_record_blocks_recovery(
    case: Case, state: str, referenced: bool
) -> None:
    with case.harness.runtime.sessions.begin() as db:
        db.add(
            WriteRecord(
                id=case.reference.record_id if referenced else random_token(),
                user_id=case.reference.user,
                session_hash=case.reference.session,
                state=state,
                digest="2" * 64,
                payload=None,
                created_at=now(),
                expires_at=now() + 120,
                purge_at=now() + 900,
            )
        )
    with pytest.raises(RecoveryDenied):
        case.recover()
    case.assert_untouched()
    with case.harness.runtime.sessions() as db:
        assert db.scalar(select(WriteRecord)) is not None


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("change", ["missing", "duplicate", "denied", "late"])
def test_incomplete_or_ambiguous_audit_rejects(
    case: Case, kind: str, change: str
) -> None:
    with case.harness.runtime.sessions.begin() as db:
        event = db.scalar(select(AuditEvent).where(AuditEvent.kind == kind))
        assert event
        if change == "missing":
            db.delete(event)
        elif change == "duplicate":
            db.add(AuditEvent(user_id=event.user_id, kind=kind, outcome="ok"))
        elif change == "denied":
            event.outcome = "denied"
        else:
            event.created_at = case.reference.created_at + 901
    with pytest.raises(RecoveryDenied, match="unique_uncertain_audit_required"):
        case.recover()
    case.assert_untouched()


@pytest.mark.parametrize("change", ["order", "prior_recovery", "wrong_user"])
def test_audit_order_and_identity_required(case: Case, change: str) -> None:
    with case.harness.runtime.sessions.begin() as db:
        event = db.scalar(select(AuditEvent).where(AuditEvent.kind == KINDS[1]))
        assert event
        if change == "order":
            event.created_at = case.reference.created_at + 4
        elif change == "wrong_user":
            event.user_id = None
        else:
            db.add(
                AuditEvent(
                    user_id=case.reference.user,
                    kind="write_operator_recovery",
                    outcome="local_only",
                )
            )
    with pytest.raises(RecoveryDenied, match="unique_uncertain_audit_required"):
        case.recover()
    if change != "prior_recovery":
        case.assert_untouched()
    with case.harness.runtime.sessions() as db:
        assert db.get(WriteFence, "1" * 64) is not None


def test_retention_not_elapsed_rejects(case: Case) -> None:
    case.reference = case.reference.model_copy(update={"created_at": now()})
    with pytest.raises(RecoveryDenied, match="retention_not_elapsed"):
        case.recover()
    case.assert_untouched()


@pytest.mark.parametrize("change", ["session", "grant", "stack", "company"])
def test_identity_must_match_preserved_session_and_configured_stack(
    case: Case, change: str
) -> None:
    with case.harness.runtime.sessions.begin() as db:
        if change == "session":
            session = db.get(Session, case.reference.session)
            assert session
            db.delete(session)
        else:
            grant = db.get(OnshapeAuthorization, case.reference.user)
            assert grant
            if change == "grant":
                grant.status = "disconnected"
            elif change == "stack":
                grant.stack = "https://example.invalid/api"
            else:
                grant.company_id = "a" * 24
    with pytest.raises(RecoveryDenied, match="original_identity_mismatch"):
        case.recover()
    case.assert_untouched()


def test_audit_failure_rolls_back_deletion(
    case: Case, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unavailable(*args: object) -> None:
        raise RuntimeError("synthetic audit unavailable")

    monkeypatch.setattr(dev_recovery, "audit", unavailable)
    with pytest.raises(RuntimeError, match="synthetic audit unavailable"):
        case.recover()
    case.assert_untouched()


@pytest.mark.parametrize(
    "field", ["session", "workspace_key", "record_id", "created_at", "settled"]
)
def test_reference_schema_is_strict_and_private(case: Case, field: str) -> None:
    data = case.reference.model_dump()
    data[field] = False if field == "created_at" else 1
    with pytest.raises(ValidationError):
        RecoveryReference.model_validate(data)
    for name in ("user", "session", "workspace_key", "record_id"):
        assert getattr(case.reference, name) not in repr(case.reference)
