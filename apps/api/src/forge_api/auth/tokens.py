"""Serialize refreshes with PostgreSQL row locks; persist no access tokens."""

from dataclasses import dataclass, field
from threading import Lock

from cryptography.fernet import InvalidToken
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from forge_api.auth.provider import OnshapeProvider, ProviderError, TokenResponse
from forge_api.auth.security import TokenCipher, audit
from forge_api.cad_edits.storage import invalidate
from forge_api.db.coordination import user_lock
from forge_api.db.models import OnshapeAuthorization, User, identifier, now


@dataclass
class CachedToken:
    generation: str
    expires_at: int
    value: str = field(repr=False)


class TokenManager:
    def __init__(
        self,
        sessions: sessionmaker[Session],
        provider: OnshapeProvider,
        cipher: TokenCipher,
    ) -> None:
        self.sessions = sessions
        self.provider = provider
        self.cipher = cipher
        self._cache: dict[str, CachedToken] = {}
        self._lock = Lock()

    def remember(self, user_id: str, generation: str, token: TokenResponse) -> None:
        with self._lock:
            self._cache = {
                key: value
                for key, value in self._cache.items()
                if value.expires_at > now() + 30
            }
            if len(self._cache) >= 1024:
                self._cache.pop(next(iter(self._cache)))
            self._cache[user_id] = CachedToken(
                generation,
                now() + token.expires_in,
                token.access_token.get_secret_value(),
            )

    def forget(self, user_id: str) -> None:
        with self._lock:
            self._cache.pop(user_id, None)

    def cached_read_credential(
        self,
        user_id: str,
        generation: str,
        granted_scope: str | None,
        *,
        capture_seconds: int,
    ) -> SecretStr:
        """Cache only. Caller must hold/validate the exact current grant row.

        No database access, provider request, refresh, persistence or cache write.
        This cannot bootstrap a separate operator process without a cached token.
        """
        if (
            type(capture_seconds) is not int
            or not 30 <= capture_seconds <= 40
            or not granted_scope
            or "OAuth2Read" not in granted_scope.split()
        ):
            raise ProviderError
        with self._lock:
            cached = self._cache.get(user_id)
            if (
                cached is None
                or cached.generation != generation
                or cached.expires_at <= now() + capture_seconds
            ):
                raise ProviderError
            return SecretStr(cached.value)

    def get_valid_onshape_access_token(self, user_id: str) -> str:
        failure: ProviderError | None = None
        result = ""
        with self.sessions.begin() as db:
            user_lock(db, user_id)
            auth = db.scalar(
                select(OnshapeAuthorization)
                .where(OnshapeAuthorization.user_id == user_id)
                .with_for_update()
            )
            if (
                auth is None
                or auth.status in ("revoked", "disconnected")
                or auth.stack != str(self.provider.settings.onshape_api_base_url)
                or auth.company_id != self.provider.settings.onshape_company_id
            ):
                raise ProviderError(revoked=True)
            if auth.retry_after and auth.retry_after > now():
                raise ProviderError
            with self._lock:
                cached = self._cache.get(user_id)
            if (
                auth.status == "connected"
                and cached
                and cached.generation == auth.generation
                and cached.expires_at > now() + 30
            ):
                return cached.value
            try:
                if not auth.encrypted_refresh_token:
                    raise InvalidToken
                token = self.provider.refresh(
                    self.cipher.decrypt(auth.encrypted_refresh_token)
                )
                if token.refresh_token:
                    auth.encrypted_refresh_token = self.cipher.encrypt(
                        token.refresh_token.get_secret_value()
                    )
                # If omitted, retain the prior refresh token, per OAuth semantics.
                auth.access_expires_at = now() + token.expires_in
                if token.scope is not None:
                    auth.granted_scope = token.scope
                auth.status = "connected"
                auth.retry_after = None
                auth.updated_at = now()
                auth.generation = identifier()
                audit(db, "authorization_refreshed", user_id=user_id)
                result = token.access_token.get_secret_value()
            except InvalidToken:
                auth.status = "error"
                auth.encrypted_refresh_token = None
                auth.access_expires_at = None
                auth.generation = identifier()
                audit(db, "authorization_failed", "encryption_error", user_id)
                failure = ProviderError()
            except ProviderError as error:
                auth.status = "revoked" if error.revoked else "error"
                auth.retry_after = None if error.revoked else now() + 60
                if error.revoked:
                    auth.encrypted_refresh_token = None
                    auth.disconnected_at = now()
                auth.access_expires_at = None
                auth.generation = identifier()
                audit(
                    db,
                    "authorization_failed",
                    "revoked" if error.revoked else "provider_error",
                    user_id,
                )
                failure = error
            invalidate(db, user_id)
            generation = auth.generation
        # Publish cache only after committing the replacement refresh token.
        if failure:
            self.forget(user_id)
            raise failure
        self.remember(user_id, generation, token)
        return result

    def check_identity(self, user_id: str) -> None:
        token = self.get_valid_onshape_access_token(user_id)
        failure: ProviderError | None = None
        with self.sessions.begin() as db:
            user_lock(db, user_id)
            auth = db.scalar(
                select(OnshapeAuthorization)
                .where(OnshapeAuthorization.user_id == user_id)
                .with_for_update()
            )
            with self._lock:
                cached = self._cache.get(user_id)
            # A concurrent login/refresh/disconnect must not be overwritten by a
            # result obtained with credentials from the preceding generation.
            if (
                auth is None
                or auth.status != "connected"
                or cached is None
                or cached.generation != auth.generation
                or cached.value != token
            ):
                raise ProviderError
            try:
                identity = self.provider.identity(token)
                user = db.get(User, user_id)
                if user is None or identity.id != user.onshape_user_id:
                    raise ProviderError(revoked=True)
                auth.verified_at = now()
            except ProviderError as error:
                auth.status = "revoked" if error.revoked else "error"
                auth.generation = identifier()
                auth.retry_after = None if error.revoked else now() + 60
                if error.revoked:
                    auth.encrypted_refresh_token = None
                    auth.access_expires_at = None
                    auth.disconnected_at = now()
                audit(
                    db,
                    "authorization_failed",
                    "revoked" if error.revoked else "provider_error",
                    user_id,
                )
                invalidate(db, user_id)
                failure = error
        if failure:
            self.forget(user_id)
            raise failure
