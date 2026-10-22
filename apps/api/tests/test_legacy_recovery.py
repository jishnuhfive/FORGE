"""Single-case legacy retirement, entirely synthetic and never auto-enrolled."""

import json
from collections.abc import Iterator
from typing import Any

import pytest
from conftest import Harness
from legacy_support import NOW, LegacyCase, saved, seed_legacy
from pydantic import ValidationError
from sqlalchemy import select
from test_modify_plan import PlanProvider

from forge_api.cad_edits import (
    legacy_enrollment,
    legacy_policy,
    legacy_recovery,
    legacy_release,
    plan_storage,
    storage,
)
from forge_api.cad_edits.domain import EditError, fingerprint
from forge_api.cad_edits.legacy_contracts import (
    LegacyCasePolicy,
    LegacyEnrollment,
    LegacyRecoveryDenied,
    LegacyResult,
    LegacyReview,
)
from forge_api.cad_edits.legacy_policy import CASE
from forge_api.cad_edits.plans import StoredPlan
from forge_api.db.models import (
    AuditEvent,
    OnshapeAuthorization,
    Session,
    User,
    WriteFence,
    WriteRecord,
)


@pytest.fixture
def case(harness: Harness, monkeypatch: pytest.MonkeyPatch) -> Iterator[LegacyCase]:
    yield seed_legacy(harness, PlanProvider(), monkeypatch)


def test_exact_case_closes_once_redacts_and_remains_consumed(
    case: LegacyCase, monkeypatch: pytest.MonkeyPatch
) -> None:
    auth_calls = len(case.harness.provider.calls)
    original = saved(case).plan
    result = case.recover()
    assert result == LegacyResult(recovered_at=NOW)
    with case.harness.runtime.sessions() as db:
        row = db.get(WriteRecord, case.enrollment.record_id)
        assert row and row.state == "operator_recovered"
        assert row.purge_at == NOW + 900
        assert row.digest == case.enrollment.plan_digest
        assert row.session_hash == original.binding.session
        assert row.payload == result.model_dump_json()
        assert db.scalar(select(WriteFence)) is None
        audits = list(
            db.scalars(
                select(AuditEvent).where(
                    AuditEvent.kind == "write_legacy_retained_retirement"
                )
            )
        )
        assert len(audits) == 1 and audits[0].outcome == "local_only"
        assert audits[0].user_id == original.binding.user
        for load in (plan_storage.load, plan_storage.result):
            with pytest.raises(EditError, match="proposal_used"):
                load(row)
        assert row.payload is not None
        payload = json.loads(row.payload)
        assert set(payload) == {
            "schema_version",
            "state",
            "original_execution_outcome",
            "identity_basis",
            "disposition",
            "recovered_at",
        }
        assert "plan" not in payload and "binding" not in payload
        assert payload["identity_basis"] == "trusted_retained_database"
        assert payload["disposition"] == "legacy_administrative_retirement"
        assert payload["original_execution_outcome"] == "execution_uncertain"
    assert len(case.provider.calls) == 5 and case.provider.writes == 0
    assert len(case.harness.provider.calls) == auth_calls
    closed = case.snapshot()
    with pytest.raises(LegacyRecoveryDenied):
        case.recover()
    assert case.snapshot() == closed and len(case.provider.calls) == 5
    # Ordinary cleanup does not erase the future tombstone.
    monkeypatch.setattr(storage, "now", lambda: NOW)
    with case.harness.runtime.sessions.begin() as db:
        storage.cleanup(db)
        assert db.get(WriteRecord, case.enrollment.record_id) is not None


