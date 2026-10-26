"""Operator closure of a partial creation incident: exact, read-only, fail closed."""

import json
from collections.abc import Iterator
from copy import deepcopy
from typing import Any, cast

import httpx2 as httpx
import pytest
from conftest import Harness
from pydantic import SecretStr
from sqlalchemy import select
from test_cad_read import REF
from test_creation_api import BRIEF, Provider, post
from test_safe_edit import M0, running

from forge_api.auth.provider import TokenResponse
from forge_api.cad_create import settlement
from forge_api.cad_create.settlement import (
    CONFIRMATION,
    SettlementDenied,
    SettlementReview,
    inspect_incident,
    settle_incident,
)
from forge_api.db.models import (
    AuditEvent,
    OnshapeAuthorization,
    WriteFence,
    WriteRecord,
)
from forge_api.db.models import now as models_now


class Incident:
    def __init__(self, harness: Harness, provider: Provider) -> None:
        self.harness = harness
        self.provider = provider
        self.transport = httpx.MockTransport(provider.handle)

    def review(self, **changes: Any) -> SettlementReview:
        values: dict[str, Any] = {
            "operator_authorized": True,
            "disposable_fixture": True,
            "writers_drained": True,
            "upstream_settled": True,
            "acknowledgement": CONFIRMATION,
            "settlement_review": "reviewed in the Onshape feature tree",
            "stack": str(self.harness.runtime.settings.onshape_api_base_url),
            "company_id": self.harness.runtime.settings.onshape_company_id,
        }
        return SettlementReview(**{**values, **changes})

    def inspect(self, **changes: Any) -> settlement.Observation:
        return inspect_incident(
            self.harness.runtime, self.review(**changes), transport=self.transport
        )

    def settle(self, **changes: Any) -> settlement.Settlement:
        return settle_incident(
            self.harness.runtime, self.review(**changes), transport=self.transport
        )

    def denied(self, action: str, code: str, **changes: Any) -> None:
        with pytest.raises(SettlementDenied) as error:
            getattr(self, action)(**changes)
        assert error.value.args == (code,)
        self.assert_untouched()

    def assert_untouched(self) -> None:
        with self.harness.runtime.sessions() as db:
            assert len(list(db.scalars(select(WriteFence)))) >= 1
            states = [r.state for r in db.scalars(select(WriteRecord))]
            assert "execution_uncertain" in states

    @property
    def posts(self) -> int:
        return sum(1 for r in self.provider.calls if r.method == "POST")


@pytest.fixture
def incident(harness: Harness, monkeypatch: pytest.MonkeyPatch) -> Iterator[Incident]:
    provider = Provider("ack")  # first POST applied, acknowledgement rejected
    with running(harness, cast(Any, provider)):
        preview = post(
            harness, "/api/create/plan", {"context": REF.model_dump(), "brief": BRIEF}
        ).json()
        response = post(
            harness,
            f"/api/create/plans/{preview['proposal_id']}/approve",
            {"digest": preview["digest"], "brief_confirmed": True},
        )
        assert response.json()["steps"] == ["execution_uncertain", "skipped"]
    assert provider.writes == 1
    runtime = harness.runtime
    runtime.settings.environment = "development"
    runtime.settings.forge_cad_writes_enabled = False
    with runtime.sessions() as db:
        grant = db.scalar(select(OnshapeAuthorization))
        assert grant is not None
        runtime.tokens.remember(
            grant.user_id,
            grant.generation,
            TokenResponse(
                access_token=SecretStr("synthetic-cached-read"),
                token_type="Bearer",
                expires_in=3600,
            ),
        )
    monkeypatch.setattr(settlement, "now", lambda: models_now() + 2000)
    yield Incident(harness, provider)


def rows(harness: Harness) -> tuple[WriteRecord, list[WriteFence], list[AuditEvent]]:
    with harness.runtime.sessions() as db:
        record = db.scalar(
            select(WriteRecord).where(
                WriteRecord.payload.like("%creation-approval-v1%")
            )
        )
        assert record is not None
        db.expunge(record)
        fences = list(db.scalars(select(WriteFence)))
        events = list(
            db.scalars(
                select(AuditEvent).where(AuditEvent.kind == "write_creation_settlement")
            )
        )
        return record, fences, events


