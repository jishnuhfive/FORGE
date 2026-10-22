"""Invented synchronous acknowledgement pins; no live response or identity."""

import json
from typing import Any

import pytest
from conftest import Harness
from legacy_support import LegacyCase
from pydantic import ValidationError
from sqlalchemy import Engine, select
from test_legacy_recovery import case as case
from test_modify_plan import PlanProvider
from test_modify_plan_postgres import use_postgres
from test_postgres import postgres as postgres

from forge_api.cad_edits import legacy_enrollment, legacy_recovery, legacy_release
from forge_api.cad_edits.legacy_contracts import (
    LegacyRecoveryDenied,
    LegacyReview,
    SynchronousAcknowledgementEvidence,
    SynchronousAckPredicates,
)
from forge_api.cad_edits.legacy_policy import CASE
from forge_api.db.models import AuditEvent


def synchronous(case: LegacyCase) -> SynchronousAcknowledgementEvidence:
    with case.harness.runtime.sessions() as db:
        events = list(
            db.scalars(
                select(AuditEvent).where(
                    AuditEvent.user_id == case.enrollment.binding.user,
                    AuditEvent.kind.in_(legacy_enrollment._SEQUENCE),
                )
            )
        )
        digest = legacy_enrollment.audit_sequence_fingerprint(events)
        issued_at = next(
            e.created_at for e in events if e.kind == "write_provider_acknowledged"
        )
    return SynchronousAcknowledgementEvidence(
        category="synchronous_provider_acknowledgement",
        case_id=CASE.case_id,
        identity_basis="trusted_retained_database",
        review_basis="reviewer_accepted_october20_source_and_audit_history",
        endpoint="POST /api/v17/partstudios/d/{did}/w/{wid}/e/{eid}/features/updates",
        operation="SET_UNSUPPRESSED",
        reviewed_source_family="forge-a1-b728d422-682dfcf7",
        predicates=SynchronousAckPredicates(
            http_status=200,
            bounded_valid_json=True,
            returned_feature_count=1,
            approved_feature_id_matches=True,
            pre_dispatch_terminal_fillet_validated=True,
            result_suppressed=False,
            microversion_skew=False,
            result_microversion_valid=True,
            result_microversion_differs_from_baseline=True,
            consumed_single_operation_no_supported_replay=True,
        ),
        audit_sequence_digest=digest,
        user=case.enrollment.binding.user,
        context=CASE.context,
        execution_start=CASE.execution_start,
        execution_end_exclusive=CASE.execution_end_exclusive,
        issued_at=issued_at,
        disposition="acknowledged_document_mutation_terminal_no_supported_replay",
    )


def use_synchronous(case: LegacyCase) -> None:
    data = case.review.model_dump(mode="json")
    data["settlement"]["evidence"] = synchronous(case).model_dump(mode="json")
    case.review = LegacyReview.model_validate_json(json.dumps(data))


def test_distinct_reviewed_synchronous_category_can_close_synthetic_case(
    case: LegacyCase,
) -> None:
    use_synchronous(case)
    assert type(case.review.settlement.evidence) is SynchronousAcknowledgementEvidence
    result = case.recover()
    assert result.state == "operator_recovered"
    assert result.original_execution_outcome == "execution_uncertain"
    assert result.disposition == "legacy_administrative_retirement"
    assert len(case.provider.calls) == 5 and case.provider.writes == 0


@pytest.mark.parametrize(
    "field,value",
    [
        ("category", "provider_acknowledgement"),
        ("case_id", "another-incident"),
        ("identity_basis", "independent_receipt"),
        ("review_basis", "operator_says_settled"),
        ("endpoint", "POST /api/v17/partstudios/another-endpoint"),
        ("operation", "SET_SUPPRESSED"),
        ("reviewed_source_family", "current_binary"),
        ("execution_start", 1792513485),
        ("execution_end_exclusive", 1792513491),
        ("issued_at", 1792513485),
        ("issued_at", 1792513490),
        ("audit_sequence_digest", ""),
        ("predicates", True),
        ("disposition", "verified_success"),
        ("disposition", "current_cad_matches"),
        ("issuer", "invented-external-confirmation"),
    ],
)
def test_fixed_acknowledgement_contract_rejects_substitution(
    case: LegacyCase, field: str, value: Any
) -> None:
    data = synchronous(case).model_dump(mode="json")
    data[field] = value
    with pytest.raises(ValidationError):
        SynchronousAcknowledgementEvidence.model_validate_json(json.dumps(data))


@pytest.mark.parametrize(
    "field",
    [
        "case_id",
        "identity_basis",
        "review_basis",
        "endpoint",
        "operation",
        "reviewed_source_family",
        "predicates",
        "audit_sequence_digest",
        "user",
        "context",
        "execution_start",
        "execution_end_exclusive",
        "issued_at",
        "disposition",
    ],
)
def test_acknowledgement_provenance_is_required(case: LegacyCase, field: str) -> None:
    data = synchronous(case).model_dump(mode="json")
    del data[field]
    with pytest.raises(ValidationError):
        SynchronousAcknowledgementEvidence.model_validate_json(json.dumps(data))


