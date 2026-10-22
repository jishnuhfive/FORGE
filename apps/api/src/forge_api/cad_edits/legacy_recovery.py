"""Temporary operator-only coordinator. No entry point or automatic fallback.

No caller-selected case/reference. Reviewed proofs are not browser credentials.
No retry after failure, timeout, or an ambiguous/lost commit response.
"""

from time import monotonic

import httpx2 as httpx
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from forge_api.auth.provider import ProviderError
from forge_api.auth.tokens import TokenManager
from forge_api.core.config import Settings
from forge_api.integrations.onshape.legacy_reader import LegacyEvidenceReader

from .legacy_contracts import (
    CAPTURE_SECONDS,
    HANDOFF_SECONDS,
    TRANSACTION_SECONDS,
    LegacyRecoveryDenied,
    LegacyResult,
    LegacyReview,
    _LegacyRun,
)
from .legacy_enrollment import validate_locked
from .legacy_policy import require_enrollment
from .legacy_release import release_legacy_record


def retire_legacy_record(
    sessions: sessionmaker[Session],
    settings: Settings,
    tokens: TokenManager,
    review: LegacyReview,
    *,
    transport: httpx.BaseTransport | None = None,
) -> LegacyResult:
    enrollment = require_enrollment(settings, review)
    started = monotonic()
    try:
        with sessions.begin() as db:
            if db.get_bind().dialect.name == "postgresql":
                db.execute(text("SET LOCAL lock_timeout = '2000ms'"))
                db.execute(text("SET LOCAL statement_timeout = '35000ms'"))
                db.execute(
                    text("SET LOCAL idle_in_transaction_session_timeout = '40000ms'")
                )
            record, saved, scope = validate_locked(db, settings, enrollment, review)
            transaction = db.get_transaction()
            if transaction is None or db.in_nested_transaction():
                raise LegacyRecoveryDenied("legacy_root_transaction_required")
            assert record.payload is not None
            run = _LegacyRun(
                db, transaction, enrollment, review, saved, record.payload, started
            )
            run.current(db)
            credential = tokens.cached_read_credential(
                enrollment.binding.user,
                enrollment.current_generation,
                scope,
                capture_seconds=CAPTURE_SECONDS,
            )
            reader = LegacyEvidenceReader(
                enrollment.stack,
                enrollment.binding.context,
                credential,
                transport=transport,
            )
            del credential
            try:
                evidence = reader.capture_legacy(
                    enrollment,
                    review,
                    deadline=started + TRANSACTION_SECONDS - HANDOFF_SECONDS,
                )
            finally:
                reader.close()
                del reader
            run.register(evidence)
            result = release_legacy_record(db, settings, run, evidence)
            run.current(db)
            if require_enrollment(settings, review) != enrollment:
                raise LegacyRecoveryDenied("legacy_enrollment_changed")
        return result
    except ProviderError:
        raise LegacyRecoveryDenied("legacy_cached_read_credential_required") from None
    except SQLAlchemyError:
        raise LegacyRecoveryDenied("legacy_transaction_failed") from None
