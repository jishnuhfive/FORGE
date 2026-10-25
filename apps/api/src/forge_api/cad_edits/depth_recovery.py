"""Internal dev operator coordinator. No route, CLI, browser or AI registration.

Trusted review/settlement/draining happen BEFORE entry. Requires this process to
already own the exact cached read credential; never bootstrap or refresh a token.
"""

from time import monotonic

import httpx2 as httpx
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from forge_api.auth.provider import ProviderError
from forge_api.auth.tokens import TokenManager
from forge_api.core.config import Settings
from forge_api.integrations.onshape.depth_reader import DepthEvidenceReader

from .depth_contracts import (
    CAPTURE_SECONDS,
    HANDOFF_SECONDS,
    TRANSACTION_SECONDS,
    DepthRecoveryDenied,
    DepthRecoveryReference,
    DepthRecoveryResult,
)
from .depth_release import lock_depth_record, release_depth_record


def recover_depth_record(
    sessions: sessionmaker[Session],
    settings: Settings,
    tokens: TokenManager,
    reference: DepthRecoveryReference,
    *,
    transport: httpx.BaseTransport | None = None,
) -> DepthRecoveryResult:
    """Return success only after commit. No retries, including lost commit replies.

    `transport` is an owned synthetic transport injection for offline tests; the
    dedicated reader enforces fixed GETs even on an injected transport.
    """
    started = monotonic()
    try:
        with sessions.begin() as db:
            if db.get_bind().dialect.name == "postgresql":
                db.execute(text("SET LOCAL lock_timeout = '2000ms'"))
                db.execute(text("SET LOCAL statement_timeout = '35000ms'"))
                db.execute(
                    text("SET LOCAL idle_in_transaction_session_timeout = '40000ms'")
                )
            run, scope = lock_depth_record(db, settings, reference, started=started)
            run._current(db)
            credential = tokens.cached_read_credential(
                reference.independent.user,
                reference.review.current_generation,
                scope,
                capture_seconds=CAPTURE_SECONDS,
            )
            reader = DepthEvidenceReader(
                reference.review.stack,
                reference.independent.context,
                credential,
                run.saved.plan.baseline.microversion,
                transport=transport,
            )
            del credential
            try:
                evidence = reader.capture(
                    reference,
                    run.saved,
                    deadline=started + TRANSACTION_SECONDS - HANDOFF_SECONDS,
                )
            finally:
                reader.close()
                del reader  # No reader/credential capability passed into release.
            run.register(evidence)
            result = release_depth_record(db, settings, run, evidence)
            run._current(db)
        return result
    except ProviderError:
        raise DepthRecoveryDenied("cached_read_credential_required") from None
    except SQLAlchemyError:
        raise DepthRecoveryDenied("recovery_transaction_failed") from None
