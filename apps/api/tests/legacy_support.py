"""Invented enrollment/settlement, synthetic CAD and isolated DBs ONLY.

The policy's user-supplied context is exercised with invented geometry; it never
selects real CAD. No live pins, receipts, credentials or provider captures are used.
"""

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

import httpx2 as httpx
import pytest
from conftest import Harness
from pydantic import SecretStr
from sqlalchemy import select
from test_modify_plan import PlanProvider, inventory
from test_modify_recovery import current
from test_safe_edit import M0, bodies, config

from forge_api.auth.provider import TokenResponse
from forge_api.cad_edits import (
    legacy_enrollment,
    legacy_policy,
    legacy_recovery,
    legacy_release,
    plan_storage,
    storage,
)
from forge_api.cad_edits.domain import Binding, fingerprint
from forge_api.cad_edits.legacy_contracts import (
    LegacyEnrollment,
    LegacyReview,
    ProviderSettlementEvidence,
    QuiescenceReview,
    SettlementReview,
    enrollment_fingerprint,
)
from forge_api.cad_edits.legacy_policy import CASE
from forge_api.cad_edits.plans import (
    ModifyPlan,
    PlanResult,
    ResolvedOperation,
    SetUnsuppressed,
    StoredPlan,
    Target,
)
from forge_api.db.models import (
    AuditEvent,
    OnshapeAuthorization,
    Session,
    WriteFence,
    WriteRecord,
)
from forge_api.integrations.onshape.contracts import WorkspaceReference
from forge_api.integrations.onshape.edit_registry import change
from forge_api.integrations.onshape.modify_evidence import project_modify_evidence

NOW = CASE.adoption_boundary + 3600


