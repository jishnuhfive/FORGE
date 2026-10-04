from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx2 as httpx
import pytest
from alembic import command
from alembic.config import Config
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from pydantic import AnyHttpUrl, SecretStr
from sqlalchemy import Engine, create_engine, select

from forge_api.auth.runtime import AuthRuntime
from forge_api.core.config import Settings
from forge_api.db.models import User
from forge_api.main import create_app


# Clearly synthetic fixtures. Random key material is never printed or persisted.
@dataclass
class MockOnshape:
    exchange_status: int = 200
    identity_status: int = 200
    refresh_status: int = 200
    refresh_error: str = "invalid_grant"
    identity_payload: object = field(
        default_factory=lambda: {"id": "synthetic-user", "name": "Test Engineer"}
    )
    rotated: bool = True
    malformed_token: bool = False
    network_error: bool = False
    calls: list[httpx.Request] = field(default_factory=list, repr=False)

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        if self.network_error:
            raise httpx.ConnectError("synthetic transport error", request=request)
        if request.url.path == "/api/users/sessioninfo":
            return httpx.Response(self.identity_status, json=self.identity_payload)
        assert request.url.path == "/oauth/token"
        values = parse_qs(request.content.decode())
        refresh = values["grant_type"] == ["refresh_token"]
        status = self.refresh_status if refresh else self.exchange_status
        if status != 200:
            return httpx.Response(status, json={"error": self.refresh_error})
        if self.malformed_token:
            return httpx.Response(200, json={"access_token": 42})
        payload: dict[str, object] = {
            "access_token": "synthetic-refreshed-access"
            if refresh
            else "synthetic-access",
            "token_type": "Bearer",
            "expires_in": 3600,
        }
        if not refresh or self.rotated:
            payload["refresh_token"] = (
                "synthetic-rotated-refresh" if refresh else "synthetic-refresh"
            )
        return httpx.Response(200, json=payload)


def migrate(engine: Engine) -> None:
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")


@dataclass
class Harness:
    client: TestClient
    runtime: AuthRuntime
    provider: MockOnshape
    engine: Engine

    def start(self) -> str:
        response = self.client.get("/auth/onshape/start", follow_redirects=False)
        assert response.status_code == 303
        return parse_qs(urlsplit(response.headers["location"]).query)["state"][0]

    def callback(self, state: str, **params: str) -> httpx.Response:
        return self.client.get(
            "/auth/onshape/callback",
            params={"state": state, **params},
            follow_redirects=False,
        )

    def login(self) -> str:
        assert (
            self.callback(self.start(), code="synthetic-code").headers["location"]
            == self.runtime.settings.origin + "/"
        )
        with self.runtime.sessions() as db:
            user_id = db.scalar(select(User.id))
            assert user_id is not None
            return user_id

    def headers(self) -> dict[str, str]:
        return {
            "Origin": self.runtime.settings.origin,
            "X-CSRF-Token": self.client.get("/api/me").json()["csrf_token"],
        }


@pytest.fixture
def harness(tmp_path: Path) -> Iterator[Harness]:
    url = "sqlite:///" + str(tmp_path / "auth.sqlite")
    engine = create_engine(url, hide_parameters=True)
    migrate(engine)
    settings = Settings(
        _env_file=None,
        environment="test",
        database_url=SecretStr(url),
        app_base_url=AnyHttpUrl("http://127.0.0.1:5173"),
        onshape_redirect_uri=AnyHttpUrl("http://127.0.0.1:5173/auth/onshape/callback"),
        onshape_client_id="synthetic-client",
        onshape_client_secret=SecretStr("synthetic-client-secret"),
        token_encryption_key=SecretStr(Fernet.generate_key().decode()),
    )
    provider = MockOnshape()
    with TestClient(create_app(settings), base_url=settings.origin) as client:
        runtime: AuthRuntime = client.app.state.auth  # type: ignore[attr-defined]
        with httpx.Client(
            transport=httpx.MockTransport(provider.handle), follow_redirects=False
        ) as transport:
            runtime.provider.client = transport
            yield Harness(client, runtime, provider, engine)
    engine.dispose()
