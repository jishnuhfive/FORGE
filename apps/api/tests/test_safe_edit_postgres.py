"""Real isolated PostgreSQL claims, upgrade preservation and fence semantics."""

from concurrent.futures import ThreadPoolExecutor

import httpx2 as httpx
import pytest
from alembic import command
from alembic.config import Config
from conftest import Harness, migrate
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session as DatabaseSession
from sqlalchemy.orm import sessionmaker
from test_cad_read import REF
from test_postgres import postgres as postgres
from test_safe_edit import M0, bodies, config, features

from forge_api.auth.security import random_token
from forge_api.cad_edits import storage
from forge_api.cad_edits.dev_recovery import (
    RecoveryDenied,
    RecoveryReference,
    recover_orphaned_fence,
)
from forge_api.cad_edits.domain import Binding, EditError, Proposal, preview
from forge_api.core.config import REPOSITORY_ROOT, Settings
from forge_api.db.models import (
    AuditEvent,
    OnshapeAuthorization,
    Session,
    User,
    WriteFence,
    WriteRecord,
    now,
)
from forge_api.integrations.onshape.write_evidence import project_write_evidence


def seed(engine: Engine) -> Proposal:
    factory = sessionmaker(engine)
    with factory.begin() as db:
        user = User(
            onshape_user_id="synthetic-safe-edit",
            display_name="Synthetic",
            stack="https://cad.onshape.com/api",
        )
        db.add(user)
        db.flush()
        binding = Binding(
            user=user.id,
            session="0" * 64,
            generation="synthetic",
            context=REF,
            workspace_key="1" * 64,
        )
        data = features()
        data["featureStates"] = {}
        p = Proposal(
            proposal_id=random_token(),
            binding=binding,
            baseline=project_write_evidence(REF, M0, data, config(), bodies()),
            created_at=now(),
            expires_at=now() + 120,
        )
        storage.store(db, p, "pending")
    return p


def test_operator_recovery_has_one_postgres_winner(postgres: Engine) -> None:
    migrate(postgres)
    p = seed(postgres)
    factory = sessionmaker(postgres)
    created = now() - 1000
    reference = RecoveryReference(
        user=p.binding.user,
        session=p.binding.session,
        workspace_key=p.binding.workspace_key,
        record_id=p.proposal_id,
        created_at=created,
        settled=True,
    )
    settings = Settings(_env_file=None, environment="development")
    with factory.begin() as db:
        row = db.get(WriteRecord, p.proposal_id)
        assert row
        row.state = "execution_uncertain"
        row.created_at = created
        row.purge_at = created + 900
        db.add(
            Session(
                token_hash=p.binding.session,
                user_id=p.binding.user,
                expires_at=now() - 1,
            )
        )
        db.add(
            OnshapeAuthorization(
                user_id=p.binding.user, stack=str(settings.onshape_api_base_url)
            )
        )
        db.add(
            WriteFence(
                user_id=p.binding.user,
                record_id=p.proposal_id,
                workspace_key=p.binding.workspace_key,
            )
        )
        for index, kind in enumerate(
            (
                "write_proposal_claimed",
                "write_dispatch_started",
                "write_provider_acknowledged",
                "write_uncertain",
            )
        ):
            db.add(
                AuditEvent(
                    user_id=p.binding.user,
                    kind=kind,
                    outcome="ok",
                    created_at=created + index,
                )
            )
        db.flush()
        storage.cleanup(db)
        # Historical orphan fixture; current cleanup preserves live records.
        db.delete(row)
        db.flush()

    def attempt(_: int) -> str:
        try:
            recover_orphaned_fence(factory, settings, reference)
            return "recovered"
        except RecoveryDenied:
            return "denied"

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(attempt, range(4)))
    assert results.count("recovered") == 1
    with factory() as db:
        assert db.scalar(select(WriteFence)) is None
        assert db.scalar(select(WriteRecord)) is None
        events = list(
            db.scalars(
                select(AuditEvent).where(AuditEvent.kind == "write_operator_recovery")
            )
        )
        assert len(events) == 1 and events[0].outcome == "local_only"


def test_one_claim_winner_across_workers_and_fence_survives_cleanup(
    postgres: Engine,
) -> None:
    migrate(postgres)
    p = seed(postgres)
    factory = sessionmaker(postgres)

    def attempt(_: int) -> str:
        try:
            with factory.begin() as db:
                storage.claim(
                    db,
                    p.proposal_id,
                    p.binding.user,
                    p.binding.session,
                    preview(p).digest,
                )
            return "claimed"
        except EditError:
            return "used"

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(attempt, range(4)))
    assert results.count("claimed") == 1
    with factory.begin() as db:
        row = db.get(WriteRecord, p.proposal_id)
        assert row
        row.purge_at = now() - 1
        db.flush()
        storage.cleanup(db)
    with factory() as db:
        assert db.get(WriteRecord, p.proposal_id) is not None
        assert db.scalar(select(WriteFence)) is not None


def test_upgrade_from_phase8_preserves_identity(postgres: Engine) -> None:
    c = Config(str(REPOSITORY_ROOT / "apps/api/alembic.ini"))
    with postgres.begin() as connection:
        c.attributes["connection"] = connection
        command.upgrade(c, "0001_authentication")
    factory = sessionmaker(postgres)
    with factory.begin() as db:
        db.add(
            User(
                id="synthetic-retained",
                onshape_user_id="synthetic-retained",
                display_name="Retained",
                stack="https://cad.onshape.com/api",
            )
        )
    migrate(postgres)
    with factory() as db:
        assert db.get(User, "synthetic-retained") is not None
    with postgres.begin() as connection:
        c.attributes["connection"] = connection
        command.check(c)


