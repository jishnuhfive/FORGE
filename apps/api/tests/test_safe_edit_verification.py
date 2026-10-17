"""Comprehensive synthetic verification, diagnostics, timeout and no-retry coverage."""

import json
import logging
from copy import deepcopy

import httpx2 as httpx
import pytest
from conftest import Harness
from pydantic import ValidationError
from sqlalchemy import select
from test_cad_read import REF
from test_safe_edit import M0, M1, approve, bodies, config, prepare, running
from test_safe_edit_guard_evidence import OmittedProvider, omitted_features

from forge_api.cad_edits import service, verification
from forge_api.cad_edits.domain import Binding, EditError, Proposal
from forge_api.core.config import Settings
from forge_api.db.models import AuditEvent, WriteFence, WriteRecord
from forge_api.integrations.onshape import write_client
from forge_api.integrations.onshape.dev import verify as diagnostic
from forge_api.integrations.onshape.dev.verify import (
    Category,
    Entry,
    Snapshot,
    diagnose,
)
from forge_api.integrations.onshape.write_evidence import project_write_evidence


def snapshots() -> tuple[Proposal, Snapshot, Snapshot]:
    before = Snapshot(
        microversion=M0,
        features=omitted_features(),
        configuration=config(),
        bodies=bodies(explicit_flags=False),
    )
    data = omitted_features()
    data["sourceMicroversion"] = M1
    data["features"][-1]["suppressed"] = True
    after = Snapshot(
        microversion=M1,
        features=data,
        configuration=config(M1),
        bodies=bodies(M1, explicit_flags=False),
    )
    baseline = project_write_evidence(
        REF,
        M0,
        before.features,
        before.configuration,
        before.bodies,
        pinned_body_microversion=M0,
    )
    proposal = Proposal(
        proposal_id="A" * 43,
        binding=Binding(
            user="synthetic-user",
            session="0" * 64,
            generation="synthetic-generation",
            context=REF,
            workspace_key="1" * 64,
        ),
        baseline=baseline,
        created_at=1,
        expires_at=121,
    )
    return proposal, before, after


def test_complete_report_preserves_honest_missing_facts() -> None:
    proposal, before, after = snapshots()
    report = diagnose(
        Settings(_env_file=None),
        proposal,
        before,
        after,
        head_bracketed=True,
        acknowledged_at_runtime=True,
        audit_elapsed_ms=3000,
    )
    failed = [r.check for r in report if r.result == "fail"]
    assert failed == ["ack_details_available", "original_timing_available"]
    changed = [r for r in report if r.check == "changed_field"]
    assert len(changed) == 1 and changed[0].position == 3
    assert changed[0].category == Category.SUPPRESSED and changed[0].result == "pass"
    serialized = json.dumps([x.model_dump(mode="json") for x in report])
    for value in (
        REF.documentId,
        M0,
        M1,
        "synthetic-feature",
        "synthetic-body",
        "Fixture",
        "https://",
    ):
        assert value not in serialized


def test_projection_failure_does_not_hide_other_available_mismatches() -> None:
    proposal, before, after = snapshots()
    data = deepcopy(after.features)
    assert isinstance(data, dict) and isinstance(data["features"], list)
    data["libraryVersion"] = 1
    data["serializationVersion"] = "changed"
    feature = data["features"][1]
    assert isinstance(feature, dict)
    feature["private-synthetic-field"] = True
    body = bodies(M1, explicit_flags=False)
    body["bodies"] = []
    changed = after.model_copy(update={"features": data, "bodies": body})
    report = diagnose(
        Settings(_env_file=None),
        proposal,
        before,
        changed,
        head_bracketed=True,
        acknowledged_at_runtime=True,
    )
    failed = {r.check for r in report if r.result == "fail"}
    assert {
        "projection",
        "serialization",
        "library",
        "definitions",
        "evidence_modes_available",
        "one_solid",
    } <= failed