@dataclass
class LegacyCase:
    harness: Harness
    provider: PlanProvider
    enrollment: LegacyEnrollment
    review: LegacyReview

    def recover(self) -> Any:
        return legacy_recovery.retire_legacy_record(
            self.harness.runtime.sessions,
            self.harness.runtime.settings,
            self.harness.runtime.tokens,
            self.review,
            transport=httpx.MockTransport(self.provider.handle),
        )

    def snapshot(self) -> tuple[Any, ...]:
        with self.harness.runtime.sessions() as db:
            row = db.get(WriteRecord, self.enrollment.record_id)
            fences = tuple(
                (f.workspace_key, f.user_id, f.record_id)
                for f in db.scalars(select(WriteFence))
            )
            audits = tuple(
                (a.kind, a.outcome)
                for a in db.scalars(
                    select(AuditEvent).where(
                        AuditEvent.kind == "write_legacy_retained_retirement"
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


def seed_legacy(
    h: Harness, provider: PlanProvider, monkeypatch: pytest.MonkeyPatch
) -> LegacyCase:
    import hashlib

    for module in (legacy_policy, legacy_enrollment, legacy_release, storage):
        monkeypatch.setattr(module, "now", lambda: NOW)
    user = h.login()
    context = WorkspaceReference.model_validate(CASE.context.model_dump())
    data = inventory()
    data["features"][-1]["suppressed"] = True
    data["featureStates"][data["features"][-1]["featureId"]]["inactive"] = True
    baseline = project_modify_evidence(
        context, M0, data, config(M0), bodies(M0, explicit_flags=False)
    ).baseline
    target = Target(
        handle="A" * 43,
        feature_id=baseline.feature_id,
        feature_type="fillet",
        position=baseline.position,
    )
    operation = SetUnsuppressed(type="SET_UNSUPPRESSED", target=target.handle)
    _, preview = change(data["features"], target, operation)
    with h.runtime.sessions.begin() as db:
        original = db.scalar(select(Session).where(Session.user_id == user))
        grant = db.get(OnshapeAuthorization, user)
        assert original and grant
        original.created_at = CASE.proposal_created_at - 10
        original.expires_at = NOW - 1
        key = hashlib.sha256(
            (
                "forge.workspace-fence.v1:"
                + grant.stack
                + ":"
                + context.documentId
                + ":"
                + context.workspaceId
            ).encode()
        ).hexdigest()
        binding = Binding(
            user=user,
            session=original.token_hash,
            generation=grant.generation,
            context=context,
            workspace_key=key,
        )
        plan = ModifyPlan(
            proposal_id="B" * 43,
            binding=binding,
            baseline=baseline,
            created_at=CASE.proposal_created_at,
            expires_at=CASE.proposal_created_at + 120,
            operations=(
                ResolvedOperation(operation=operation, target=target, preview=preview),
            ),
        )
        saved = StoredPlan(
            plan=plan,
            result=PlanResult(
                state="execution_uncertain", operations=("execution_uncertain",)
            ),
        )
        digest = fingerprint(plan.model_dump(mode="json"))
        db.add(
            WriteRecord(
                id=plan.proposal_id,
                user_id=user,
                session_hash=original.token_hash,
                state="execution_uncertain",
                digest=digest,
                payload=saved.model_dump_json(),
                created_at=plan.created_at,
                expires_at=plan.expires_at,
                purge_at=plan.created_at + 900,
            )
        )
        db.add(WriteFence(workspace_key=key, user_id=user, record_id=plan.proposal_id))
        for index, kind in enumerate(
            (
                "write_proposal_claimed",
                "write_dispatch_started",
                "write_provider_acknowledged",
                "write_uncertain",
            )
        ):
            db.add(
                AuditEvent(
                    user_id=user,
                    kind=kind,
                    outcome="ok",
                    created_at=CASE.execution_start + index,
                )
            )
        grant.generation = "synthetic-legacy-current-generation"
        grant.granted_scope = "OAuth2Read OAuth2Write"
        enrollment = LegacyEnrollment(
            history_source="preserved_october20_conversation",
            history_evidence_digest="1" * 64,
            reviewer="synthetic-enrollment-reviewer",
            review_id="synthetic-enrollment-review",
            reviewed_at=NOW - 10,
            binding=binding,
            record_id=plan.proposal_id,
            fence_user=user,
            fence_workspace_key=key,
            fence_record_id=plan.proposal_id,
            plan_digest=digest,
            payload_fingerprint=fingerprint(saved.model_dump(mode="json")),
            created_at=1792513443,
            expires_at=1792513563,
            feature_id=baseline.feature_id,
            target_position=baseline.position,
            stack="https://cad.onshape.com/api",
            company_id=None,
            current_generation=grant.generation,
        )
        pin = enrollment_fingerprint(enrollment)
        settlement = SettlementReview(
            case_id=CASE.case_id,
            enrollment_fingerprint=pin,
            reviewer="synthetic-settlement-reviewer",
            review_id="synthetic-settlement-review",
            reviewed_at=NOW - 5,
            valid_until=NOW + 300,
            evidence=ProviderSettlementEvidence(
                category="provider_issued_terminal_confirmation",
                issuer="synthetic-provider",
                evidence_reference="synthetic-confirmation",
                evidence_digest="2" * 64,
                user=user,
                context=CASE.context,
                execution_start=CASE.execution_start,
                execution_end_exclusive=CASE.execution_end_exclusive,
                issued_at=NOW - 6,
                disposition="terminated_no_outstanding_activity_can_later_apply",
            ),
            disposition="approved_for_exact_legacy_retirement",
        )
        quiescence = QuiescenceReview(
            case_id=CASE.case_id,
            enrollment_fingerprint=pin,
            reviewer="synthetic-maintenance-reviewer",
            review_id="synthetic-maintenance-review",
            reviewed_at=NOW - 5,
            valid_until=NOW + 300,
            deployment_inventory_digest="3" * 64,
            write_admission_evidence_digest="4" * 64,
            worker_drain_evidence_digest="5" * 64,
            queue_inspection_digest="6" * 64,
            approval_inspection_digest="7" * 64,
            recovery_exclusion_digest="8" * 64,
            effective_writes_off=True,
            workers_drained=True,
            no_queued_same_user_write=True,
            no_resumable_historical_approval=True,
            original_session_hard_inactive=True,
            no_competing_recovery=True,
        )
        review = LegacyReview(settlement=settlement, quiescence=quiescence)
        h.runtime.tokens.remember(
            user,
            grant.generation,
            TokenResponse(
                access_token=SecretStr("synthetic-cached-legacy-read"),
                token_type="Bearer",
                expires_in=3600,
            ),
        )
    monkeypatch.setattr(legacy_policy, "_ENROLLMENT", enrollment)
    h.runtime.settings.environment = "development"
    h.runtime.settings.forge_cad_writes_enabled = False
    provider.data = deepcopy(data)
    current(provider, False)
    provider.calls.clear()
    return LegacyCase(h, provider, enrollment, review)


def saved(case: LegacyCase) -> StoredPlan:
    with case.harness.runtime.sessions() as db:
        row = db.get(WriteRecord, case.enrollment.record_id)
        assert row
        return plan_storage.load(row)