def test_inspection_reports_sanitized_partial_state_and_changes_nothing(
    incident: Incident,
) -> None:
    posts = incident.posts
    seen = incident.inspect()
    assert (seen.feature_count, seen.body_count) == (1, 0)
    assert seen.stable and seen.sketch_named_and_healthy and seen.revision_advanced
    assert seen.ack_check is None and seen.denial is None
    text = repr(seen)
    assert REF.documentId not in text and "synthetic-cached-read" not in text
    assert incident.posts == posts == 1
    record, fences, events = rows(incident.harness)
    assert record.state == "execution_uncertain" and len(fences) == 1 and not events


def test_inspection_names_the_acknowledgement_check_and_field_names_only(
    incident: Incident,
) -> None:
    incident.provider.data["features"][0]["bogusProviderKey"] = "secret-value"
    seen = incident.inspect()
    assert seen.ack_check == "ack_feature_keys"
    assert seen.ack_fields == ("bogusProviderKey",)
    assert "secret-value" not in repr(seen)


def test_exact_authorized_settlement_preserves_uncertainty_and_never_writes(
    incident: Incident,
) -> None:
    before, _, _ = rows(incident.harness)
    result = incident.settle()
    assert result.original_outcome == "execution_uncertain"
    assert result.disposition == "independently_settled_partial_sketch"
    record, fences, events = rows(incident.harness)
    assert record.state == "operator_recovered" and not fences
    assert record.payload == before.payload  # historical steps are untouched
    assert json.loads(record.payload or "")["steps"] == [
        "execution_uncertain",
        "skipped",
    ]
    assert [(e.outcome, e.created_at) for e in events] == [
        ("local_only", result.recovered_at)
    ]
    assert incident.posts == 1  # only the original dispatch; settlement is GET-only
    assert incident.provider.writes == 1


def test_second_settlement_is_denied_after_the_fence_is_gone(
    incident: Incident,
) -> None:
    incident.settle()
    with pytest.raises(SettlementDenied) as error:
        incident.settle()
    assert error.value.args == ("unique_incident_required",)
    assert len(rows(incident.harness)[2]) == 1


@pytest.mark.parametrize(
    ("changes", "code"),
    [
        ({"acknowledgement": CONFIRMATION + " "}, "exact_acknowledgement_required"),
        ({"acknowledgement": ""}, "exact_acknowledgement_required"),
        ({"operator_authorized": False}, "operator_review_required"),
        ({"disposable_fixture": False}, "operator_review_required"),
        ({"writers_drained": False}, "operator_review_required"),
        ({"upstream_settled": False}, "operator_review_required"),
        ({"stack": "https://other.example"}, "reviewed_configuration_mismatch"),
        ({"company_id": "c" * 24}, "reviewed_configuration_mismatch"),
    ],
)
def test_review_and_exact_acknowledgement_are_required(
    incident: Incident, changes: dict[str, Any], code: str
) -> None:
    incident.denied("settle", code, **changes)


def test_writes_on_or_non_development_denies(incident: Incident) -> None:
    incident.harness.runtime.settings.forge_cad_writes_enabled = True
    incident.denied("settle", "development_writes_off_required")
    incident.harness.runtime.settings.forge_cad_writes_enabled = False
    incident.harness.runtime.settings.environment = "production"
    incident.denied("settle", "development_writes_off_required")


def test_missing_cached_credential_denies(incident: Incident) -> None:
    incident.harness.runtime.tokens.forget(rows(incident.harness)[0].user_id)
    incident.denied("settle", "cached_read_credential_required")


def test_unaged_record_is_denied(
    incident: Incident, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settlement, "now", models_now)
    incident.denied("settle", "exact_partial_creation_record_required")


def test_wrong_workspace_is_denied(incident: Incident) -> None:
    with incident.harness.runtime.sessions.begin() as db:
        grant = db.scalar(select(OnshapeAuthorization))
        assert grant is not None
        grant.stack = "https://other-stack.example"
    incident.denied("settle", "workspace_reference_mismatch")


def test_mismatched_fence_is_denied(incident: Incident) -> None:
    with incident.harness.runtime.sessions.begin() as db:
        fence = db.scalar(select(WriteFence))
        assert fence is not None
        fence.workspace_key = "e" * 64
    incident.denied("settle", "exact_partial_creation_record_required")


