"""Invented receipts, temporary DB rows and mock CAD only. Never live fixtures."""

from copy import deepcopy
from dataclasses import dataclass

import httpx2 as httpx
from conftest import Harness
from pydantic import SecretStr
from sqlalchemy import select
from test_cad_read import REF
from test_modify_plan import PlanProvider
from test_modify_recovery import current, uncertain
from test_safe_edit import M0, bodies, config

from forge_api.auth.provider import TokenResponse
from forge_api.cad_edits import plan_storage, storage
from forge_api.cad_edits.depth_contracts import (
    DepthRecoveryReference,
    IndependentDepthApproval,
    IndependentSettlement,
    OperatorReview,
    PreservedHandle,
    build_depth_reference,
)
from forge_api.cad_edits.depth_recovery import recover_depth_record
from forge_api.cad_edits.domain import fingerprint
from forge_api.cad_edits.plans import StoredPlan
from forge_api.db.models import (
    AuditEvent,
    OnshapeAuthorization,
    Session,
    WriteFence,
    WriteRecord,
    now,
)
from forge_api.integrations.onshape.edit_registry import change


@dataclass
class DepthCase:
    harness: Harness
    provider: PlanProvider
    reference: DepthRecoveryReference

    def recover(self) -> object:
        return recover_depth_record(
            self.harness.runtime.sessions,
            self.harness.runtime.settings,
            self.harness.runtime.tokens,
            self.reference,
            transport=httpx.MockTransport(self.provider.handle),
        )

    def snapshot(self) -> tuple[object, ...]:
        with self.harness.runtime.sessions() as db:
            row = db.get(WriteRecord, self.reference.historical.record_id)
            fences = tuple(
                (f.workspace_key, f.user_id, f.record_id)
                for f in db.scalars(select(WriteFence))
            )
            audits = tuple(
                (a.kind, a.outcome)
                for a in db.scalars(
                    select(AuditEvent).where(
                        AuditEvent.kind == "write_depth_operator_recovery"
                    )
                )
            )
            return (
                None
                if row is None
                else (
                    row.state,
                    row.payload,
                    row.digest,
                    row.session_hash,
                    row.purge_at,
                ),
                fences,
                audits,
            )


def seed_depth(
    h: Harness, provider: PlanProvider, *, unsuppress: bool = False
) -> DepthCase:
    historical_data = deepcopy(provider.data)
    preview = uncertain(h, ("SET_EXTRUDE_DEPTH",))
    at = now() - 1000
    with h.runtime.sessions.begin() as db:
        row = db.get(WriteRecord, preview.proposal_id)
        assert row
        saved = plan_storage.load(row)
        plan = saved.plan.model_copy(update={"created_at": at, "expires_at": at + 120})
        saved = StoredPlan(plan=plan, result=saved.result)
        row.created_at, row.expires_at, row.purge_at = at, at + 120, at + 900
        row.digest = fingerprint(plan.model_dump(mode="json"))
        row.payload = saved.model_dump_json()
        # Simulate elapsed ordinary retention before administrative review.
        for other in db.scalars(select(WriteRecord).where(WriteRecord.id != row.id)):
            other.purge_at = now() - 1
        db.flush()
        storage.cleanup(db)
        session = db.get(Session, row.session_hash)
        assert session
        session.created_at, session.expires_at = at - 10, now() - 1
        db.add(
            Session(token_hash="a" * 64, user_id=row.user_id, expires_at=now() + 3600)
        )
        grant = db.get(OnshapeAuthorization, row.user_id)
        assert grant
        grant.generation = "synthetic-current-generation"
        grant.granted_scope = "OAuth2Read OAuth2Write"
        for event in db.scalars(
            select(AuditEvent).where(AuditEvent.kind == "write_proposal_claimed")
        ):
            event.created_at = at + 1
        for event in db.scalars(
            select(AuditEvent).where(AuditEvent.kind == "write_uncertain")
        ):
            event.created_at = at + 4
        db.add_all(
            [
                AuditEvent(
                    user_id=row.user_id,
                    kind="write_dispatch_started",
                    outcome="ok",
                    created_at=at + 2,
                ),
                AuditEvent(
                    user_id=row.user_id,
                    kind="write_provider_acknowledged",
                    outcome="ok",
                    created_at=at + 3,
                ),
            ]
        )
        # The independently preserved synthetic receipt anchors the handle from
        # preview, not a handle newly discovered by looking at a current fence.
        assert plan.operations[0].operation.type == "SET_EXTRUDE_DEPTH"
        independent = IndependentDepthApproval(
            source="previously_preserved_operation_receipt",
            receipt_digest="b" * 64,
            user=plan.binding.user,
            context=REF,
            operation="SET_EXTRUDE_DEPTH",
            quantity=plan.operations[0].operation.quantity,
            target_feature_id=plan.operations[0].target.feature_id,
            target_position=plan.operations[0].target.position,
            anchor=PreservedHandle(
                kind="preserved_record_handle", value=preview.proposal_id
            ),
        )
        review = OperatorReview(
            operator_authorized=True,
            independent_receipt_reviewed=True,
            writers_drained=True,
            upstream_settled=True,
            stack=grant.stack,
            company_id=grant.company_id,
            current_generation=grant.generation,
        )
        reference = build_depth_reference(
            independent,
            saved,
            review,
            IndependentSettlement(
                source="independently_reviewed_upstream_settlement",
                evidence_digest="c" * 64,
                settled=True,
            ),
        )
        h.runtime.tokens.remember(
            row.user_id,
            grant.generation,
            TokenResponse(
                access_token=SecretStr("synthetic-cached-read"),
                token_type="Bearer",
                expires_in=3600,
            ),
        )
    h.runtime.settings.environment = "development"
    h.runtime.settings.forge_cad_writes_enabled = False
    current(provider, False)
    operation = saved.plan.operations[0]
    updated, _ = change(
        provider.data["features"], operation.target, operation.operation
    )
    provider.data["features"][operation.target.position - 1] = updated
    original = provider.handle

    def handle(request: httpx.Request) -> httpx.Response:
        if f"/m/{M0}/" in request.url.path:
            provider.calls.append(request)
            assert request.method == "GET"
            if request.url.path.endswith("/features"):
                return httpx.Response(200, json=historical_data)
            if request.url.path.endswith("/configuration"):
                return httpx.Response(200, json=config(M0))
            if request.url.path.endswith("/bodydetails"):
                return httpx.Response(200, json=bodies(M0, explicit_flags=False))
            raise AssertionError("unexpected historical path")
        return original(request)

    provider.handle = handle  # type: ignore[method-assign]

    provider.calls.clear()
    return DepthCase(h, provider, reference)