@pytest.mark.parametrize(
    "field", ["unknown", "nodeId", "parameters", "query", "bool_to_int"]
)
@pytest.mark.parametrize("position", [0, 1, 2])
def test_report_rejects_changes_at_every_position_and_never_outputs_unknown_keys(
    field: str, position: int
) -> None:
    proposal, before, after = snapshots()
    data = deepcopy(after.features)
    assert isinstance(data, dict) and isinstance(data["features"], list)
    feature = data["features"][position]
    assert isinstance(feature, dict)
    category = Category.UNKNOWN
    if field == "unknown":
        feature["private-synthetic-field"] = "private-synthetic-value"
    elif field == "nodeId":
        feature["nodeId"] = "private-synthetic-node"
        category = Category.NODE
    elif field == "parameters":
        feature["parameters"] = [{"expression": "private-synthetic-expression"}]
        category = Category.PARAMETER
    elif field == "query":
        feature["parameters"] = [
            {"queries": [{"queryString": "private-synthetic-query"}]}
        ]
        category = Category.PARAMETER
    else:
        feature["returnAfterSubfeatures"] = 0
        category = Category.RETURN
    changed = after.model_copy(update={"features": data})
    report = diagnose(
        Settings(_env_file=None),
        proposal,
        before,
        changed,
        head_bracketed=True,
        acknowledged_at_runtime=True,
    )
    assert any(
        r.check == "definitions" and r.position == position + 1 and r.result == "fail"
        for r in report
    )
    assert any(r.category == category and r.result == "fail" for r in report)
    assert "private-synthetic" not in json.dumps(
        [r.model_dump(mode="json") for r in report]
    )
    if field in ("parameters", "query"):
        query = next(
            r for r in report if r.check == "queries" and r.position == position + 1
        )
        assert query.result == ("fail" if field == "query" else "pass")


@pytest.mark.parametrize(
    "environment,writes", [("production", False), ("development", True)]
)
def test_offline_diagnostic_is_development_and_writes_off_only(
    environment: str, writes: bool
) -> None:
    proposal, before, after = snapshots()
    settings = Settings(_env_file=None).model_copy(
        update={"environment": environment, "forge_cad_writes_enabled": writes}
    )
    with pytest.raises(EditError):
        diagnose(
            settings,
            proposal,
            before,
            after,
            head_bracketed=True,
            acknowledged_at_runtime=True,
        )


def test_all_final_comparisons_keep_exact_marker_and_definitions() -> None:
    proposal, _, after = snapshots()
    baseline = proposal.baseline
    current = project_write_evidence(
        REF,
        M1,
        after.features,
        after.configuration,
        after.bodies,
        after=True,
        pinned_body_microversion=M1,
    )
    assert all(verification.final_checks(baseline, current, M1, 3).values())
    changed = current.model_copy(
        update={
            "serialization": "changed",
            "library": current.library + 1,
            "feature_id": "synthetic-replaced",
            "definitions": "0" * 64,
            "parent_suppression_evidence": (),
            "configured_suppression_evidence": (),
        }
    )
    checks = verification.final_checks(baseline, changed, "f" * 24, 31)
    assert len(checks) == 8 and not any(checks.values())
    assert len(verification.failures(checks)) == 8


@pytest.mark.parametrize("elapsed", [float("inf"), float("nan"), -1, 30.001])
def test_deadline_is_bounded_and_never_removed(elapsed: float) -> None:
    proposal, _, after = snapshots()
    current = project_write_evidence(
        REF,
        M1,
        after.features,
        after.configuration,
        after.bodies,
        after=True,
        pinned_body_microversion=M1,
    )
    assert (
        verification.final_checks(proposal.baseline, current, M1, elapsed)["deadline"]
        is False
    )


CHANGES = [
    "sketch",
    "extrude",
    "fillet",
    "parameter",
    "query",
    "type",
    "identity",
    "order",
    "removal",
    "insertion",
    "node",
    "unknown",
    "aux",
    "serialization",
    "library",
    "ack_marker",
    "post_marker",
    "not_suppressed",
    "body",
]


class ChangedProvider(OmittedProvider):
    change = ""

    def handle(self, request: httpx.Request) -> httpx.Response:
        if (
            self.change == "body"
            and self.marker == M1
            and request.url.path.endswith("/bodydetails")
        ):
            self.calls.append(request)
            data = bodies(M1, explicit_flags=False)
            data["bodies"] = []
            return httpx.Response(200, json=data)
        response = super().handle(request)
        if request.method != "POST":
            return response
        items = self.data["features"]
        if self.change in ("sketch", "extrude", "fillet"):
            items[{"sketch": 0, "extrude": 1, "fillet": 2}[self.change]]["name"] = (
                "private-synthetic-name"
            )
        elif self.change in ("parameter", "query"):
            items[-1]["parameters"] = (
                [{"queries": [{"queryString": "private-synthetic-query"}]}]
                if self.change == "query"
                else [{"expression": "private-synthetic-expression"}]
            )
        elif self.change == "type":
            items[-1]["featureType"] = "extrude"
        elif self.change == "identity":
            items[-1]["featureId"] = "private-synthetic-replaced"
        elif self.change == "order":
            items[:2] = reversed(items[:2])
        elif self.change == "removal":
            items.pop()
            self.data["rollbackIndex"] = len(items)
        elif self.change == "insertion":
            added = deepcopy(items[1])
            added["featureId"] = "private-synthetic-insertion"
            items.insert(1, added)
            self.data["rollbackIndex"] = len(items)
        elif self.change == "node":
            items[-1]["nodeId"] = "private-synthetic-node"
        elif self.change == "unknown":
            items[-1]["private-synthetic-field"] = "private-synthetic-value"
        elif self.change == "aux":
            items[-1]["suppressionState"] = {
                "btType": "BTMSuppressionState-1924",
                "suppressionConfigured": False,
            }
        elif self.change == "serialization":
            self.data["serializationVersion"] = "changed"
        elif self.change == "library":
            self.data["libraryVersion"] += 1
        elif self.change == "ack_marker":
            payload = response.json()
            payload["sourceMicroversion"] = "f" * 24
            response = httpx.Response(200, json=payload)
        elif self.change == "post_marker":
            self.marker = "f" * 24
            self.data["sourceMicroversion"] = self.marker
        elif self.change == "not_suppressed":
            items[-1]["suppressed"] = False
        return response


