from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError

from forge_api.core.config import Settings
from forge_api.main import create_app
from forge_api.web import FRAME_ANCESTORS


@pytest.fixture(autouse=True)
def isolated_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)


@pytest.fixture
def web_build(tmp_path: Path) -> Path:
    (tmp_path / "assets").mkdir()
    (tmp_path / "brand").mkdir()
    (tmp_path / "index.html").write_text(
        '<html><div id="root">synthetic build</div></html>'
    )
    (tmp_path / "assets" / "app-abcd1234.js").write_text('console.log("synthetic");')
    (tmp_path / "brand" / "forge-icon.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"/>'
    )
    return tmp_path


@pytest.fixture
def production_values(web_build: Path) -> dict[str, object]:
    return {
        "environment": "production",
        "app_base_url": "https://forge.example",
        "database_url": "postgresql+psycopg://localhost/unused",
        "token_encryption_key": SecretStr(Fernet.generate_key().decode()),
        "onshape_client_id": "synthetic-client",
        "onshape_client_secret": SecretStr("synthetic-client-secret"),
        "onshape_redirect_uri": "https://forge.example/auth/onshape/callback",
        "web_build_dir": web_build,
    }


@pytest.fixture
def production_client(production_values: dict[str, object]) -> TestClient:
    # No lifespan: routing tests never connect to a DB or external provider.
    return TestClient(create_app(Settings.model_validate(production_values)))


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/extension",
        "/extension?documentId=synthetic&workspaceId=synthetic&elementId=synthetic",
    ],
)
def test_production_entrypoints(production_client: TestClient, path: str) -> None:
    response = production_client.get(path)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert 'id="root"' in response.text
    assert str(response.url).endswith(path)
    assert response.headers["content-security-policy"] == FRAME_ANCESTORS
    assert "x-frame-options" not in response.headers
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-content-type-options"] == "nosniff"


@pytest.mark.parametrize(
    "path,media",
    [
        ("/assets/app-abcd1234.js", "javascript"),
        ("/brand/forge-icon.svg", "image/svg+xml"),
    ],
)
def test_production_assets(
    production_client: TestClient, path: str, media: str
) -> None:
    response = production_client.get(path)
    assert response.status_code == 200
    assert media in response.headers["content-type"]


@pytest.mark.parametrize(
    "path",
    [
        "/api/missing",
        "/api",
        "/auth/missing",
        "/auth/onshape/callback/",
        "/api/me/",
        "/auth",
        "/health/missing",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/lab",
        "/src/main.tsx",
        "/.env",
        "/index.html",
        "/assets/missing.js",
        "/assets/%2e%2e/index.html",
        "/assets/%2e%2e/%2e%2e/.env",
        "/brand/%2e%2e/index.html",
    ],
)
def test_reserved_and_unknown_paths_never_receive_spa(
    production_client: TestClient, path: str
) -> None:
    response = production_client.get(path, follow_redirects=False)
    assert response.status_code == 404
    assert 'id="root"' not in response.text
    assert response.headers["content-security-policy"] == FRAME_ANCESTORS
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "x-frame-options" not in response.headers


def test_api_auth_health_and_error_precedence(production_client: TestClient) -> None:
    assert production_client.get("/api/me").json()["status"] == "signed_out"
    assert production_client.get("/health").json() == {
        "status": "ok",
        "service": "forge-api",
    }
    assert production_client.get("/auth/onshape/start").status_code == 503
    callback = production_client.get(
        "/auth/onshape/callback?code=synthetic", follow_redirects=False
    )
    assert callback.status_code == 303
    assert (
        callback.headers["location"]
        == "https://forge.example/#/auth/authorization_error"
    )
    assert callback.headers["content-security-policy"] == FRAME_ANCESTORS
    assert production_client.post("/extension").status_code == 405
    rejected = production_client.get("/extension?query=" + "x" * 8193)
    assert rejected.status_code == 400
    assert rejected.headers["content-security-policy"] == FRAME_ANCESTORS


def test_forwarding_headers_do_not_select_security_origin(
    production_values: dict[str, object],
) -> None:
    config = Settings.model_validate(production_values)
    client = TestClient(create_app(config), base_url="http://internal.invalid")
    response = client.get(
        "/auth/onshape/callback",
        headers={
            "Host": "untrusted.invalid",
            "X-Forwarded-Proto": "http",
            "X-Forwarded-Host": "untrusted.invalid",
            "X-Forwarded-For": "192.0.2.1",
        },
        follow_redirects=False,
    )
    assert response.headers["location"].startswith(config.origin + "/")
    assert "Secure" in response.headers["set-cookie"]
    assert "__Host-forge_oauth" in response.headers["set-cookie"]
    assert not config.forge_cad_writes_enabled
    assert not config.forge_safe_edit_diagnostics_enabled
    assert config.forge_cad_write_conformance_pause_seconds == 0
    assert config.session_samesite == "lax"


@pytest.mark.parametrize(
    "field",
    [
        "web_build_dir",
        "database_url",
        "token_encryption_key",
        "onshape_client_id",
        "onshape_client_secret",
        "onshape_redirect_uri",
    ],
)
def test_production_configuration_fails_closed(
    production_values: dict[str, object], field: str
) -> None:
    production_values[field] = None
    with pytest.raises(ValidationError):
        Settings.model_validate(production_values)


@pytest.mark.parametrize(
    "kind",
    [
        "relative",
        "missing",
        "no_index",
        "no_assets",
        "traversal",
        "root_link",
        "asset_link",
        "file_link",
        "development",
    ],
)
def test_static_path_validation(
    production_values: dict[str, object], web_build: Path, kind: str
) -> None:
    match kind:
        case "relative":
            production_values["web_build_dir"] = "apps/web/dist"
        case "missing":
            production_values["web_build_dir"] = web_build / "missing"
        case "no_index":
            (web_build / "index.html").unlink()
        case "no_assets":
            (web_build / "assets" / "app-abcd1234.js").unlink()
            (web_build / "assets").rmdir()
        case "traversal":
            production_values["web_build_dir"] = web_build / ".." / web_build.name
        case "root_link":
            link = web_build / "link"
            link.symlink_to(web_build, target_is_directory=True)
            production_values["web_build_dir"] = link
        case "asset_link":
            (web_build / "assets" / "escape").symlink_to(
                web_build.parent, target_is_directory=True
            )
        case "file_link":
            (web_build / "index.html").unlink()
            (web_build / "index.html").symlink_to(
                web_build / "brand" / "forge-icon.svg"
            )
        case "development":
            production_values["environment"] = "development"
    with pytest.raises(ValidationError):
        Settings.model_validate(production_values)


def test_development_does_not_serve_static() -> None:
    client = TestClient(create_app(Settings(_env_file=None)))
    assert client.get("/").status_code == 404
    assert client.get("/extension").status_code == 404


def test_static_failure_keeps_safe_error_headers(
    production_client: TestClient, web_build: Path
) -> None:
    (web_build / "index.html").unlink()
    response = production_client.get("/extension")
    assert response.status_code == 503
    assert response.json() == {"detail": "service_unavailable"}
    assert response.headers["content-security-policy"] == FRAME_ANCESTORS
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_untrusted_origin_does_not_change_frame_policy(
    production_client: TestClient,
) -> None:
    response = production_client.get(
        "/extension", headers={"Origin": "https://unapproved.invalid"}
    )
    assert response.headers["content-security-policy"] == FRAME_ANCESTORS
    assert "access-control-allow-origin" not in response.headers
    assert "x-frame-options" not in response.headers
