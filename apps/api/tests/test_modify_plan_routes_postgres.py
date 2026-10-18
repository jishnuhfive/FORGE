"""A2 authority races against isolated PostgreSQL schemas, mocked CAD only."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from typing import Any

import pytest
from conftest import Harness
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session
from test_modify_plan import PlanProvider, prepare
from test_modify_plan_postgres import use_postgres
from test_modify_plan_routes import events, path, status
from test_modify_plan_routes import no_ai as no_ai
from test_postgres import postgres as postgres
from test_safe_edit import running

from forge_api.cad_edits import plan_service, plan_storage
from forge_api.cad_edits.plans import ModifyPlan, PlanResult
from forge_api.db.coordination import user_lock
from forge_api.db.models import AuditEvent, WriteFence, WriteRecord


@pytest.mark.parametrize("iteration", range(6))
def test_http_cancel_approval_race_one_authority(
    postgres: Engine, harness: Harness, iteration: int
) -> None:
    use_postgres(harness, postgres)
    provider = PlanProvider()
    with running(harness, provider):
        _, preview = prepare(harness)
        headers = harness.headers()
        barrier = Barrier(2)

        def attempt(action: str) -> tuple[str, int]:
            barrier.wait(timeout=5)
            response = harness.client.post(
                path(preview, "/" + action),
                headers=headers,
                json={"digest": preview.digest} if action == "approve" else {},
            )
            if response.status_code == 200 and action == "approve":
                assert events(response)[-1]["state"] == "verified_success"
            return action, response.status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = dict(pool.map(attempt, ("approve", "cancel")))
        assert sorted(results.values()) == [200, 409], iteration
        final = status(harness, preview)
        if results["cancel"] == 200:
            assert final == {"state": "cancelled", "operations": ["skipped"] * 3}
            assert provider.writes == 0
        else:
            assert final == {
                "state": "verified_success",
                "operations": ["verified_success"] * 3,
            }
            assert provider.writes == 3
        with harness.runtime.sessions() as db:
            assert db.scalar(select(WriteFence)) is None
            kinds = list(db.scalars(select(AuditEvent.kind)))
            assert (
                kinds.count("write_proposal_claimed"),
                kinds.count("write_proposal_cancelled"),
            ) in ((1, 0), (0, 1))


@pytest.mark.parametrize("winner", ["approve", "cancel"])
def test_both_ordered_race_outcomes_with_competitor_at_database_lock(
    postgres: Engine, harness: Harness, monkeypatch: pytest.MonkeyPatch, winner: str
) -> None:
    use_postgres(harness, postgres)
    provider = PlanProvider()
    owns_lock, competitor, release = Event(), Event(), Event()
    original_lock = user_lock
    original_claim, original_cancel = plan_storage.claim, plan_storage.cancel

    def lock(db: Session, user: str) -> None:
        if owns_lock.is_set() and not release.is_set():
            competitor.set()
        original_lock(db, user)

    def wait() -> None:
        owns_lock.set()
        assert release.wait(10)

    def claim(*args: Any, **kwargs: Any) -> ModifyPlan:
        if winner == "approve":
            wait()
        return original_claim(*args, **kwargs)

    def cancel(*args: Any, **kwargs: Any) -> PlanResult:
        if winner == "cancel":
            wait()
        return original_cancel(*args, **kwargs)

    monkeypatch.setattr(plan_service, "user_lock", lock)
    monkeypatch.setattr(plan_storage, "claim", claim)
    monkeypatch.setattr(plan_storage, "cancel", cancel)
    with running(harness, provider):
        _, preview = prepare(harness)
        headers = harness.headers()

        def attempt(action: str) -> int:
            return harness.client.post(
                path(preview, "/" + action),
                headers=headers,
                json={"digest": preview.digest} if action == "approve" else {},
            ).status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(attempt, winner)
            assert owns_lock.wait(5)
            second = pool.submit(
                attempt, "cancel" if winner == "approve" else "approve"
            )
            assert competitor.wait(5)
            release.set()
            assert first.result(timeout=10) == 200
            assert second.result(timeout=10) == 409
        assert status(harness, preview)["state"] == (
            "verified_success" if winner == "approve" else "cancelled"
        )
        assert provider.writes == (3 if winner == "approve" else 0)


def test_http_concurrent_approval_one_winner_three_writes(
    postgres: Engine, harness: Harness
) -> None:
    use_postgres(harness, postgres)
    provider = PlanProvider()
    with running(harness, provider):
        _, preview = prepare(harness)
        headers = harness.headers()
        barrier = Barrier(4)

        def attempt(_: int) -> int:
            barrier.wait(timeout=5)
            response = harness.client.post(
                path(preview, "/approve"),
                headers=headers,
                json={"digest": preview.digest},
            )
            if response.status_code == 200:
                assert events(response)[-1]["state"] == "verified_success"
            return response.status_code

        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(attempt, range(4)))
        assert results.count(200) == 1 and results.count(409) == 3
        assert provider.writes == 3
        assert status(harness, preview)["operations"] == ["verified_success"] * 3
        with harness.runtime.sessions() as db:
            assert db.scalar(select(WriteFence)) is None
            row = db.get(WriteRecord, preview.proposal_id)
            assert row and row.state == "verified_success"


def test_storage_compare_and_set_without_process_or_user_lock(
    postgres: Engine, harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Force both transactions to load pending before their conditional UPDATEs."""
    from forge_api.cad_edits.domain import EditError

    use_postgres(harness, postgres)
    provider = PlanProvider()
    original = plan_storage.load
    barrier = Barrier(2)

    def load(row: WriteRecord) -> Any:
        value = original(row)
        barrier.wait(timeout=5)
        return value

    with running(harness, provider):
        _, preview = prepare(harness)
        with harness.runtime.sessions() as db:
            row = db.get(WriteRecord, preview.proposal_id)
            assert row
            binding = original(row).plan.binding
        monkeypatch.setattr(plan_storage, "load", load)

        def attempt(action: str) -> str:
            try:
                with harness.runtime.sessions.begin() as db:
                    if action == "approve":
                        plan_storage.claim(
                            db,
                            preview.proposal_id,
                            binding.user,
                            binding.session,
                            preview.digest,
                        )
                    else:
                        plan_storage.cancel(
                            db, preview.proposal_id, binding.user, binding.session
                        )
                return action
            except EditError:
                return "denied"

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, ("approve", "cancel")))
        assert results.count("denied") == 1
        with harness.runtime.sessions() as db:
            row = db.get(WriteRecord, preview.proposal_id)
            assert row
            assert row.state == ("claimed" if "approve" in results else "cancelled")
            assert (db.scalar(select(WriteFence)) is not None) == ("approve" in results)
        assert provider.writes == 0  # This test claims storage only; never resumes.
