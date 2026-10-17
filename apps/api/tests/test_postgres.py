"""Opt-in real PostgreSQL tests. Every run owns and removes only its random schema."""

import os
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from urllib.parse import parse_qs
from uuid import uuid4

import httpx2 as httpx
import pytest
from alembic import command
from alembic.config import Config
from conftest import migrate
from cryptography.fernet import Fernet
from pydantic import SecretStr
from sqlalchemy import Engine, create_engine, insert, inspect, select, text, update

from forge_api.auth.runtime import AuthRuntime
from forge_api.auth.security import digest, random_token
from forge_api.core.config import REPOSITORY_ROOT, Settings
from forge_api.db.database import verify_schema
from forge_api.db.models import OAuthState, OnshapeAuthorization, User, now


@pytest.fixture
def postgres() -> Iterator[Engine]:
    url = os.environ.get("FORGE_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set FORGE_TEST_DATABASE_URL for isolated real PostgreSQL tests")
    schema = "forge_auth_test_" + uuid4().hex
    admin = create_engine(url, hide_parameters=True)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(
        url, hide_parameters=True, connect_args={"options": f"-csearch_path={schema}"}
    )
    try:
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def test_fresh_upgrade_current_schema_and_no_schema_drift(postgres: Engine) -> None:
    assert inspect(postgres).get_table_names() == []
    migrate(postgres)
    verify_schema(postgres)
    migrate(postgres)
    assert set(inspect(postgres).get_table_names()) == {
        "alembic_version",
        "users",
        "onshape_authorizations",
        "sessions",
        "oauth_states",
        "user_preferences",
        "audit_events",
        "write_records",
        "write_fences",
    }
    config = Config(str(REPOSITORY_ROOT / "apps/api/alembic.ini"))
    with postgres.begin() as connection:
        config.attributes["connection"] = connection
        command.check(config)


def test_concurrent_state_consumption_has_exactly_one_winner(postgres: Engine) -> None:
    migrate(postgres)
    state, browser = digest(random_token()), digest(random_token())
    with postgres.begin() as connection:
        connection.execute(
            insert(OAuthState).values(
                state_hash=state, browser_hash=browser, expires_at=now() + 600
            )
        )

    def consume(_: int) -> str | None:
        with postgres.begin() as connection:
            return connection.scalar(
                update(OAuthState)
                .where(
                    OAuthState.state_hash == state,
                    OAuthState.browser_hash == browser,
                    OAuthState.consumed_at.is_(None),
                )
                .values(consumed_at=now())
                .returning(OAuthState.state_hash)
            )

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(consume, range(4)))
    assert results.count(state) == 1


def test_independent_workers_serialize_rotating_refresh(postgres: Engine) -> None:
    migrate(postgres)
    lock = Lock()
    rotation = [0]

    def provider(request: httpx.Request) -> httpx.Response:
        body = parse_qs(request.content.decode())
        with lock:
            assert body["refresh_token"] == [f"synthetic-refresh-{rotation[0]}"]
            rotation[0] += 1
            return httpx.Response(
                200,
                json={
                    "access_token": f"synthetic-access-{rotation[0]}",
                    "refresh_token": f"synthetic-refresh-{rotation[0]}",
                    "expires_in": 3600,
                    "token_type": "Bearer",
                },
            )

    config = Settings(
        _env_file=None,
        environment="test",
        token_encryption_key=SecretStr(Fernet.generate_key().decode()),
    )
    with httpx.Client(transport=httpx.MockTransport(provider)) as client:
        workers = [AuthRuntime.create(config, postgres, client) for _ in range(4)]
        with workers[0].sessions.begin() as db:
            user = User(
                onshape_user_id="synthetic-concurrent",
                display_name="Concurrent test",
                stack="https://cad.onshape.com/api",
            )
            db.add(user)
            db.flush()
            user_id = user.id
            db.add(
                OnshapeAuthorization(
                    user_id=user_id,
                    stack=user.stack,
                    encrypted_refresh_token=workers[0].cipher.encrypt(
                        "synthetic-refresh-0"
                    ),
                )
            )
        with ThreadPoolExecutor(max_workers=4) as pool:
            tokens = list(
                pool.map(
                    lambda runtime: runtime.tokens.get_valid_onshape_access_token(
                        user_id
                    ),
                    workers,
                )
            )
        assert len(set(tokens)) == 4
        assert rotation[0] == 4
        with workers[0].sessions() as db:
            grant = db.scalar(select(OnshapeAuthorization))
            assert grant and grant.encrypted_refresh_token
            assert (
                workers[0].cipher.decrypt(grant.encrypted_refresh_token)
                == "synthetic-refresh-4"
            )
