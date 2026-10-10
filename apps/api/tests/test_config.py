import pytest
from pydantic import SecretStr, ValidationError

from forge_api.core.config import REPOSITORY_ROOT, Settings


@pytest.fixture(autouse=True)
def isolated_config(monkeypatch: pytest.MonkeyPatch) -> None:
    # Real local OAuth setup must not fill deliberately incomplete test settings.
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    for field in Settings.model_fields:
        monkeypatch.delenv(field.upper(), raising=False)


def test_config_finds_repository_and_ignores_empty_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "")
    monkeypatch.setenv("APP_BASE_URL", "")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    config = Settings(_env_file=None)
    assert (REPOSITORY_ROOT / "AGENTS.md").is_file()
    assert config.environment == "development"
    assert str(config.app_base_url) == "http://127.0.0.1:5173/"
    assert config.database_url is None


def test_invalid_environment_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate({"environment": "unknown"})


def test_sensitive_database_configuration_is_redacted() -> None:
    local_placeholder = (
        "postgresql+psycopg://placeholder:placeholder@localhost/placeholder"
    )
    config = Settings(database_url=SecretStr(local_placeholder), _env_file=None)
    assert local_placeholder not in repr(config)


@pytest.mark.parametrize(
    "values",
    [
        {"environment": "production"},
        {"app_base_url": "http://public.example"},
        {"app_base_url": "https://forge.example/nested"},
        {"session_samesite": "none"},
        {"onshape_redirect_uri": "https://attacker.invalid/callback"},
        {"onshape_api_base_url": "https://cad.onshape.com.attacker.invalid/api"},
        {"onshape_api_base_url": "http://cad.onshape.com/api"},
        {"onshape_token_url": "https://oauth.onshape.com/oauth/token?secret=value"},
        {"onshape_authorization_url": "https://oauth.onshape.com/other"},
        {"onshape_company_id": "bad-company"},
        {"token_encryption_key": "not-an-encryption-key"},
        {"database_url": "sqlite:///local.sqlite"},
        {"session_lifetime_seconds": 999999},
    ],
)
def test_unsafe_configuration_is_rejected(values: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate(values)