@pytest.mark.parametrize(
    "change",
    [
        "unenrolled",
        "test_environment",
        "production",
        "writes",
        "before_boundary",
        "sunset",
        "record_missing",
        "record_id",
        "state",
        "digest",
        "payload",
        "payload_large",
        "binding",
        "record_owner",
        "record_session",
        "creation",
        "expiry",
        "fence_missing",
        "fence_record",
        "fence_workspace",
        "fence_owner",
        "session_missing",
        "session_active",
        "session_idle_only",
        "session_owner",
        "session_newer",
        "grant_missing",
        "grant_disconnected",
        "grant_stack",
        "grant_company",
        "grant_generation",
        "grant_scope",
        "grant_cooldown",
        "other_pending",
        "other_uncertain",
        "other_unknown",
        "cache_miss",
        "snapshot_pin",
    ],
)
def test_pre_capture_denials_preserve_exact_fenced_state(
    case: LegacyCase, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    h, e = case.harness, case.enrollment
    with h.runtime.sessions.begin() as db:
        row = db.get(WriteRecord, e.record_id)
        session = db.get(Session, e.binding.session)
        grant = db.get(OnshapeAuthorization, e.binding.user)
        fence = db.get(WriteFence, e.fence_workspace_key)
        assert row and session and grant and fence
        if change == "unenrolled":
            monkeypatch.setattr(legacy_policy, "_ENROLLMENT", None)
        elif change in ("test_environment", "production"):
            h.runtime.settings.environment = (
                "test" if change == "test_environment" else "production"
            )
        elif change == "writes":
            h.runtime.settings.forge_cad_writes_enabled = True
        elif change in ("before_boundary", "sunset"):
            monkeypatch.setattr(
                legacy_policy,
                "now",
                lambda: (
                    CASE.adoption_boundary - 1
                    if change == "before_boundary"
                    else CASE.sunset
                ),
            )
        elif change == "record_missing":
            db.delete(row)
        elif change == "record_id":
            row.id = "C" * 43
        elif change == "state":
            row.state = "verifying"
        elif change == "digest":
            row.digest = "0" * 64
        elif change == "payload":
            row.payload = "{}"
        elif change == "payload_large":
            row.payload = " " * 65537
        elif change == "binding":
            s = plan_storage.load(row)
            p = s.plan.model_copy(
                update={
                    "binding": s.plan.binding.model_copy(
                        update={"generation": "synthetic-different-old-generation"}
                    )
                }
            )
            row.digest = fingerprint(p.model_dump(mode="json"))
            row.payload = s.model_copy(update={"plan": p}).model_dump_json()
        elif change == "record_owner" or change in ("fence_owner", "session_owner"):
            user = User(
                onshape_user_id="synthetic-other", stack=e.stack, display_name="Other"
            )
            db.add(user)
            db.flush()
            if change == "record_owner":
                row.user_id = user.id
            elif change == "fence_owner":
                fence.user_id = user.id
            else:
                session.user_id = user.id
        elif change == "record_session":
            row.session_hash = "0" * 64
        elif change == "creation":
            row.created_at = CASE.adoption_boundary
        elif change == "expiry":
            row.expires_at += 1
        elif change == "fence_missing":
            db.delete(fence)
        elif change == "fence_record":
            fence.record_id = "C" * 43
        elif change == "fence_workspace":
            fence.workspace_key = "0" * 64
        elif change == "session_missing":
            db.delete(session)
        elif change in ("session_active", "session_idle_only"):
            session.expires_at = NOW + 100
        elif change == "session_newer":
            session.created_at = CASE.proposal_created_at + 1
        elif change == "grant_missing":
            db.delete(grant)
        elif change == "grant_disconnected":
            grant.status = "disconnected"
        elif change == "grant_stack":
            grant.stack = "https://other.onshape.com/api"
        elif change == "grant_company":
            grant.company_id = "a" * 24
        elif change == "grant_generation":
            grant.generation = "synthetic-rotated"
        elif change == "grant_scope":
            grant.granted_scope = "OAuth2Write"
        elif change == "grant_cooldown":
            grant.retry_after = NOW + 100
        elif change.startswith("other_"):
            db.add(
                WriteRecord(
                    id="C" * 43,
                    user_id=e.binding.user,
                    session_hash=e.binding.session,
                    state={
                        "other_pending": "pending",
                        "other_uncertain": "execution_uncertain",
                        "other_unknown": "future_state",
                    }[change],
                    digest="0" * 64,
                    payload=None,
                    created_at=NOW,
                    expires_at=NOW + 120,
                    purge_at=NOW + 900,
                )
            )
        elif change == "cache_miss":
            h.runtime.tokens.forget(e.binding.user)
        else:
            monkeypatch.setattr(
                legacy_policy,
                "_ENROLLMENT",
                e.model_copy(update={"payload_fingerprint": "0" * 64}),
            )
    before = case.snapshot()
    with pytest.raises(LegacyRecoveryDenied):
        case.recover()
    assert case.snapshot() == before and not case.provider.calls


@pytest.mark.parametrize(
    "change",
    [
        "missing",
        "duplicate",
        "wrong_order",
        "wrong_user",
        "outside_start",
        "outside_end",
        "outcome",
        "overlap",
        "verified",
        "v1_retirement",
        "legacy_retirement",
        "unknown",
    ],
)
def test_audit_ambiguity_denies_without_capture(case: LegacyCase, change: str) -> None:
    with case.harness.runtime.sessions.begin() as db:
        events = list(
            db.scalars(
                select(AuditEvent).where(
                    AuditEvent.kind == "write_provider_acknowledged"
                )
            )
        )
        assert len(events) == 1
        event = events[0]
        if change == "missing":
            db.delete(event)
        elif change == "wrong_order" or change == "outside_start":
            event.created_at = CASE.execution_start - 1
        elif change == "outside_end":
            event.created_at = CASE.execution_end_exclusive
        elif change == "wrong_user":
            event.user_id = None
        elif change == "outcome":
            event.outcome = "denied"
        else:
            kind = {
                "duplicate": "write_provider_acknowledged",
                "overlap": "write_dispatch_started",
                "verified": "write_verified",
                "v1_retirement": "write_retained_operator_recovery",
                "legacy_retirement": "write_legacy_retained_retirement",
                "unknown": "write_future_execution",
            }[change]
            db.add(
                AuditEvent(
                    user_id=case.enrollment.binding.user,
                    kind=kind,
                    outcome="ok",
                    created_at=CASE.execution_start + 2,
                )
            )
    before = case.snapshot()
    with pytest.raises(LegacyRecoveryDenied):
        case.recover()
    assert case.snapshot() == before and not case.provider.calls


@pytest.mark.parametrize(
    "change",
    [
        "suppress",
        "rename",
        "batch",
        "different_fillet",
        "nonterminal",
        "original_false",
        "preview",
        "claimed",
        "verified",
    ],
)
def test_scope_and_journal_are_checked_independently_of_pins(
    case: LegacyCase, change: str
) -> None:
    value = saved(case).model_dump(mode="json")
    op = value["plan"]["operations"][0]
    if change == "suppress":
        op["operation"]["type"] = op["preview"]["type"] = "SET_SUPPRESSED"
        op["preview"]["current"], op["preview"]["proposed"] = "Active", "Suppressed"
        value["plan"]["baseline"]["suppressed"] = False
    elif change == "rename":
        op["operation"] = {
            "type": "RENAME_FEATURE",
            "target": op["target"]["handle"],
            "new_name": "Other",
        }
        op["preview"]["type"] = "RENAME_FEATURE"
    elif change == "batch":
        value["plan"]["operations"].append(op.copy())
        value["result"]["operations"].append("execution_uncertain")
    elif change == "different_fillet":
        op["target"]["feature_id"] = "synthetic-other-fillet"
    elif change == "nonterminal":
        op["target"]["position"] -= 1
    elif change == "original_false":
        value["plan"]["baseline"]["suppressed"] = False
    elif change == "preview":
        op["preview"]["field"] = "Name"
    elif change == "claimed":
        value["result"] = {"state": "claimed", "operations": ["executing"]}
    else:
        value["result"]["operations"] = ["verified_success"]
    checked = StoredPlan.model_validate_json(json.dumps(value))
    with pytest.raises(LegacyRecoveryDenied):
        legacy_enrollment._plan(checked, case.enrollment)


@pytest.mark.parametrize(
    "field,value",
    [
        ("adoption_boundary", 0),
        ("proposal_created_at", 1792540800),
        ("execution_start", 0),
        ("execution_end_exclusive", 9999999999),
        ("sunset", 9999999999),
        ("operation", "SET_SUPPRESSED"),
        ("environment", "production"),
        ("allow_legacy", True),
        ("terminal_fillet", False),
    ],
)
def test_policy_cannot_accept_caller_selected_alternatives(
    field: str, value: Any
) -> None:
    data = CASE.model_dump(mode="json")
    data[field] = value
    with pytest.raises(ValidationError):
        LegacyCasePolicy.model_validate_json(json.dumps(data))


@pytest.mark.parametrize(
    "field", ["documentId", "workspaceId", "elementId", "revisionKind"]
)
def test_policy_context_is_closed(field: str) -> None:
    data = CASE.model_dump(mode="json")
    data["context"][field] = "version" if field == "revisionKind" else "a" * 24
    with pytest.raises(ValidationError):
        LegacyCasePolicy.model_validate_json(json.dumps(data))


@pytest.mark.parametrize(
    "field,value",
    [
        ("identity_basis", "independent_receipt"),
        ("created_at", 1792540800),
        ("created_at", 1792513444),
        ("expires_at", 1792513564),
        ("reviewed_at", 1792713600),
        ("history_source", "current_database"),
        ("extra", True),
    ],
)
def test_enrollment_is_closed(case: LegacyCase, field: str, value: Any) -> None:
    data = case.enrollment.model_dump(mode="json")
    data[field] = value
    with pytest.raises(ValidationError):
        LegacyEnrollment.model_validate_json(json.dumps(data))


@pytest.mark.parametrize(
    "section,field,value",
    [
        ("settlement", "evidence", True),
        ("settlement", "settled", True),
        ("settlement", "reviewer", ""),
        ("settlement", "review_id", ""),
        ("settlement", "disposition", "verified_success"),
        ("evidence", "category", "elapsed_time"),
        ("evidence", "category", "stable_head"),
        ("evidence", "category", "provider_acknowledgement"),
        ("evidence", "evidence_reference", ""),
        ("evidence", "evidence_digest", ""),
        ("evidence", "issuer", ""),
        ("evidence", "execution_start", 0),
        ("evidence", "execution_end_exclusive", 9999999999),
        ("evidence", "disposition", "current_suppression_matches"),
        ("quiescence", "effective_writes_off", False),
        ("quiescence", "workers_drained", False),
        ("quiescence", "no_queued_same_user_write", False),
        ("quiescence", "no_resumable_historical_approval", False),
        ("quiescence", "original_session_hard_inactive", False),
        ("quiescence", "no_competing_recovery", False),
        ("quiescence", "deployment_inventory_digest", ""),
        ("quiescence", "worker_drain_evidence_digest", ""),
        ("quiescence", "queue_inspection_digest", ""),
        ("quiescence", "approval_inspection_digest", ""),
        ("quiescence", "recovery_exclusion_digest", ""),
        ("quiescence", "write_admission_evidence_digest", ""),
    ],
)
def test_incomplete_or_unsupported_proofs_are_not_accepted(
    case: LegacyCase, section: str, field: str, value: Any
) -> None:
    data = case.review.model_dump(mode="json")
    target = data["settlement"]["evidence"] if section == "evidence" else data[section]
    target[field] = value
    with pytest.raises(ValidationError):
        LegacyReview.model_validate_json(json.dumps(data))


@pytest.mark.parametrize(
    "change",
    [
        "settlement_pin",
        "quiescence_pin",
        "user",
        "future_evidence",
        "expired",
        "long_validity",
        "future_review",
    ],
)
def test_semantically_mismatched_proofs_deny_without_capture(
    case: LegacyCase, change: str
) -> None:
    data = case.review.model_dump(mode="json")
    if change.endswith("_pin"):
        data[change.split("_")[0]]["enrollment_fingerprint"] = "0" * 64
    elif change == "user":
        data["settlement"]["evidence"]["user"] = "synthetic-other"
    elif change == "future_evidence":
        data["settlement"]["evidence"]["issued_at"] = NOW + 1
    elif change == "expired":
        data["quiescence"]["valid_until"] = NOW
    elif change == "long_validity":
        data["settlement"]["valid_until"] = NOW + 1000
    else:
        data["quiescence"]["reviewed_at"] = NOW + 1
    case.review = LegacyReview.model_validate_json(json.dumps(data))
    before = case.snapshot()
    with pytest.raises(LegacyRecoveryDenied):
        case.recover()
    assert case.snapshot() == before and not case.provider.calls


@pytest.mark.parametrize(
    "change",
    [
        "sunset",
        "proof_expiry",
        "generation",
        "payload",
        "conflict",
        "audit",
        "writes",
        "unenroll",
    ],
)
def test_revalidates_everything_after_capture(
    case: LegacyCase, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    release = legacy_release.release_legacy_record
    before = case.snapshot()

    def changed(db: Any, settings: Any, run: Any, evidence: Any) -> Any:
        if change == "sunset":
            monkeypatch.setattr(legacy_policy, "now", lambda: CASE.sunset)
        elif change == "proof_expiry":
            monkeypatch.setattr(legacy_policy, "now", lambda: NOW + 300)
        elif change == "generation":
            db.get(
                OnshapeAuthorization, run.enrollment.binding.user
            ).generation = "synthetic-rotated"
        elif change == "payload":
            db.get(WriteRecord, run.enrollment.record_id).payload += " "
        elif change == "audit":
            db.add(
                AuditEvent(
                    user_id=run.enrollment.binding.user,
                    kind="write_verified",
                    outcome="ok",
                    created_at=NOW,
                )
            )
        elif change == "writes":
            settings.forge_cad_writes_enabled = True
        elif change == "unenroll":
            monkeypatch.setattr(legacy_policy, "_ENROLLMENT", None)
        else:
            db.add(
                WriteRecord(
                    id="C" * 43,
                    user_id=run.enrollment.binding.user,
                    session_hash=run.enrollment.binding.session,
                    state="pending",
                    digest="0" * 64,
                    payload=None,
                    created_at=NOW,
                    expires_at=NOW + 120,
                    purge_at=NOW + 900,
                )
            )
        db.flush()
        return release(db, settings, run, evidence)

    monkeypatch.setattr(legacy_recovery, "release_legacy_record", changed)
    with pytest.raises(LegacyRecoveryDenied):
        case.recover()
    assert case.snapshot() == before and case.provider.writes == 0


@pytest.mark.parametrize(
    "section,field",
    [
        ("settlement", "reviewer"),
        ("settlement", "review_id"),
        ("settlement", "enrollment_fingerprint"),
        ("settlement", "evidence"),
        ("settlement", "disposition"),
        ("evidence", "issuer"),
        ("evidence", "evidence_digest"),
        ("evidence", "evidence_reference"),
        ("evidence", "context"),
        ("evidence", "user"),
        ("evidence", "execution_start"),
        ("quiescence", "deployment_inventory_digest"),
        ("quiescence", "write_admission_evidence_digest"),
        ("quiescence", "worker_drain_evidence_digest"),
        ("quiescence", "queue_inspection_digest"),
        ("quiescence", "approval_inspection_digest"),
        ("quiescence", "recovery_exclusion_digest"),
        ("quiescence", "effective_writes_off"),
        ("quiescence", "workers_drained"),
        ("quiescence", "no_queued_same_user_write"),
        ("quiescence", "no_resumable_historical_approval"),
        ("quiescence", "original_session_hard_inactive"),
        ("quiescence", "no_competing_recovery"),
    ],
)
def test_proof_provenance_cannot_be_omitted(
    case: LegacyCase, section: str, field: str
) -> None:
    data = case.review.model_dump(mode="json")
    target = data["settlement"]["evidence"] if section == "evidence" else data[section]
    del target[field]
    with pytest.raises(ValidationError):
        LegacyReview.model_validate_json(json.dumps(data))


@pytest.mark.parametrize("value", [1, "true", 1.0])
def test_quiescence_requires_actual_booleans(case: LegacyCase, value: Any) -> None:
    data = case.review.model_dump(mode="json")
    data["quiescence"]["effective_writes_off"] = value
    with pytest.raises(ValidationError):
        LegacyReview.model_validate_json(json.dumps(data))


@pytest.mark.parametrize(
    "field", ["documentId", "workspaceId", "elementId", "revisionKind"]
)
def test_settlement_cannot_substitute_context(case: LegacyCase, field: str) -> None:
    data = case.review.model_dump(mode="json")
    data["settlement"]["evidence"]["context"][field] = (
        "version" if field == "revisionKind" else "a" * 24
    )
    with pytest.raises(ValidationError):
        LegacyReview.model_validate_json(json.dumps(data))


def test_sunset_at_precommit_check_rolls_back_closure(
    case: LegacyCase, monkeypatch: pytest.MonkeyPatch
) -> None:
    release = legacy_release.release_legacy_record
    before = case.snapshot()

    def expired(*args: Any) -> Any:
        result = release(*args)
        monkeypatch.setattr(legacy_policy, "now", lambda: CASE.sunset)
        return result

    monkeypatch.setattr(legacy_recovery, "release_legacy_record", expired)
    with pytest.raises(LegacyRecoveryDenied):
        case.recover()
    assert case.snapshot() == before
