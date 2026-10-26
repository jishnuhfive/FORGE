"""Operator-only closure of one partially executed creation incident.

No route, browser, AI or approval path reaches this module. It never writes CAD:
evidence comes from fixed GETs over a GET-only transport using the operator
process's already cached read credential (never refreshed or bootstrapped).

Closure preserves the historical ``execution_uncertain`` fact (the stored payload
and step states are untouched), moves the record to the existing closed state
``operator_recovered``, removes exactly the one matching fence and writes one fixed
local-only audit event. It does not verify, continue, retry or clean up anything.
"""

import hashlib
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, cast

import httpx2 as httpx
from pydantic import Field
from sqlalchemy import delete, select, text, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from forge_api.auth.provider import ProviderError
from forge_api.auth.runtime import AuthRuntime
from forge_api.cad_edits.domain import Closed, EditError, fingerprint
from forge_api.core.config import Settings
from forge_api.db.coordination import user_lock
from forge_api.db.models import (
    AuditEvent,
    OnshapeAuthorization,
    WriteFence,
    WriteRecord,
    now,
)
from forge_api.integrations.onshape.write_client import SafeEditClient

from .evidence import CreationEvidence, difference
from .models import CreateSketchRect
from .plane_filter import structure
from .provider import AckRejected, acknowledge, feature
from .service import Approval, StoredCreation, load

CONFIRMATION = (
    "The original FORGE Creation execution remains uncertain. A partial native "
    "sketch is present. The requested complete two-feature model was not verified. "
    "I authorize administrative closure of this exact incident without retrying or "
    "completing its CAD mutations."
)
_CLOSED = (
    "cancelled",
    "expired",
    "invalidated",
    "rejected_stale",
    "write_failed",
    "verified_success",
    "partial_failure",
    "reconciled_current_state",
    "operator_recovered",
)
_NON_EXECUTION = (
    "write_proposal_created",
    "write_proposal_expired",
    "write_proposal_invalidated",
    "write_proposal_cancelled",
)
_CAPTURE_SECONDS = 30
_MAX_CAPTURES = 4  # strict bound: one read set each, no further retry


class SettlementDenied(Exception):
    """Closed denial code only; never provider data or exception text."""


class SettlementReview(Closed):
    operator_authorized: bool
    disposable_fixture: bool
    writers_drained: bool
    upstream_settled: bool
    acknowledgement: str = Field(max_length=1024)
    settlement_review: str = Field(min_length=1, max_length=2048)
    stack: str = Field(max_length=255)
    company_id: str | None = None


@dataclass(frozen=True)
class Observation:
    """Sanitized facts about the current Part Studio; no identities or values."""

    stable: bool
    feature_count: int
    body_count: int
    sketch_named_and_healthy: bool
    revision_advanced: bool
    ack_check: str | None
    ack_fields: tuple[str, ...]
    denial: str | None
    captures: int = 0
    instability: str | None = None
    instability_path: tuple[str, ...] = ()
    ack_chain: tuple[str, ...] = ()
    filter_structures: tuple[str, ...] = ()


class _GetOnly(httpx.BaseTransport):
    def __init__(self, inner: httpx.BaseTransport) -> None:
        self._inner = inner

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        if request.method != "GET":
            raise SettlementDenied("read_only_transport")
        return self._inner.handle_request(request)


def _limits(db: Session) -> None:
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text("SET LOCAL lock_timeout = '2000ms'"))
        db.execute(text("SET LOCAL statement_timeout = '60000ms'"))
        db.execute(text("SET LOCAL idle_in_transaction_session_timeout = '70000ms'"))


def _workspace_key(stack: str, approval: Approval) -> str:
    context = approval.binding.context
    return hashlib.sha256(
        f"forge.workspace-fence.v1:{stack}:{context.documentId}:{context.workspaceId}".encode()
    ).hexdigest()


