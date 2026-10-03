import pytest
from pydantic import SecretStr, ValidationError

from forge_api.core.config import REPOSITORY_ROOT, Settings


def test_config_finds_repository_and_ignores_empty_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "")
    monkeypatch.setenv("APP_BASE_URL", "")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    config = Settings(_env_file=None)
    assert (REPOSITORY_ROOT / "AGENTS.md").is_file()
    assert config.environment == "development"
    assert str(config.app_base_url) == "http://localhost:5173/"
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
