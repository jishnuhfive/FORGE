from dataclasses import dataclass

import httpx2 as httpx
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from forge_api.auth.provider import OnshapeProvider
from forge_api.auth.security import TokenCipher
from forge_api.auth.tokens import TokenManager
from forge_api.core.config import Settings
from forge_api.db.database import session_factory


@dataclass
class AuthRuntime:
    settings: Settings
    sessions: sessionmaker[Session]
    provider: OnshapeProvider
    cipher: TokenCipher
    tokens: TokenManager

    @classmethod
    def create(
        cls, settings: Settings, engine: Engine, client: httpx.Client
    ) -> AuthRuntime:
        sessions = session_factory(engine)
        provider = OnshapeProvider(settings, client)
        cipher = TokenCipher(settings)
        return cls(
            settings,
            sessions,
            provider,
            cipher,
            TokenManager(sessions, provider, cipher),
        )
