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
    assert not config.forge_cad_writes_enabled


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


@pytest.mark.parametrize("scheme", ["postgresql", "postgresql+psycopg"])
def test_postgresql_url_normalization_preserves_encoded_material(scheme: str) -> None:
    suffix = (
        "synthetic:p%40ss%3Aword@postgres.railway.internal:5432/forge?sslmode=require"
    )
    config = Settings(database_url=SecretStr(scheme + "://" + suffix), _env_file=None)
    assert config.database_url is not None
    assert config.database_url.get_secret_value() == "postgresql+psycopg://" + suffix
    assert suffix not in repr(config)


@pytest.mark.parametrize(
    "value",
    [
        "mysql://host/db",
        "sqlite:///local.db",
        "https://host/db",
        "postgres://host/db",
        "postgresql+asyncpg://host/db",
        "postgresql://",
        "postgresql:///db",
        "postgresql://host",
        "postgresql://host/",
        "postgresql://host:bad/db",
        "postgresql://host:65536/db",
        "postgresql://host:0/db",
        "postgresql://host/db#fragment",
        "postgresql://ho st/db",
        "postgresql://host/db\n",
        "postgresql://[broken/db",
        "postgresql://user:%zz@host/db",
        "postgresql://host/db?x=%zz",
        "postgresql://user:p@ss@host/db",
    ],
)
def test_invalid_database_urls_are_rejected_without_disclosure(value: str) -> None:
    with pytest.raises(ValidationError) as caught:
        Settings(database_url=SecretStr(value), _env_file=None)
    assert value not in str(caught.value)


@pytest.mark.parametrize("host", ["POSTGRES.railway.internal", "[::1]"])
def test_valid_postgresql_hosts_are_preserved(host: str) -> None:
    value = "postgresql://synthetic:synthetic@" + host + ":5432/synthetic"
    config = Settings(database_url=SecretStr(value), _env_file=None)
    assert config.database_url is not None
    assert config.database_url.get_secret_value() == value.replace(
        "postgresql://", "postgresql+psycopg://", 1
    )
