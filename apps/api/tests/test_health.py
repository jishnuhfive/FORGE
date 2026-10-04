import pytest
from conftest import Harness
from fastapi.testclient import TestClient

from forge_api.core.config import Settings
from forge_api.main import create_app


def test_health_returns_safe_liveness_contract() -> None:
    with TestClient(create_app(Settings(_env_file=None))) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {"status": "ok", "service": "forge-api"}


@pytest.mark.parametrize("path", ["/auth/onshape", "/agent", "/cad"])
def test_product_endpoints_are_not_implemented(path: str) -> None:
    with TestClient(create_app(Settings(_env_file=None))) as client:
        assert client.get(path).status_code == 404


def test_production_disables_public_api_documentation(harness: Harness) -> None:
    values = harness.runtime.settings.model_dump()
    values.update(
        environment="production",
        app_base_url="https://forge.example",
        onshape_redirect_uri="https://forge.example/auth/onshape/callback",
        database_url="postgresql+psycopg://localhost/unused",
    )
    config = Settings.model_validate(values)
    # Liveness/documentation do not require running the persistence lifespan.
    client = TestClient(create_app(config))
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404
    assert client.get("/health").status_code == 200
