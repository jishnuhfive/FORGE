from pathlib import Path
from typing import Literal

from pydantic import AnyHttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

REPOSITORY_ROOT = Path(__file__).resolve().parents[5]


class Settings(BaseSettings):
    """Backend settings; optional integrations remain dormant during Phase 0."""

    model_config = SettingsConfigDict(
        env_file=REPOSITORY_ROOT / ".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    environment: Literal["development", "test", "production"] = "development"
    app_base_url: AnyHttpUrl = AnyHttpUrl("http://localhost:5173")
    database_url: SecretStr | None = None
    session_secret: SecretStr | None = None
    token_encryption_key: SecretStr | None = None
