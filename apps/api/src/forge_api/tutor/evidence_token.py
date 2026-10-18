"""Session-bound proof of a deterministic check result, with no storage.

Check my step issues this token; the tutor accepts check results ONLY through it.
The key is derived from the caller's own session credential (the same idea as the
CSRF MAC), so a token cannot be replayed from another session, forged, or edited:
any change to the signed bytes fails verification. Nothing is persisted.
"""

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from forge_api.step_checks.bracket import STEPS
from forge_api.step_checks.model import RequirementResult

from .models import CheckOutcome, CheckStatus

VERSION: Literal[1] = 1
MAX_AGE_SECONDS = 3600
FUTURE_SKEW_SECONDS = 60
DOMAIN = b"forge.evidence.v1:"


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    id: str = Field(min_length=1, max_length=64)
    status: CheckStatus
    reason: str = Field(min_length=1, max_length=40)
    blocking: bool
    statement: str = Field(min_length=1, max_length=300)


class Payload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    v: Literal[1]
    lesson: str = Field(max_length=64)
    step: str = Field(max_length=64)
    outcome: CheckOutcome
    captured: str = Field(max_length=40)
    issued: int = Field(ge=0)
    findings: tuple[Finding, ...] = Field(min_length=1, max_length=8)


@dataclass(frozen=True)
class VerifiedCheck:
    lesson_id: str
    step_id: str
    outcome: CheckOutcome
    captured_at: str
    issued_at: int
    findings: tuple[Finding, ...]


class TokenError(Exception):
    """Forged, altered, foreign or malformed. Never says which."""


class TokenExpired(Exception):
    """Authentic but too old to describe the current model."""


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _mac(session_credential: str, body: bytes) -> bytes:
    key = DOMAIN + session_credential.encode()
    return hmac.new(key, body, hashlib.sha256).digest()


def issue(
    session_credential: str,
    *,
    lesson_id: str,
    step_id: str,
    outcome: str,
    captured_at: str,
    results: tuple[RequirementResult, ...],
    now: int,
) -> str:
    payload = Payload(
        v=VERSION,
        lesson=lesson_id,
        step=step_id,
        outcome=cast(CheckOutcome, outcome),
        captured=captured_at,
        issued=now,
        findings=tuple(
            Finding(
                id=item.requirement_id,
                status=item.outcome.status,
                reason=item.outcome.reason,
                blocking=item.blocking,
                statement=item.outcome.finding,
            )
            for item in results
        ),
    )
    body = json.dumps(
        payload.model_dump(mode="json"), separators=(",", ":"), sort_keys=True
    ).encode()
    return _b64(body) + "." + _b64(_mac(session_credential, body))


def verify(
    session_credential: str,
    token: str,
    *,
    lesson_id: str,
    step_id: str,
    now: int,
) -> VerifiedCheck:
    """Raise TokenError (forged/foreign/mismatched) or TokenExpired (stale)."""
    try:
        body_part, mac_part = token.split(".")
        body, mac = _unb64(body_part), _unb64(mac_part)
    except ValueError:
        raise TokenError from None
    if not hmac.compare_digest(mac, _mac(session_credential, body)):
        raise TokenError
    try:
        payload = Payload.model_validate_json(body)
    except ValidationError:
        raise TokenError from None
    # Authentic but must also describe exactly the step being asked about, and
    # may only name requirements the server's own checker defines for that step.
    if payload.lesson != lesson_id or payload.step != step_id:
        raise TokenError
    known = {r.id for r in STEPS.get(step_id, ())}
    if not known or any(f.id not in known for f in payload.findings):
        raise TokenError
    if payload.issued > now + FUTURE_SKEW_SECONDS:
        raise TokenError
    if now - payload.issued > MAX_AGE_SECONDS:
        raise TokenExpired
    return VerifiedCheck(
        lesson_id=payload.lesson,
        step_id=payload.step,
        outcome=payload.outcome,
        captured_at=payload.captured,
        issued_at=payload.issued,
        findings=payload.findings,
    )
