"""Internal dev operator coordinator. No route, browser or AI registration.

Trusted review/settlement/draining happen BEFORE entry. Requires this process to
already own the exact cached read credential; never bootstrap or refresh a token.
"""

from time import monotonic

import httpx2 as httpx
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from forge_api.auth.provider import ProviderError
from forge_api.auth.runtime import AuthRuntime
from forge_api.auth.tokens import TokenManager
from forge_api.core.config import Settings
from forge_api.db.coordination import user_lock
from forge_api.db.models import (
    AuditEvent,
    OnshapeAuthorization,
    WriteFence,
    WriteRecord,
)
from forge_api.integrations.onshape.depth_reader import DepthEvidenceReader

from . import plan_storage
from .depth_contracts import (
    CAPTURE_SECONDS,
    HANDOFF_SECONDS,
    TRANSACTION_SECONDS,
    DepthRecoveryDenied,
    DepthReference,
    DepthResult,
    DevelopmentIncidentReview,
    DevelopmentOperatorReview,
    HistoricalPlanReference,
    IndependentSettlement,
    ServerAttestedDepthReference,
    ServerAttestedDepthResult,
    ServerAttestedDevelopmentApproval,
)
from .depth_release import lock_depth_record, release_depth_record
from .domain import EditError, fingerprint


def recover_depth_record(
    sessions: sessionmaker[Session],
    settings: Settings,
    tokens: TokenManager,
    reference: DepthReference,
    *,
    transport: httpx.BaseTransport | None = None,
) -> DepthResult:
    """Return success only after commit. No retries, including lost commit replies.

    `transport` is an owned synthetic transport injection for offline tests; the
    dedicated reader enforces fixed GETs even on an injected transport.
    """
    started = monotonic()
    try:
        with sessions.begin() as db:
            result = _recover_locked(
                db, settings, tokens, reference, started, transport
            )
        return result
    except ProviderError:
        raise DepthRecoveryDenied("cached_read_credential_required") from None
    except SQLAlchemyError:
        raise DepthRecoveryDenied("recovery_transaction_failed") from None