@pytest.mark.parametrize(
    "field,value",
    [
        ("http_status", 202),
        ("http_status", 200.0),
        ("bounded_valid_json", False),
        ("bounded_valid_json", 1),
        ("returned_feature_count", 2),
        ("returned_feature_count", True),
        ("approved_feature_id_matches", False),
        ("pre_dispatch_terminal_fillet_validated", False),
        ("result_suppressed", True),
        ("result_suppressed", 0),
        ("microversion_skew", True),
        ("result_microversion_valid", False),
        ("result_microversion_differs_from_baseline", False),
        ("consumed_single_operation_no_supported_replay", False),
        ("settled", True),
    ],
)
def test_every_historical_response_predicate_is_fixed(
    case: LegacyCase, field: str, value: Any
) -> None:
    data = synchronous(case).predicates.model_dump(mode="json")
    data[field] = value
    with pytest.raises(ValidationError):
        SynchronousAckPredicates.model_validate_json(json.dumps(data))


@pytest.mark.parametrize("field", list(SynchronousAckPredicates.model_fields))
def test_no_acknowledgement_predicate_can_be_omitted(
    case: LegacyCase, field: str
) -> None:
    data = synchronous(case).predicates.model_dump(mode="json")
    del data[field]
    with pytest.raises(ValidationError):
        SynchronousAckPredicates.model_validate_json(json.dumps(data))


@pytest.mark.parametrize(
    "change",
    [
        "digest",
        "ack_time",
        "audit_id",
        "audit_time",
        "audit_user",
        "missing",
        "duplicate",
        "conflict",
    ],
)
def test_synchronous_review_must_match_exact_audit_rows(
    case: LegacyCase, change: str
) -> None:
    use_synchronous(case)
    if change in ("digest", "ack_time"):
        data = case.review.model_dump(mode="json")
        data["settlement"]["evidence"][
            "audit_sequence_digest" if change == "digest" else "issued_at"
        ] = "0" * 64 if change == "digest" else CASE.execution_start
        case.review = LegacyReview.model_validate_json(json.dumps(data))
    else:
        with case.harness.runtime.sessions.begin() as db:
            ack = db.scalar(
                select(AuditEvent).where(
                    AuditEvent.kind == "write_provider_acknowledged"
                )
            )
            assert ack
            if change == "audit_id":
                ack.id = "synthetic-replacement-audit-id"
            elif change == "audit_time":
                ack.created_at -= 1
            elif change == "audit_user":
                ack.user_id = None
            elif change == "missing":
                db.delete(ack)
            else:
                db.add(
                    AuditEvent(
                        user_id=case.enrollment.binding.user,
                        kind="write_provider_acknowledged"
                        if change == "duplicate"
                        else "write_verified",
                        outcome="ok",
                        created_at=CASE.execution_start + 2,
                    )
                )
    before = case.snapshot()
    with pytest.raises(LegacyRecoveryDenied):
        case.recover()
    assert case.snapshot() == before and not case.provider.calls


def test_audit_pins_are_rechecked_after_capture(
    case: LegacyCase, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_synchronous(case)
    release = legacy_release.release_legacy_record
    before = case.snapshot()

    def changed(db: Any, *args: Any) -> Any:
        ack = db.scalar(
            select(AuditEvent).where(AuditEvent.kind == "write_provider_acknowledged")
        )
        ack.id = "synthetic-replacement-audit-id"
        db.flush()
        return release(db, *args)

    monkeypatch.setattr(legacy_recovery, "release_legacy_record", changed)
    with pytest.raises(LegacyRecoveryDenied):
        case.recover()
    assert case.snapshot() == before and case.provider.writes == 0


@pytest.mark.parametrize(
    "field", ["documentId", "workspaceId", "elementId", "revisionKind"]
)
def test_acknowledgement_context_is_not_caller_selected(
    case: LegacyCase, field: str
) -> None:
    data = synchronous(case).model_dump(mode="json")
    data["context"][field] = "version" if field == "revisionKind" else "a" * 24
    with pytest.raises(ValidationError):
        SynchronousAcknowledgementEvidence.model_validate_json(json.dumps(data))


@pytest.mark.parametrize("changed_audit", [False, True])
def test_synchronous_category_on_isolated_postgres(
    postgres: Engine,
    harness: Harness,
    monkeypatch: pytest.MonkeyPatch,
    changed_audit: bool,
) -> None:
    from legacy_support import seed_legacy

    use_postgres(harness, postgres)
    c = seed_legacy(harness, PlanProvider(), monkeypatch)
    use_synchronous(c)
    if changed_audit:
        with harness.runtime.sessions.begin() as db:
            ack = db.scalar(
                select(AuditEvent).where(
                    AuditEvent.kind == "write_provider_acknowledged"
                )
            )
            assert ack
            ack.created_at -= 1  # Still ordered/in-window, but differs from review.
        before = c.snapshot()
        with pytest.raises(LegacyRecoveryDenied):
            c.recover()
        assert c.snapshot() == before and not c.provider.calls
    else:
        result = c.recover()
        assert result.disposition == "legacy_administrative_retirement"
        assert len(c.provider.calls) == 5 and c.provider.writes == 0
