"""Real isolated PostgreSQL, with every CAD read/write still mocked."""

from concurrent.futures import ThreadPoolExecutor

import pytest
from conftest import Harness, migrate
from sqlalchemy import Engine, select
from test_modify_plan import PlanProvider, approve, prepare
from test_postgres import postgres as postgres
from test_safe_edit import running

from forge_api.auth.runtime import AuthRuntime
from forge_api.cad_edits import plan_service, plan_storage, storage
from forge_api.cad_edits.domain import EditError
from forge_api.db.models import WriteFence, WriteRecord, now


def use_postgres(harness: Harness, postgres: Engine) -> None:
    migrate(postgres)
    runtime = AuthRuntime.create(
        harness.runtime.settings, postgres, harness.runtime.provider.client
    )
    harness.runtime = runtime
    harness.client.app.state.auth = runtime  # type: ignore[attr-defined]


def test_concurrent_plan_approval_has_one_winner_and_three_writes(
    postgres: Engine, harness: Harness
) -> None:
    use_postgres(harness, postgres)
    provider = PlanProvider()
    with running(harness, provider):
        req, preview = prepare(harness)

        def attempt(_: int) -> str:
            try:
                return plan_service.approve(
                    req, harness.runtime, preview.proposal_id, preview.digest
                ).state
            except EditError:
                return "denied"

        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(attempt, range(4)))
        assert results.count("verified_success") == 1
        assert results.count("denied") == 3
        assert provider.writes == 3
        with harness.runtime.sessions() as db:
            row = db.get(WriteRecord, preview.proposal_id)
            assert (
                row and plan_storage.result(row).operations == ("verified_success",) * 3
            )
            assert db.scalar(select(WriteFence)) is None


def test_partial_uncertainty_retains_prefix_and_denies_phase9(
    postgres: Engine, harness: Harness
) -> None:
    from test_safe_edit import post

    use_postgres(harness, postgres)
    provider = PlanProvider()
    with running(harness, provider):
        req, preview = prepare(harness)
        provider.mode = "timeout"
        result = approve(harness, req, preview)
        assert result.operations == (
            "verified_success",
            "execution_uncertain",
            "skipped",
        )
        assert provider.writes == 2
        blocked = post(
            harness,
            "targets",
            {"context": req_context(), "intent": "Suppress the final fillet."},
        )
        assert (
            blocked.status_code == 409
            and blocked.json()["detail"] == "workspace_fenced"
        )
        with harness.runtime.sessions.begin() as db:
            row = db.get(WriteRecord, preview.proposal_id)
            assert row
            row.purge_at = now() - 1
            db.flush()
            storage.cleanup(db)
        with harness.runtime.sessions() as db:
            assert db.get(WriteRecord, preview.proposal_id) is not None
            assert db.scalar(select(WriteFence)) is not None
        assert provider.writes == 2


def req_context() -> dict[str, object]:
    from test_cad_read import REF

    return REF.model_dump()


def test_auth_revocation_between_verified_operations_stops_dispatch(
    postgres: Engine, harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    from forge_api.db.models import Session
    from forge_api.integrations.onshape.contracts import WorkspaceReference
    from forge_api.integrations.onshape.modify_evidence import ModifyEvidence
    from forge_api.integrations.onshape.write_client import SafeEditClient

    use_postgres(harness, postgres)
    provider = PlanProvider()
    with running(harness, provider):
        req, preview = prepare(harness)
        original = SafeEditClient.modify_evidence
        reads = 0

        def read(self: SafeEditClient, context: WorkspaceReference) -> ModifyEvidence:
            nonlocal reads
            reads += 1
            # Third evidence read: op1 already durably verified; op2 checking.
            if reads == 3:
                with harness.runtime.sessions.begin() as db:
                    session = db.scalar(select(Session))
                    assert session
                    session.revoked_at = now()
            return original(self, context)

        monkeypatch.setattr(SafeEditClient, "modify_evidence", read)
        result = approve(harness, req, preview)
        assert result.operations == ("verified_success", "write_failed", "skipped")
        assert provider.writes == 1


def test_abandoned_claim_cannot_resume_and_expires_to_uncertain(
    postgres: Engine, harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_postgres(harness, postgres)
    provider = PlanProvider()
    with running(harness, provider):
        req, preview = prepare(harness)
        with harness.runtime.sessions.begin() as db:
            row = db.get(WriteRecord, preview.proposal_id)
            assert row
            saved = plan_storage.load(row)
            plan_storage.claim(
                db,
                preview.proposal_id,
                saved.plan.binding.user,
                saved.plan.binding.session,
                preview.digest,
            )
        monkeypatch.setattr(storage, "now", lambda: saved.plan.created_at + 151)
        result = plan_service.status(req, harness.runtime, preview.proposal_id)
        assert result.state == "execution_uncertain"
        assert result.operations == ("execution_uncertain", "skipped", "skipped")
        with pytest.raises(EditError):
            approve(harness, req, preview)
        assert provider.writes == 0
        with harness.runtime.sessions() as db:
            assert db.scalar(select(WriteFence)) is not None
