"""PostgreSQL recovery races in a random schema, using invented CAD only."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from typing import Any

import pytest
from conftest import Harness
from sqlalchemy import Engine, select
from test_cad_read import REF
from test_modify_plan import PlanProvider, request_for
from test_modify_plan_postgres import use_postgres
from test_modify_recovery import current, uncertain
from test_postgres import postgres as postgres
from test_safe_edit import running

from forge_api.cad_edits import plan_recovery, plan_service, storage
from forge_api.cad_edits.domain import EditError
from forge_api.db.models import AuditEvent, WriteFence, WriteRecord, now


def test_concurrent_read_reconciliation_has_one_closure(
    postgres: Engine, harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_postgres(harness, postgres)
    provider = PlanProvider()
    with running(harness, provider):
        preview = uncertain(harness)
        current(provider, True)
        original = plan_service._capture
        barrier = Barrier(2)

        def capture(*args: Any, **kwargs: Any) -> Any:
            # Both workers obtain the same legitimate fresh read before racing
            # for the final user lock. Avoid artificial CAD-gate rate rejection.
            evidence = args[2].modify_evidence(REF)
            barrier.wait(timeout=10)
            return evidence

        monkeypatch.setattr(plan_service, "_capture", capture)

        def attempt(_: int) -> str:
            try:
                return plan_recovery.reconcile(
                    request_for(harness), harness.runtime, preview.proposal_id
                ).state
            except EditError:
                return "denied"

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, range(2)))
        assert results.count("reconciled_current_state") == 1
        assert results.count("denied") == 1
        assert provider.writes == 0
        monkeypatch.setattr(plan_service, "_capture", original)
        with harness.runtime.sessions.begin() as db:
            assert db.scalar(select(WriteFence)) is None
            assert (
                len(
                    list(
                        db.scalars(
                            select(AuditEvent).where(
                                AuditEvent.kind == "write_current_state_reconciled"
                            )
                        )
                    )
                )
                == 1
            )
            row = db.get(WriteRecord, preview.proposal_id)
            assert row
            row.purge_at = now() - 1
            db.flush()
            storage.cleanup(db)
            assert db.get(WriteRecord, preview.proposal_id) is None
