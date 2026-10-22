"""Only closed development verification categories may enter the log."""

import logging
from typing import Any

import pytest
from conftest import Harness
from test_modify_plan import PlanProvider, approve, prepare
from test_safe_edit import running

from forge_api.cad_edits import plan_diagnostics, plan_service


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
