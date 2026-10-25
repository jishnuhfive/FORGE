import hashlib
import hmac
import secrets
from typing import Literal

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from sqlalchemy.orm import Session

from forge_api.core.config import Settings
from forge_api.db.models import AuditEvent

AuditKind = Literal[
    "write_proposal_created",
    "write_proposal_expired",
    "write_proposal_invalidated",
    "write_proposal_claimed",
    "write_proposal_cancelled",
    "write_dispatch_started",
    "write_provider_acknowledged",
    "write_verified",
    "write_failed",
    "write_uncertain",
    "write_rejected_stale",
    "write_reconciliation_required",
    "write_current_state_reconciled",
    "write_verification_failed",
    "write_operator_recovery",
    "write_retained_operator_recovery",
    "write_depth_operator_recovery",
    "login_started",
    "login_succeeded",
    "login_failed",
    "login_denied",
    "logout",
    "authorization_disconnected",
    "authorization_refreshed",
    "authorization_failed",
    "session_revoked",
]
AuditOutcome = Literal[
    "verify_serialization",
    "verify_library",
    "verify_target_identity",
    "verify_ack_revision",
    "verify_definitions",
    "verify_parent",
    "verify_configured",
    "verify_deadline",
    "verify_provider_ack",
    "verify_post_read",
    "verify_authority",
    "verify_internal",
    "ok",
    "denied",
    "invalid_state",
    "malformed",
    "provider_error",
    "revoked",
    "encryption_error",
    "local_only",
]


def random_token() -> str:
    return secrets.token_urlsafe(32)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def csrf_token(session_token: str) -> str:
    return hmac.new(
        session_token.encode(), b"forge.csrf.v1", hashlib.sha256
    ).hexdigest()


def audit(
    db: Session,
    kind: AuditKind,
    outcome: AuditOutcome = "ok",
    user_id: str | None = None,
) -> None:
    # Deliberately no arbitrary metadata, exception text, IPs, URLs or headers.
    db.add(AuditEvent(kind=kind, outcome=outcome, user_id=user_id))


class TokenCipher:
    def __init__(self, settings: Settings) -> None:
        if not settings.token_encryption_key:
            raise ValueError("Token encryption is not configured")
        keys = [settings.token_encryption_key.get_secret_value()]
        if settings.token_encryption_previous_keys:
            keys += settings.token_encryption_previous_keys.get_secret_value().split(
                ","
            )
        self._cipher = MultiFernet([Fernet(key.encode()) for key in keys])

    def encrypt(self, token: str) -> str:
        return "fernet:v1:" + self._cipher.encrypt(token.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        if not ciphertext.startswith("fernet:v1:"):
            raise InvalidToken
        try:
            return self._cipher.decrypt(ciphertext[10:].encode()).decode()
        except UnicodeError, ValueError:
            raise InvalidToken from None