@pytest.mark.parametrize("change", CHANGES)
def test_unrelated_change_or_marker_mismatch_stays_uncertain_and_durable(
    harness: Harness, change: str, caplog: pytest.LogCaptureFixture
) -> None:
    fake = ChangedProvider()
    with running(harness, fake), caplog.at_level(logging.WARNING):
        harness.runtime.settings.environment = "development"
        proposal = prepare(harness)
        fake.change = change
        assert approve(harness, proposal)[-1]["state"] == "execution_uncertain"
        approve(harness, proposal)
    assert fake.writes == 1
    with harness.runtime.sessions() as db:
        assert db.scalar(select(WriteFence)) is not None
        row = db.get(WriteRecord, proposal["proposal_id"])
        assert row and row.state == "execution_uncertain"
        outcomes = list(
            db.scalars(
                select(AuditEvent.outcome).where(
                    AuditEvent.kind == "write_verification_failed"
                )
            )
        )
        assert outcomes
        if change == "identity":
            assert {"verify_target_identity", "verify_definitions"} <= set(outcomes)
        if change in ("ack_marker", "post_marker"):
            assert "verify_ack_revision" in outcomes
    for private in ("private-synthetic", REF.documentId, M0, M1):
        assert private not in caplog.text


def test_intended_only_transition_releases_fence_and_records_no_failed_check(
    harness: Harness, caplog: pytest.LogCaptureFixture
) -> None:
    fake = OmittedProvider()
    with running(harness, fake), caplog.at_level(logging.WARNING):
        harness.runtime.settings.environment = "development"
        proposal = prepare(harness)
        assert approve(harness, proposal)[-1]["state"] == "verified_success"
        approve(harness, proposal)
    assert fake.writes == 1
    checks = [
        r.message
        for r in caplog.records
        if r.message.startswith("safe_edit_verify stage=final_compare ")
    ]
    assert len(checks) == 8 and all("result=pass" in line for line in checks)
    with harness.runtime.sessions() as db:
        assert db.scalar(select(WriteFence)) is None
        assert (
            db.scalar(
                select(AuditEvent).where(AuditEvent.kind == "write_verification_failed")
            )
            is None
        )
        row = db.get(WriteRecord, proposal["proposal_id"])
        assert row and row.state == "verified_success" and row.payload is None