def test_pending_invalidation_and_expiry_are_not_reusable(postgres: Engine) -> None:
    migrate(postgres)
    p = seed(postgres)
    factory = sessionmaker(postgres)
    with factory.begin() as db:
        storage.invalidate(db, p.binding.user, p.binding.session)
    with factory.begin() as db:
        row = db.get(WriteRecord, p.proposal_id)
        assert row and row.state == "invalidated" and row.payload is None
        try:
            storage.claim(
                db, p.proposal_id, p.binding.user, p.binding.session, preview(p).digest
            )
        except EditError as e:
            assert e.code == "proposal_used"
        else:
            raise AssertionError("invalidated claim accepted")


def test_workspace_fence_rejects_another_user_and_expiry_cannot_claim(
    postgres: Engine,
) -> None:
    migrate(postgres)
    p = seed(postgres)
    factory = sessionmaker(postgres)
    with factory.begin() as db:
        storage.claim(
            db, p.proposal_id, p.binding.user, p.binding.session, preview(p).digest
        )
    with factory.begin() as db:
        user = User(
            onshape_user_id="synthetic-second",
            display_name="Second",
            stack="https://cad.onshape.com/api",
        )
        db.add(user)
        db.flush()
        other = p.model_copy(
            update={
                "proposal_id": random_token(),
                "binding": p.binding.model_copy(update={"user": user.id}),
            }
        )
        storage.store(db, other, "pending")
    with factory.begin() as db:
        try:
            storage.claim(
                db,
                other.proposal_id,
                other.binding.user,
                other.binding.session,
                preview(other).digest,
            )
        except EditError as e:
            assert e.code == "workspace_fenced"
        else:
            raise AssertionError("workspace collision accepted")
    with factory.begin() as db:
        row = db.get(WriteRecord, other.proposal_id)
        assert row
        row.expires_at = now() - 1
        db.flush()
        storage.cleanup(db)
    with factory.begin() as db:
        try:
            storage.claim(
                db,
                other.proposal_id,
                other.binding.user,
                other.binding.session,
                preview(other).digest,
            )
        except EditError as e:
            assert e.code == "proposal_expired"
        else:
            raise AssertionError("expired approval accepted")


def test_postgres_route_concurrent_approval_dispatches_once(
    postgres: Engine, harness: Harness
) -> None:
    from test_safe_edit import Provider, approve, prepare, running

    from forge_api.auth.runtime import AuthRuntime

    migrate(postgres)
    runtime = AuthRuntime.create(
        harness.runtime.settings, postgres, harness.runtime.provider.client
    )
    harness.runtime = runtime
    harness.client.app.state.auth = runtime  # type: ignore[attr-defined]
    fake = Provider()
    with running(harness, fake):
        p = prepare(harness)
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: approve(harness, p), range(4)))
        assert sum(r[-1].get("state") == "verified_success" for r in results) == 1
        assert fake.writes == 1


def test_logout_commits_before_final_authority_prevents_dispatch(
    postgres: Engine, harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    from threading import Event

    from test_safe_edit import Provider, approve, prepare, running

    from forge_api.auth.runtime import AuthRuntime

    migrate(postgres)
    runtime = AuthRuntime.create(
        harness.runtime.settings, postgres, harness.runtime.provider.client
    )
    harness.runtime = runtime
    harness.client.app.state.auth = runtime  # type: ignore[attr-defined]
    fake = Provider()
    with running(harness, fake):
        proposal = prepare(harness)
        headers = harness.headers()
        entered, release = Event(), Event()
        original = fake.handle

        def paused(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/currentmicroversion"):
                entered.set()
                assert release.wait(5), "test barrier timed out"
            return original(request)

        monkeypatch.setattr(fake, "handle", paused)
        with httpx.Client(transport=httpx.MockTransport(paused)) as transport:
            harness.client.app.state.cad_transport = transport  # type: ignore[attr-defined]
            with ThreadPoolExecutor(max_workers=2) as pool:
                pending = pool.submit(approve, harness, proposal)
                try:
                    assert entered.wait(5), "approval did not reach fresh read"
                    assert (
                        harness.client.post("/auth/logout", headers=headers).status_code
                        == 204
                    )
                finally:
                    release.set()
                events = pending.result(timeout=10)
        assert events[-1].get("code") == "session_expired"
        assert fake.writes == 0


def test_reauthorization_coordinates_before_user_row_lock(
    postgres: Engine, harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    from threading import Event

    from sqlalchemy import text

    from forge_api.auth.runtime import AuthRuntime
    from forge_api.db.coordination import user_lock

    migrate(postgres)
    runtime = AuthRuntime.create(
        harness.runtime.settings, postgres, harness.runtime.provider.client
    )
    harness.runtime = runtime
    harness.client.app.state.auth = runtime  # type: ignore[attr-defined]
    user = harness.login()
    state = harness.start()
    entered = Event()

    def observed(db: DatabaseSession, user_id: str) -> None:
        entered.set()
        user_lock(db, user_id)

    monkeypatch.setattr("forge_api.auth.routes.user_lock", observed)
    with ThreadPoolExecutor(max_workers=1) as pool:
        with runtime.sessions.begin() as db:
            user_lock(db, user)
            callback = pool.submit(harness.callback, state, code="synthetic-new-code")
            assert entered.wait(5)
            db.execute(text("SET LOCAL lock_timeout = '1s'"))
            # A write-record FK needs this key-share lock. The callback must be
            # waiting on the advisory lock without holding User FOR UPDATE.
            assert (
                db.scalar(
                    select(User.id)
                    .where(User.id == user)
                    .with_for_update(read=True, key_share=True)
                )
                == user
            )
        assert callback.result(timeout=5).status_code == 303