def _recover_locked(
    db: Session,
    settings: Settings,
    tokens: TokenManager,
    reference: DepthReference,
    started: float,
    transport: httpx.BaseTransport | None,
) -> DepthResult:
    _transaction_limits(db)
    run, scope = lock_depth_record(db, settings, reference, started=started)
    run._current(db)
    credential = tokens.cached_read_credential(
        reference.approval.user,
        reference.review.current_generation,
        scope,
        capture_seconds=CAPTURE_SECONDS,
    )
    reader = DepthEvidenceReader(
        reference.review.stack,
        reference.approval.context,
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


def _development_reference(
    db: Session,
    settings: Settings,
    review: DevelopmentIncidentReview,
) -> ServerAttestedDepthReference:
    if settings.environment != "development" or settings.forge_cad_writes_enabled:
        raise DepthRecoveryDenied("development_writes_off_required")
    if not all(
        (
            review.operator_authorized,
            review.server_attested_policy_accepted,
            review.disposable_fixture,
            review.writers_drained,
            review.upstream_settled,
        )
    ):
        raise DepthRecoveryDenied("development_incident_review_required")
    if (
        review.stack != str(settings.onshape_api_base_url)
        or review.company_id != settings.onshape_company_id
    ):
        raise DepthRecoveryDenied("reviewed_configuration_mismatch")
    fences = list(db.scalars(select(WriteFence).limit(2)))
    if len(fences) != 1:
        raise DepthRecoveryDenied("unique_development_incident_required")
    fence = fences[0]
    user_lock(db, fence.user_id)
    record = db.get(WriteRecord, fence.record_id)
    if (
        record is None
        or record.state != "execution_uncertain"
        or record.payload is None
        or len(record.payload.encode()) > 65536
    ):
        raise DepthRecoveryDenied("exact_aged_uncertain_record_required")
    try:
        saved = plan_storage.load(record)
    except EditError:
        raise DepthRecoveryDenied("retained_payload_invalid") from None
    plan = saved.plan
    if (
        len(plan.operations) != 1
        or plan.operations[0].operation.type != "SET_EXTRUDE_DEPTH"
    ):
        raise DepthRecoveryDenied("unsupported_depth_operation")
    operation = plan.operations[0]
    assert operation.operation.type == "SET_EXTRUDE_DEPTH"
    grant = db.get(OnshapeAuthorization, fence.user_id)
    if grant is None:
        raise DepthRecoveryDenied("current_connected_read_grant_required")
    return ServerAttestedDepthReference(
        approval=ServerAttestedDevelopmentApproval(
            user=plan.binding.user,
            context=plan.binding.context,
            plan_digest=record.digest,
            record_id=record.id,
            quantity=operation.operation.quantity,
            target_feature_id=operation.target.feature_id,
            target_position=operation.target.position,
        ),
        settlement=IndependentSettlement(
            source="independently_reviewed_upstream_settlement",
            settled=True,
            evidence_digest=fingerprint(review.settlement_review),
        ),
        historical=HistoricalPlanReference(
            record_id=record.id,
            binding=plan.binding,
            plan_digest=record.digest,
            payload_fingerprint=fingerprint(saved.model_dump(mode="json")),
            created_at=record.created_at,
            expires_at=record.expires_at,
        ),
        review=DevelopmentOperatorReview(
            operator_authorized=review.operator_authorized,
            server_attested_policy_accepted=review.server_attested_policy_accepted,
            disposable_fixture=review.disposable_fixture,
            writers_drained=review.writers_drained,
            upstream_settled=review.upstream_settled,
            stack=review.stack,
            company_id=review.company_id,
            current_generation=grant.generation,
        ),
    )


def recover_development_depth_incident(
    runtime: AuthRuntime,
    review: DevelopmentIncidentReview,
    *,
    transport: httpx.BaseTransport | None = None,
) -> ServerAttestedDepthResult:
    """Trusted in-process operator only. No external IDs or approval receipt.

    Trusts server records/code/audits, not independent approval provenance. Only
    the unique disposable development incident is eligible. Never retries, refreshes
    credentials, or contacts CAD except the fixed bounded GET capture. The caller
    must already own this runtime and its cached read credential.
    """
    started = monotonic()
    try:
        with runtime.sessions.begin() as db:
            _transaction_limits(db)
            reference = _development_reference(db, runtime.settings, review)
            result = _recover_locked(
                db, runtime.settings, runtime.tokens, reference, started, transport
            )
        if not isinstance(result, ServerAttestedDepthResult):
            raise DepthRecoveryDenied("completion_unconfirmed_no_retry")
        # Confirm the exact committed tombstone and denial removal read-only.
        with runtime.sessions.begin() as db:
            _transaction_limits(db)
            if db.get_bind().dialect.name == "postgresql":
                db.execute(text("SET TRANSACTION READ ONLY"))
            row = db.get(WriteRecord, reference.historical.record_id)
            related = db.scalar(
                select(WriteFence).where(
                    (WriteFence.user_id == reference.approval.user)
                    | (
                        WriteFence.workspace_key
                        == reference.historical.binding.workspace_key
                    )
                    | (WriteFence.record_id == reference.historical.record_id)
                )
            )
            events = list(
                db.scalars(
                    select(AuditEvent).where(
                        AuditEvent.user_id == reference.approval.user,
                        AuditEvent.kind == "write_depth_development_recovery",
                        AuditEvent.created_at >= reference.historical.created_at,
                    )
                )
            )
            if (
                row is None
                or row.state != "operator_recovered"
                or row.payload != result.model_dump_json()
                or row.digest != reference.historical.plan_digest
                or row.user_id != reference.approval.user
                or row.session_hash != reference.historical.binding.session
                or related is not None
                or len(events) != 1
                or events[0].outcome != "local_only"
                or events[0].created_at != result.recovered_at
            ):
                raise DepthRecoveryDenied("completion_unconfirmed_no_retry")
        return result
    except ProviderError:
        raise DepthRecoveryDenied("cached_read_credential_required") from None
    except EditError:
        raise DepthRecoveryDenied("retained_payload_invalid") from None
    except SQLAlchemyError:
        raise DepthRecoveryDenied("recovery_transaction_failed_no_retry") from None
    except DepthRecoveryDenied:
        raise
    except Exception:
        # Commit may have completed. Never expose arbitrary exception text or retry.
        raise DepthRecoveryDenied("completion_unconfirmed_no_retry") from None


def _transaction_limits(db: Session) -> None:
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text("SET LOCAL lock_timeout = '2000ms'"))
        db.execute(text("SET LOCAL statement_timeout = '35000ms'"))
        db.execute(text("SET LOCAL idle_in_transaction_session_timeout = '40000ms'"))
