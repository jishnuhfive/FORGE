"""Only closed development verification categories may enter the log."""

import logging
from copy import deepcopy
from typing import Any

import httpx2 as httpx
import pytest
from conftest import Harness
from sqlalchemy import select
from test_modify_plan import PlanProvider, approve, prepare
from test_safe_edit import running

from forge_api.cad_edits import plan_diagnostics, plan_service, plan_storage
from forge_api.cad_edits.domain import EditError
from forge_api.cad_edits.plans import PlanResult
from forge_api.db.models import WriteFence
from forge_api.integrations.onshape.write_client import SafeEditClient


@pytest.mark.parametrize("development", [True, False])
@pytest.mark.parametrize("fail", [True, False])
def test_generalized_stages_are_fixed_and_development_only(
    harness: Harness,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    development: bool,
    fail: bool,
) -> None:
    provider = PlanProvider()
    with running(harness, provider):
        req, preview = prepare(harness, ("SET_SUPPRESSED",))
        harness.runtime.settings.environment = "development" if development else "test"
        if fail:

            def reject(*args: Any, **kwargs: Any) -> None:
                raise RuntimeError(
                    "synthetic-private-feature CAD-IDs token https://secret.invalid"
                )

            monkeypatch.setattr(plan_service, "verify_operation", reject)
        with caplog.at_level(logging.WARNING, logger=plan_diagnostics.logger.name):
            result = approve(harness, req, preview)
        messages = [
            r.getMessage()
            for r in caplog.records
            if r.name == plan_diagnostics.logger.name
            and r.getMessage().startswith("a2_verify ")
        ]
        assert result.state == ("execution_uncertain" if fail else "verified_success")
        expected = [
            "a2_verify stage=post_read result=pass",
            "a2_verify stage=operation_compare result=" + ("fail" if fail else "pass"),
        ]
        if not fail:
            expected += [
                "a2_verify stage=deadline result=pass",
                "a2_verify stage=authority result=pass",
            ]
        assert messages == (expected if development else [])
        if not development:
            assert not any(
                record.name == plan_diagnostics.logger.name for record in caplog.records
            )


@pytest.mark.parametrize(
    "failure,stage",
    [
        ("exchange", "provider_exchange"),
        ("skew", "ack_skew"),
        ("envelope", "ack_feature_envelope"),
        ("identity", "ack_target_identity"),
        ("effect", "ack_fingerprint"),
        ("marker_shape", "ack_marker_shape"),
        ("marker_advance", "ack_marker_advance"),
    ],
)
def test_dispatched_failure_has_closed_precise_diagnostic(
    harness: Harness,
    caplog: pytest.LogCaptureFixture,
    failure: str,
    stage: str,
) -> None:
    class AckProvider(PlanProvider):
        def handle(self, request: httpx.Request) -> httpx.Response:
            prior = self.marker
            response = super().handle(request)
            if request.method != "POST":
                return response
            if failure == "exchange":
                return httpx.Response(503, json={"private": "synthetic-secret"})
            data: dict[str, Any] = deepcopy(response.json())
            if failure == "skew":
                data["microversionSkew"] = True
            elif failure == "envelope":
                data.pop("feature")
            elif failure == "identity":
                data["feature"]["featureId"] = "synthetic-other"
            elif failure == "effect":
                data["feature"]["unexpected"] = "synthetic-secret"
            elif failure == "marker_shape":
                data["sourceMicroversion"] = None
            elif failure == "marker_advance":
                data["sourceMicroversion"] = prior
            return httpx.Response(200, json=data)

    provider = AckProvider()
    with running(harness, provider):
        req, preview = prepare(harness, ("SET_EXTRUDE_DEPTH",))
        harness.runtime.settings.environment = "development"
        with caplog.at_level(logging.WARNING, logger=plan_diagnostics.logger.name):
            result = approve(harness, req, preview)
        messages = [
            record.getMessage()
            for record in caplog.records
            if record.name == plan_diagnostics.logger.name
        ]
        assert result.state == "execution_uncertain"
        assert result.operations == ("execution_uncertain",)
        assert plan_service.status(req, harness.runtime, preview.proposal_id) == result
        assert provider.writes == 1
        with harness.runtime.sessions() as db:
            assert db.scalar(select(WriteFence)) is not None
        assert messages[-1] == f"a2_dispatch stage={stage} result=fail"
        assert not any("a2_verify" in message for message in messages)
        assert all("synthetic-secret" not in message for message in messages)


def test_ack_journal_failure_is_distinguished_from_ack_validation(
    harness: Harness,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    provider = PlanProvider()
    with running(harness, provider):
        req, preview = prepare(harness, ("SET_EXTRUDE_DEPTH",))
        harness.runtime.settings.environment = "development"
        original = plan_storage.journal

        def journal(db: Any, plan: Any, result: PlanResult) -> None:
            if result.state == "verifying":
                raise RuntimeError("synthetic-secret")
            original(db, plan, result)

        monkeypatch.setattr(plan_storage, "journal", journal)
        with caplog.at_level(logging.WARNING, logger=plan_diagnostics.logger.name):
            result = approve(harness, req, preview)
        messages = [
            record.getMessage()
            for record in caplog.records
            if record.name == plan_diagnostics.logger.name
        ]
        assert result.state == "execution_uncertain" and provider.writes == 1
        with harness.runtime.sessions() as db:
            assert db.scalar(select(WriteFence)) is not None
        assert messages[-2:] == [
            "a2_dispatch stage=ack_marker_advance result=pass",
            "a2_dispatch stage=ack_journal result=fail",
        ]
        assert not any("a2_verify" in message for message in messages)
        assert all("synthetic-secret" not in message for message in messages)


def test_dispatch_preflight_failure_is_sanitized_and_retains_uncertainty(
    harness: Harness,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    provider = PlanProvider()
    with running(harness, provider):
        req, preview = prepare(harness, ("SET_EXTRUDE_DEPTH",))
        harness.runtime.settings.environment = "development"
        original = SafeEditClient._operation_request
        calls = 0

        def preflight(self: SafeEditClient, evidence: Any, operation: Any) -> Any:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise EditError("unsupported_target", 422)
            return original(self, evidence, operation)

        monkeypatch.setattr(SafeEditClient, "_operation_request", preflight)
        with caplog.at_level(logging.WARNING, logger=plan_diagnostics.logger.name):
            result = approve(harness, req, preview)
        messages = [
            record.getMessage()
            for record in caplog.records
            if record.name == plan_diagnostics.logger.name
        ]
        assert result.state == "execution_uncertain" and provider.writes == 0
        with harness.runtime.sessions() as db:
            assert db.scalar(select(WriteFence)) is not None
        assert messages[-1] == "a2_dispatch stage=request_preflight result=fail"
        assert not any("a2_verify" in message for message in messages)
