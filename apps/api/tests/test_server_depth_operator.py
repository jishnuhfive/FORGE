"""Short in-process operator entry; mocked CAD and temporary database only."""

from typing import Any

import httpx2 as httpx
import pytest
from conftest import Harness
from server_depth_support import ServerCase, review
from sqlalchemy import delete, select
from sqlalchemy.orm import SessionTransaction
from test_modify_plan import PlanProvider, prepare
from test_modify_plan_routes import send
from test_safe_edit import running
from test_server_depth_recovery import case as case

from forge_api.cad_edits.depth_contracts import DepthRecoveryDenied
from forge_api.cad_edits.depth_recovery import recover_development_depth_incident
from forge_api.db.models import AuditEvent, OnshapeAuthorization, WriteRecord


def execute(c: ServerCase, **changes: Any) -> object:
    return recover_development_depth_incident(
        c.harness.runtime,
        review(c.harness).model_copy(update=changes),
        transport=httpx.MockTransport(c.provider.handle),
    )


def test_operator_derives_pins_and_confirms_redacted_closure(case: ServerCase) -> None:
    assert "independent" not in case.reference.model_dump()
    result = execute(case)
    assert result.approval_provenance == "server_attested_development"  # type: ignore[attr-defined]
    assert result.original_execution_outcome == "execution_uncertain"  # type: ignore[attr-defined]
    assert case.snapshot()[1] == ()
    assert len(case.provider.calls) == 8 and case.provider.writes == 0
    after = case.snapshot()
    with pytest.raises(DepthRecoveryDenied):
        execute(case)
    assert case.snapshot() == after and len(case.provider.calls) == 8


@pytest.mark.parametrize(
    "field",
    [
        "operator_authorized",
        "server_attested_policy_accepted",
        "disposable_fixture",
        "writers_drained",
        "upstream_settled",
    ],
)
def test_operator_review_is_mandatory(case: ServerCase, field: str) -> None:
    before = case.snapshot()
    with pytest.raises(
        DepthRecoveryDenied, match="development_incident_review_required"
    ):
        execute(case, **{field: False})
    assert case.snapshot() == before and not case.provider.calls


@pytest.mark.parametrize("environment", ["production", "test"])
def test_operator_environment_denied(case: ServerCase, environment: str) -> None:
    case.harness.runtime.settings.environment = environment  # type: ignore[assignment]
    before = case.snapshot()
    with pytest.raises(DepthRecoveryDenied, match="development_writes_off_required"):
        execute(case)
    assert case.snapshot() == before and not case.provider.calls


@pytest.mark.parametrize(
    "kind", ["write_proposal_claimed", "write_dispatch_started", "write_uncertain"]
)
@pytest.mark.parametrize("mutation", ["missing", "duplicate", "order"])
def test_exact_server_audit_window_is_required(
    case: ServerCase, kind: str, mutation: str
) -> None:
    with case.harness.runtime.sessions.begin() as db:
        event = db.scalar(select(AuditEvent).where(AuditEvent.kind == kind))
        assert event
        if mutation == "missing":
            db.delete(event)
        elif mutation == "duplicate":
            db.add(
                AuditEvent(
                    kind=kind,
                    user_id=event.user_id,
                    outcome="ok",
                    created_at=event.created_at,
                )
            )
        else:
            event.created_at = case.reference.historical.created_at + (
                10 if kind != "write_uncertain" else 0
            )
    before = case.snapshot()
    with pytest.raises(DepthRecoveryDenied):
        execute(case)
    assert case.snapshot() == before and not case.provider.calls


def test_absent_ack_can_close_but_never_becomes_ack_evidence(case: ServerCase) -> None:
    with case.harness.runtime.sessions.begin() as db:
        db.execute(
            delete(AuditEvent).where(AuditEvent.kind == "write_provider_acknowledged")
        )
    execute(case)
    with case.harness.runtime.sessions() as db:
        assert (
            db.scalar(
                select(AuditEvent).where(
                    AuditEvent.kind == "write_provider_acknowledged"
                )
            )
            is None
        )


def test_lost_commit_reply_is_sanitized_without_retry(
    case: ServerCase, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = SessionTransaction.__exit__
    failed = False

    def commit(self: SessionTransaction, *a: Any, **kw: Any) -> Any:
        nonlocal failed
        value = original(self, *a, **kw)
        if not failed and len(case.provider.calls) == 8 and self.parent is None:
            failed = True
            raise RuntimeError("synthetic private unknown completion")
        return value

    monkeypatch.setattr(SessionTransaction, "__exit__", commit)
    with pytest.raises(DepthRecoveryDenied, match="completion_unconfirmed_no_retry"):
        execute(case)
    committed = case.snapshot()
    assert committed[0][0] == "operator_recovered"  # type: ignore[index]
    with pytest.raises(DepthRecoveryDenied):
        execute(case)
    assert case.snapshot() == committed and len(case.provider.calls) == 8


def test_cached_credential_unavailable_never_refreshes(
    case: ServerCase, monkeypatch: pytest.MonkeyPatch
) -> None:
    from forge_api.auth.provider import ProviderError

    def missing(*a: Any, **kw: Any) -> Any:
        raise ProviderError

    def forbidden(*a: Any, **kw: Any) -> Any:
        raise AssertionError("must not refresh")

    monkeypatch.setattr(case.harness.runtime.tokens, "cached_read_credential", missing)
    monkeypatch.setattr(case.harness.runtime.provider, "refresh", forbidden)
    before = case.snapshot()
    with pytest.raises(DepthRecoveryDenied, match="cached_read_credential_required"):
        execute(case)
    assert case.snapshot() == before and not case.provider.calls


def test_claim_audit_precedes_current_grant_revalidation(harness: Harness) -> None:
    provider = PlanProvider()
    with running(harness, provider):
        _, proposal = prepare(harness, ("SET_EXTRUDE_DEPTH",))
        with harness.runtime.sessions.begin() as db:
            grant = db.scalar(select(OnshapeAuthorization))
            assert grant
            grant.granted_scope = "OAuth2Read"
        response = send(harness, proposal)
        assert response.status_code == 200
        with harness.runtime.sessions() as db:
            kinds = [e.kind for e in db.scalars(select(AuditEvent))]
            row = db.get(WriteRecord, proposal.proposal_id)
            assert row and row.state == "write_failed"
            assert kinds.count("write_proposal_claimed") == 1
            assert "write_dispatch_started" not in kinds
        assert provider.writes == 0