def test_missing_fence_is_denied(incident: Incident) -> None:
    with incident.harness.runtime.sessions.begin() as db:
        for fence in db.scalars(select(WriteFence)):
            db.delete(fence)
    with pytest.raises(SettlementDenied) as error:
        incident.settle()
    assert error.value.args == ("unique_incident_required",)


def test_a_second_open_operation_for_the_user_is_denied(incident: Incident) -> None:
    record, _, _ = rows(incident.harness)
    with incident.harness.runtime.sessions.begin() as db:
        db.add(
            WriteRecord(
                id="x" * 43,
                user_id=record.user_id,
                session_hash="a" * 64,
                state="claimed",
                digest="b" * 64,
                payload=None,
                created_at=1,
                expires_at=2,
                purge_at=3,
            )
        )
    incident.denied("settle", "conflicting_user_operation")


def test_extra_audit_history_is_denied(incident: Incident) -> None:
    record, _, _ = rows(incident.harness)
    with incident.harness.runtime.sessions.begin() as db:
        db.add(
            AuditEvent(
                kind="write_provider_acknowledged",
                outcome="ok",
                user_id=record.user_id,
                created_at=record.created_at + 1,
            )
        )
    incident.denied("settle", "unique_partial_audit_required")


def test_unexpected_feature_set_is_denied(incident: Incident) -> None:
    data = incident.provider.data
    data["features"] = [*data["features"], deepcopy(data["features"][0])]
    data["features"][1]["featureId"] = "second"
    data["rollbackIndex"] = 2
    incident.denied("settle", "unexpected_feature_set")


def test_extra_inspection_flags_unexpected_feature_without_denying_read_only(
    incident: Incident,
) -> None:
    data = incident.provider.data
    data["features"] = []
    data["rollbackIndex"] = 0
    seen = incident.inspect()
    assert seen.feature_count == 0 and seen.denial == "unexpected_feature_set"


def test_renamed_or_suppressed_sketch_is_denied(incident: Incident) -> None:
    incident.provider.data["features"][0]["name"] = "Someone else"
    incident.denied("settle", "unexpected_feature")


def test_an_existing_body_is_denied(
    incident: Incident, monkeypatch: pytest.MonkeyPatch
) -> None:
    incident.provider.writes = 2  # the test double then reports a solid body
    incident.denied("settle", "unexpected_body")


def test_unchanged_revision_is_denied(incident: Incident) -> None:
    incident.provider.marker = M0
    incident.provider.data["sourceMicroversion"] = M0
    incident.denied("settle", "revision_not_advanced")