def _locate(
    db: Session, settings: Settings, review: SettlementReview, *, settle: bool
) -> tuple[WriteRecord, Approval, OnshapeAuthorization]:
    if settings.environment != "development" or settings.forge_cad_writes_enabled:
        raise SettlementDenied("development_writes_off_required")
    if not all(
        (
            review.operator_authorized,
            review.disposable_fixture,
            review.writers_drained,
            review.upstream_settled,
        )
    ):
        raise SettlementDenied("operator_review_required")
    if settle and review.acknowledgement != CONFIRMATION:
        raise SettlementDenied("exact_acknowledgement_required")
    if (
        review.stack != str(settings.onshape_api_base_url)
        or review.company_id != settings.onshape_company_id
    ):
        raise SettlementDenied("reviewed_configuration_mismatch")
    fences = list(db.scalars(select(WriteFence).limit(2)))
    if len(fences) != 1:
        raise SettlementDenied("unique_incident_required")
    fence = fences[0]
    user_lock(db, fence.user_id)
    record = db.scalar(
        select(WriteRecord)
        .where(WriteRecord.id == fence.record_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if (
        record is None
        or record.state != "execution_uncertain"
        or record.payload is None
        or len(record.payload.encode()) > 65536
    ):
        raise SettlementDenied("exact_uncertain_record_required")
    try:
        approval = load(record)
        stored = StoredCreation.model_validate_json(record.payload)
    except EditError, ValueError:
        raise SettlementDenied("creation_record_invalid") from None
    at = now()
    if (
        stored.steps[0] != "execution_uncertain"
        or any(s != "skipped" for s in stored.steps[1:])
        or not isinstance(approval.plan.steps[0].op, CreateSketchRect)
        or record.user_id != fence.user_id
        or approval.binding.user != fence.user_id
        or approval.binding.workspace_key != fence.workspace_key
        or record.created_at + 900 > at
        or record.expires_at > at
    ):
        raise SettlementDenied("exact_partial_creation_record_required")
    grant = db.get(OnshapeAuthorization, fence.user_id)
    if (
        grant is None
        or grant.status != "connected"
        or "OAuth2Read" not in (grant.granted_scope or "").split()
    ):
        raise SettlementDenied("current_connected_read_grant_required")
    if _workspace_key(grant.stack, approval) != fence.workspace_key:
        raise SettlementDenied("workspace_reference_mismatch")
    events = list(
        db.scalars(
            select(AuditEvent).where(
                AuditEvent.user_id == fence.user_id,
                AuditEvent.created_at >= record.created_at,
                AuditEvent.kind.startswith("write_"),
                AuditEvent.kind.not_in(_NON_EXECUTION),
            )
        )
    )
    kinds = sorted(e.kind for e in events)
    if kinds != sorted(
        ["write_proposal_claimed", "write_dispatch_started", "write_uncertain"]
    ) or any(e.outcome != "ok" for e in events if e.kind != "write_uncertain"):
        raise SettlementDenied("unique_partial_audit_required")
    other = db.scalar(
        select(WriteRecord.id)
        .where(
            WriteRecord.user_id == fence.user_id,
            WriteRecord.id != record.id,
            WriteRecord.state.not_in(_CLOSED),
            # Authority-free leftovers that only wait for the next cleanup: the
            # rate-limit placeholder and a preview that can no longer be claimed.
            WriteRecord.state != "admission",
            ~((WriteRecord.state == "pending") & (WriteRecord.expires_at <= at)),
        )
        .limit(1)
    )
    if other is not None:
        raise SettlementDenied("conflicting_user_operation")
    return record, approval, grant


def _capture(
    settings: Settings,
    token: str,
    approval: Approval,
    transport: httpx.BaseTransport | None,
) -> CreationEvidence:
    inner = (
        transport
        if transport is not None
        else httpx.HTTPTransport(retries=0, trust_env=False)
    )
    with httpx.Client(
        transport=_GetOnly(inner), follow_redirects=False, trust_env=False
    ) as client:
        reader = SafeEditClient(settings, client, token)
        return CreationEvidence.project(
            *reader._read_evidence(approval.binding.context)
        )


def _observe(
    runtime: AuthRuntime,
    approval: Approval,
    grant: OnshapeAuthorization,
    transport: httpx.BaseTransport | None,
) -> Observation:
    try:
        credential = runtime.tokens.cached_read_credential(
            approval.binding.user,
            grant.generation,
            grant.granted_scope,
            capture_seconds=_CAPTURE_SECONDS,
        )
    except ProviderError:
        raise SettlementDenied("cached_read_credential_required") from None
    token = credential.get_secret_value()
    captured: list[CreationEvidence] = []
    try:
        # Bounded quiescence: stable means two CONSECUTIVE identical full captures
        # (marker included). A moving revision or differing content never counts.
        while len(captured) < _MAX_CAPTURES:
            captured.append(_capture(runtime.settings, token, approval, transport))
            if len(captured) > 1 and captured[-1].digest == captured[-2].digest:
                break
    except SettlementDenied:
        raise
    except EditError as error:
        # A head that moves inside one read set is a moving revision, not a read error.
        raise SettlementDenied(
            "evidence_unsupported"
            if error.code == "unsupported_target"
            else "revision_still_moving"
            if error.code == "model_changed"
            else "evidence_unavailable"
        ) from None
    except Exception:
        raise SettlementDenied("evidence_unavailable") from None
    finally:
        del token, credential
    first = captured[-1]
    stable = len(captured) > 1 and first.digest == captured[-2].digest
    instability: str | None = None
    path: tuple[str, ...] = ()
    if not stable:
        # Report why the last two captures disagree, by category and name-only path.
        category, path = difference(captured[-2], first)
        instability = (
            "revision_still_moving" if category == "marker" else f"{category}_differs"
        )
    elif len(captured) > 2:
        # It settled, but earlier captures disagreed: say what moved first.
        category, path = difference(captured[0], captured[1])
        instability = f"settled_after_{category}_change"
    features = cast(list[dict[str, Any]], first.inventory["features"])
    step = approval.plan.steps[0]
    sketch = features[0] if len(features) == 1 else {}
    healthy = (
        sketch.get("featureType") == "newSketch"
        and sketch.get("name") == f"Forge {step.id}"
        and sketch.get("suppressed") is False
    )
    advanced = first.parts["marker"] != approval.baseline_parts.marker
    label: str | None = None
    names: tuple[str, ...] = ()
    chain: list[str] = []
    probe = dict(sketch)
    for _ in range(4):  # diagnostic only: peel unrecognized top-level keys to see more
        if not probe:
            break
        try:
            acknowledge(
                feature(step, {}),
                {
                    "microversionSkew": False,
                    "sourceMicroversion": first.marker,
                    "feature": probe,
                },
                cast(CreationEvidence, SimpleNamespace(marker="")),
            )
            break
        except AckRejected as error:
            chain.append(error.check)
            if label is None:
                label, names = error.check, error.names
            if error.check != "ack_feature_keys" or not error.names:
                break
            for name in error.names:
                probe.pop(name, None)
        except EditError:
            label = label or "ack_contract"
            break
    bodies = len(cast(list[Any], first.bodies["bodies"]))
    denial = (
        instability
        if not stable
        else "unexpected_feature_set"
        if len(features) != 1
        else "unexpected_feature"
        if not healthy
        else "unexpected_body"
        if bodies
        else "revision_not_advanced"
        if not advanced
        else None
    )
    return Observation(
        stable,
        len(features),
        bodies,
        healthy,
        advanced,
        label,
        names,
        denial,
        len(captured),
        instability,
        path,
        tuple(chain),
        tuple(
            structure(p["filter"])
            for p in cast(list[Any], sketch.get("parameters", []))[:4]
            if isinstance(p, dict) and "filter" in p
        ),
    )


def inspect_incident(
    runtime: AuthRuntime,
    review: SettlementReview,
    *,
    transport: httpx.BaseTransport | None = None,
) -> Observation:
    """Read-only: validates the record and reports sanitized current evidence."""
    try:
        with runtime.sessions() as db:
            _, approval, grant = _locate(db, runtime.settings, review, settle=False)
        return _observe(runtime, approval, grant, transport)
    except SQLAlchemyError:
        raise SettlementDenied("inspection_unavailable") from None


@dataclass(frozen=True)
class Settlement:
    disposition: str
    original_outcome: str
    recovered_at: int


def settle_incident(
    runtime: AuthRuntime,
    review: SettlementReview,
    *,
    transport: httpx.BaseTransport | None = None,
) -> Settlement:
    """One attempt. Commit failure or any doubt leaves the fence in place."""
    try:
        with runtime.sessions.begin() as db:
            _limits(db)
            record, approval, grant = _locate(db, runtime.settings, review, settle=True)
            observation = _observe(runtime, approval, grant, transport)
            if observation.denial is not None:
                raise SettlementDenied(observation.denial)
            raw = record.payload
            at = now()
            updated = list(
                db.scalars(
                    update(WriteRecord)
                    .where(
                        WriteRecord.id == record.id,
                        WriteRecord.user_id == approval.binding.user,
                        WriteRecord.state == "execution_uncertain",
                        WriteRecord.payload == raw,
                    )
                    .values(state="operator_recovered", purge_at=at + 900)
                    .returning(WriteRecord.id)
                )
            )
            removed = list(
                db.scalars(
                    delete(WriteFence)
                    .where(
                        WriteFence.user_id == approval.binding.user,
                        WriteFence.workspace_key == approval.binding.workspace_key,
                        WriteFence.record_id == record.id,
                    )
                    .returning(WriteFence.workspace_key)
                )
            )
            if len(updated) != 1 or len(removed) != 1:
                raise SettlementDenied("exact_record_and_fence_required")
            db.add(
                AuditEvent(
                    kind="write_creation_settlement",
                    outcome="local_only",
                    user_id=approval.binding.user,
                    created_at=at,
                )
            )
            record_id, user, workspace, payload_hash = (
                record.id,
                approval.binding.user,
                approval.binding.workspace_key,
                fingerprint(raw),
            )
        with runtime.sessions() as db:
            row = db.get(WriteRecord, record_id)
            fence = db.scalar(
                select(WriteFence).where(
                    (WriteFence.user_id == user)
                    | (WriteFence.workspace_key == workspace)
                    | (WriteFence.record_id == record_id)
                )
            )
            events = list(
                db.scalars(
                    select(AuditEvent).where(
                        AuditEvent.user_id == user,
                        AuditEvent.kind == "write_creation_settlement",
                    )
                )
            )
            if (
                row is None
                or row.state != "operator_recovered"
                or fingerprint(row.payload) != payload_hash
                or fence is not None
                or len(events) != 1
                or events[0].created_at != at
            ):
                raise SettlementDenied("completion_unconfirmed_no_retry")
        return Settlement(
            "independently_settled_partial_sketch", "execution_uncertain", at
        )
    except SettlementDenied:
        raise
    except Exception:
        # The commit may have happened; never retry and never expose the cause.
        raise SettlementDenied("completion_unconfirmed_no_retry") from None
