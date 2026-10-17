from pathlib import Path
from typing import Literal, Self
from urllib.parse import urlsplit

from cryptography.fernet import Fernet
from pydantic import AliasChoices, AnyHttpUrl, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPOSITORY_ROOT = Path(__file__).resolve().parents[5]


class Settings(BaseSettings):
    """Validated server-only configuration. No environment-selectable mock login."""

    model_config = SettingsConfigDict(
        env_file=REPOSITORY_ROOT / ".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
        hide_input_in_errors=True,
    )

    forge_cad_writes_enabled: bool = False
    forge_cad_write_conformance_pause_seconds: int = Field(default=0, ge=0, le=10)

    environment: Literal["development", "test", "production"] = "development"
    app_base_url: AnyHttpUrl = AnyHttpUrl("http://127.0.0.1:5173")
    database_url: SecretStr | None = None
    token_encryption_key: SecretStr | None = None
    token_encryption_previous_keys: SecretStr | None = None
    onshape_client_id: str | None = Field(
        default=None, min_length=1, max_length=256, pattern=r"^\S+$"
    )
    onshape_client_secret: SecretStr | None = Field(
        default=None, min_length=1, max_length=16384
    )
    onshape_redirect_uri: AnyHttpUrl | None = None
    onshape_authorization_url: AnyHttpUrl = AnyHttpUrl(
        "https://oauth.onshape.com/oauth/authorize"
    )
    onshape_token_url: AnyHttpUrl = AnyHttpUrl("https://oauth.onshape.com/oauth/token")
    onshape_api_base_url: AnyHttpUrl = AnyHttpUrl("https://cad.onshape.com/api")
    onshape_company_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{24}$")
    session_samesite: Literal["lax", "none"] = "lax"
    session_lifetime_seconds: int = Field(default=28800, ge=300, le=86400)
    session_idle_seconds: int = Field(default=3600, ge=60, le=28800)
    openai_api_key: SecretStr | None = Field(
        default=None, min_length=1, max_length=4096
    )
    forge_ai_provider: Literal["groq", "openai"] = "groq"
    groq_api_key: SecretStr | None = Field(default=None, min_length=1, max_length=4096)
    forge_groq_model: Literal["openai/gpt-oss-120b"] = "openai/gpt-oss-120b"
    forge_groq_reasoning_effort: Literal["low", "medium", "high"] = "low"
    forge_openai_model: Literal["gpt-6.1-sol"] = Field(
        default="gpt-6.1-sol",
        validation_alias=AliasChoices("forge_openai_model", "forge_ai_model"),
    )
    forge_openai_reasoning_effort: Literal["low", "medium", "high"] = Field(
        default="high",
        validation_alias=AliasChoices(
            "forge_openai_reasoning_effort", "forge_ai_reasoning_effort"
        ),
    )

    @property
    def ai_configured(self) -> bool:
        return bool(
            self.groq_api_key
            if self.forge_ai_provider == "groq"
            else self.openai_api_key
        )

    @property
    def secure_cookies(self) -> bool:
        return self.app_base_url.scheme == "https"

    @property
    def session_cookie(self) -> str:
        return "__Host-forge_session" if self.secure_cookies else "forge_session"

    @property
    def state_cookie(self) -> str:
        return "__Host-forge_oauth" if self.secure_cookies else "forge_oauth"

    @property
    def auth_configured(self) -> bool:
        return all(
            (
                self.database_url,
                self.token_encryption_key,
                self.onshape_client_id,
                self.onshape_client_secret,
                self.onshape_redirect_uri,
            )
        )

    @property
    def origin(self) -> str:
        return str(self.app_base_url).rstrip("/")

    @model_validator(mode="after")
    def validate_security(self) -> Self:
        if (
            self.forge_cad_write_conformance_pause_seconds
            and self.environment != "development"
        ):
            raise ValueError("Conformance pause is development-only")
        base = urlsplit(str(self.app_base_url))
        if base.path not in ("", "/") or base.query or base.fragment or base.username:
            raise ValueError("APP_BASE_URL must be an origin without a path")
        if base.scheme != "https" and base.hostname not in ("127.0.0.1", "localhost"):
            raise ValueError("APP_BASE_URL requires HTTPS outside loopback")
        if self.environment == "production" and not self.secure_cookies:
            raise ValueError("Production requires HTTPS")
        if self.session_samesite == "none" and not self.secure_cookies:
            raise ValueError("SameSite=None requires HTTPS")
        if self.onshape_redirect_uri and str(self.onshape_redirect_uri) != (
            self.origin + "/auth/onshape/callback"
        ):
            raise ValueError("Redirect must be APP_BASE_URL/auth/onshape/callback")
        for url in (
            self.onshape_authorization_url,
            self.onshape_token_url,
            self.onshape_api_base_url,
        ):
            parsed = urlsplit(str(url))
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or not parsed.hostname.endswith(".onshape.com")
                or parsed.username
                or parsed.password
                or parsed.query
                or parsed.fragment
                or parsed.port not in (None, 443)
            ):
                raise ValueError("Provider URLs must be HTTPS Onshape endpoints")
        if urlsplit(str(self.onshape_authorization_url)).path != "/oauth/authorize":
            raise ValueError("Invalid Onshape authorization path")
        if urlsplit(str(self.onshape_token_url)).path != "/oauth/token":
            raise ValueError("Invalid Onshape token path")
        if urlsplit(str(self.onshape_api_base_url)).path != "/api":
            raise ValueError("Onshape API base must end in /api")
        if self.database_url:
            value = self.database_url.get_secret_value()
            if not value.startswith("postgresql+psycopg://") and not (
                self.environment == "test" and value.startswith("sqlite")
            ):
                raise ValueError("PostgreSQL with psycopg is required")
        keys = [self.token_encryption_key]
        if self.token_encryption_previous_keys:
            keys += [
                SecretStr(k)
                for k in self.token_encryption_previous_keys.get_secret_value().split(
                    ","
                )
            ]
        for key in keys:
            if key:
                try:
                    Fernet(key.get_secret_value().encode())
                except ValueError, TypeError:
                    raise ValueError(
                        "Invalid token encryption key configuration"
                    ) from None
        if self.environment == "production" and not self.auth_configured:
            raise ValueError(
                "Production requires complete authentication configuration"
            )
        return self