def test_unstable_evidence_is_denied(incident: Incident) -> None:
    original = incident.provider.handle
    count = {"n": 0}

    def drifting(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/features"):
            count["n"] += 1
            incident.provider.data["drift"] = count["n"]
        return original(request)

    incident.transport = httpx.MockTransport(drifting)
    incident.denied("settle", "inventory_differs")


def test_unhealthy_feature_state_is_denied(incident: Incident) -> None:
    feature_id = incident.provider.data["features"][0]["featureId"]
    incident.provider.data["featureStates"] = {
        feature_id: {"featureStatus": "ERROR", "inactive": False}
    }
    incident.denied("settle", "evidence_unsupported")


def test_provider_read_failure_is_denied_without_detail(incident: Incident) -> None:
    def broken(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("synthetic secret detail")

    incident.transport = httpx.MockTransport(broken)
    incident.denied("settle", "evidence_unavailable")


def test_transaction_failure_retains_fence_and_uncertainty(
    incident: Incident, monkeypatch: pytest.MonkeyPatch
) -> None:
    def explode(**_: Any) -> Any:
        raise RuntimeError("synthetic commit-time failure")

    monkeypatch.setattr(settlement, "AuditEvent", explode)
    incident.denied("settle", "completion_unconfirmed_no_retry")
    record, fences, events = rows(incident.harness)
    assert record.state == "execution_uncertain" and len(fences) == 1 and not events


def test_the_read_transport_refuses_every_non_get_request() -> None:
    sent: list[str] = []

    def inner(request: httpx.Request) -> httpx.Response:
        sent.append(request.method)
        return httpx.Response(200, json={})

    guarded = settlement._GetOnly(httpx.MockTransport(inner))
    with httpx.Client(transport=guarded) as client:
        assert client.get("https://cad.example/x").status_code == 200
        for method in ("POST", "PUT", "DELETE", "PATCH"):
            with pytest.raises(SettlementDenied):
                client.request(method, "https://cad.example/x")
    assert sent == ["GET"]


def test_expired_placeholders_do_not_block_but_a_live_preview_does(
    incident: Incident,
) -> None:
    record, _, _ = rows(incident.harness)

    def add(state: str, expires: int, ident: str) -> None:
        with incident.harness.runtime.sessions.begin() as db:
            db.add(
                WriteRecord(
                    id=ident * 43,
                    user_id=record.user_id,
                    session_hash="a" * 64,
                    state=state,
                    digest="b" * 64,
                    payload=None,
                    created_at=1,
                    expires_at=expires,
                    purge_at=expires + 60,
                )
            )

    add("admission", 2, "p")
    add("pending", 2, "q")
    add("pending", 10**12, "r")  # still claimable: blocks
    incident.denied("settle", "conflicting_user_operation")
    with incident.harness.runtime.sessions.begin() as db:
        db.delete(db.get(WriteRecord, "r" * 43))
    assert incident.settle().original_outcome == "execution_uncertain"


def test_transient_disagreement_settles_after_bounded_quiescence(
    incident: Incident,
) -> None:
    original = incident.provider.handle
    reads = {"features": 0}

    def settling(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/features"):
            reads["features"] += 1
            if reads["features"] == 1:
                incident.provider.data["transient"] = True
            else:
                incident.provider.data.pop("transient", None)
        return original(request)

    incident.transport = httpx.MockTransport(settling)
    seen = incident.inspect()
    assert seen.stable and seen.denial is None and seen.captures == 3
    assert seen.instability == "settled_after_inventory_change"
    assert seen.instability_path == ("transient", "<present>")
    assert incident.posts == 1


def test_a_revision_that_keeps_moving_never_counts_as_stable_and_is_bounded(
    incident: Incident,
) -> None:
    original = incident.provider.handle
    reads = {"n": 0}

    def moving(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("currentmicroversion"):
            reads["n"] += 1  # two head reads bracket each capture
            marker = f"{(reads['n'] - 1) // 2 + 1:024x}"
            incident.provider.marker = marker
            incident.provider.data["sourceMicroversion"] = marker
        return original(request)

    incident.transport = httpx.MockTransport(moving)
    seen = incident.inspect()
    assert not seen.stable and seen.captures == 4  # bounded: never a fifth read set
    assert seen.denial == seen.instability == "revision_still_moving"
    assert seen.instability_path == ()
    incident.denied("settle", "revision_still_moving")


def test_a_head_that_moves_inside_one_read_set_is_a_moving_revision(
    incident: Incident,
) -> None:
    original = incident.provider.handle
    reads = {"n": 0}

    def inside(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("currentmicroversion"):
            reads["n"] += 1
            incident.provider.marker = f"{reads['n']:024x}"
        return original(request)

    incident.transport = httpx.MockTransport(inside)
    incident.denied("settle", "revision_still_moving")


@pytest.mark.parametrize(
    ("value", "check", "chain"),
    [
        ([], None, ()),
        (
            [{"btType": "BTMParameter-1"}],
            "ack_parameter_libraries",
            ("ack_parameter_libraries",),
        ),
    ],
)
def test_inspection_classifies_parameter_libraries(
    incident: Incident, value: Any, check: str | None, chain: tuple[str, ...]
) -> None:
    incident.provider.data["features"][0]["parameterLibraries"] = value
    seen = incident.inspect()
    assert seen.ack_check == check and seen.ack_chain == chain


def test_inspection_peels_unknown_keys_to_show_what_fails_next(
    incident: Incident,
) -> None:
    feature = incident.provider.data["features"][0]
    feature["bogusProviderKey"] = 1
    feature["constraints"] = [{"btType": "BTMSketchConstraint-2"}]
    seen = incident.inspect()
    assert seen.ack_check == "ack_feature_keys"
    assert seen.ack_chain == ("ack_feature_keys", "ack_constraints")
    assert seen.ack_fields == ("bogusProviderKey",)