@pytest.mark.parametrize("phase", ["before", "ack", "post_read"])
def test_timeouts_preserve_budget_and_never_retry(
    harness: Harness, monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    class Clock:
        value = 0.0

        def __call__(self) -> float:
            return self.value

    clock = Clock()
    shifted = False
    armed = False

    class Slow(OmittedProvider):
        def handle(self, request: httpx.Request) -> httpx.Response:
            nonlocal shifted
            response = super().handle(request)
            if (
                armed
                and not shifted
                and (
                    (
                        phase == "before"
                        and request.url.path.endswith("/features")
                        and self.marker == M0
                    )
                    or (phase == "ack" and request.method == "POST")
                    or (
                        phase == "post_read"
                        and self.marker == M1
                        and request.url.path.endswith("/bodydetails")
                    )
                )
            ):
                clock.value += 26 if phase == "before" else 31
                shifted = True
            return response

    fake = Slow()
    with running(harness, fake):
        proposal = prepare(harness)
        monkeypatch.setattr(service, "monotonic", clock)
        monkeypatch.setattr(write_client, "monotonic", clock)
        armed = True
        result = approve(harness, proposal)[-1]
        if phase == "before":
            assert result["code"] == "model_changed" and fake.writes == 0
        else:
            assert result["state"] == "execution_uncertain" and fake.writes == 1
        approve(harness, proposal)
    with harness.runtime.sessions() as db:
        assert (db.scalar(select(WriteFence)) is not None) is (phase != "before")
    assert fake.writes == int(phase != "before")


@pytest.mark.parametrize("geometry_changed", [False, True])
def test_full_sketch_definition_is_fingerprinted_with_no_geometry_id_expansion(
    harness: Harness, geometry_changed: bool
) -> None:
    class FullSketch(OmittedProvider):
        def handle(self, request: httpx.Request) -> httpx.Response:
            response = super().handle(request)
            if request.url.path.endswith("/features"):
                assert dict(request.url.params) == {
                    "includeGeometryIds": "false",
                    "noSketchGeometry": "false",
                    "rollbackBarIndex": "-1",
                }
                data = response.json()
                data["features"][0]["entities"] = [
                    {
                        "synthetic_point": 1
                        if geometry_changed and self.marker == M1
                        else 0
                    }
                ]
                data["features"][0]["constraints"] = [{"synthetic_constraint": True}]
                return httpx.Response(200, json=data)
            return response

    fake = FullSketch()
    with running(harness, fake):
        proposal = prepare(harness)
        result = approve(harness, proposal)[-1]
        assert result["state"] == (
            "execution_uncertain" if geometry_changed else "verified_success"
        )
        approve(harness, proposal)
    assert fake.writes == 1
    with harness.runtime.sessions() as db:
        assert (db.scalar(select(WriteFence)) is not None) is geometry_changed


@pytest.mark.parametrize(
    "case",
    [
        "marker_old",
        "marker_missing",
        "skew",
        "feature_count",
        "feature_identity",
        "suppressed",
        "http_error",
        "nonjson",
    ],
)
def test_every_acknowledgement_requirement_stays_fail_closed(
    harness: Harness, case: str
) -> None:
    class BadAck(OmittedProvider):
        def handle(self, request: httpx.Request) -> httpx.Response:
            response = super().handle(request)
            if request.method != "POST":
                return response
            data = response.json()
            if case == "marker_old":
                data["sourceMicroversion"] = M0
            elif case == "marker_missing":
                del data["sourceMicroversion"]
            elif case == "skew":
                data["microversionSkew"] = True
            elif case == "feature_count":
                data["features"] = []
            elif case == "feature_identity":
                data["features"][0]["featureId"] = "synthetic-other"
            elif case == "suppressed":
                data["features"][0]["suppressed"] = False
            elif case == "http_error":
                return httpx.Response(500, json={})
            elif case == "nonjson":
                return httpx.Response(200, content=b"private-synthetic-error")
            return httpx.Response(200, json=data)

    fake = BadAck()
    with running(harness, fake):
        proposal = prepare(harness)
        assert approve(harness, proposal)[-1]["state"] == "execution_uncertain"
        approve(harness, proposal)
    assert fake.writes == 1
    with harness.runtime.sessions() as db:
        assert db.scalar(select(WriteFence)) is not None
        assert (
            db.scalar(
                select(AuditEvent).where(
                    AuditEvent.kind == "write_verification_failed",
                    AuditEvent.outcome == "verify_provider_ack",
                )
            )
            is not None
        )


def test_older_geometry_minimizing_proposal_policy_cannot_dispatch(
    harness: Harness,
) -> None:
    fake = OmittedProvider()
    with running(harness, fake):
        proposal = prepare(harness)
        with harness.runtime.sessions.begin() as db:
            row = db.get(WriteRecord, proposal["proposal_id"])
            assert row and row.payload
            data = json.loads(row.payload)
            data["policy_version"] = "terminal-fillet-5"
            from forge_api.cad_edits.domain import fingerprint

            row.payload = json.dumps(data)
            row.digest = fingerprint(data)
            proposal["digest"] = row.digest
        assert approve(harness, proposal)[-1]["code"] == "proposal_tampered"
    assert fake.writes == 0


def test_verification_debug_lines_are_not_emitted_in_production(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        verification.emit(False, "final_compare", "definitions", False)
    assert not caplog.records


@pytest.mark.parametrize(
    "change",
    [
        {"check": "private-synthetic-token"},
        {"category": "private-synthetic-token"},
        {"mode": "private-synthetic-token"},
        {"position": 21},
        {"elapsed_ms": 180001},
        {"raw_payload": "private-synthetic-token"},
    ],
)
def test_diagnostic_output_schema_rejects_private_values_and_unbounded_metadata(
    change: dict[str, object],
) -> None:
    with pytest.raises(ValidationError) as caught:
        Entry.model_validate(
            {"stage": "structural", "check": "definitions", "result": "fail", **change}
        )
    assert "private-synthetic-token" not in str(caught.value)


@pytest.mark.parametrize("marker", ["../features/updates", "", True, "f" * 23])
def test_full_definition_reader_requires_strict_marker_before_any_network_or_database(
    marker: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    proposal, _, _ = snapshots()

    def forbidden(*args: object) -> None:
        raise AssertionError("database/network must not be reached")

    monkeypatch.setattr(diagnostic, "make_engine", forbidden)
    with pytest.raises(ValidationError):
        diagnostic.read_definition_pair(Settings(_env_file=None), proposal, marker)  # type: ignore[arg-type]
