"""No public registration, receipt impersonation, generic enrollment or writes."""

import ast
import inspect
import json
from pathlib import Path
from typing import Any, cast

import pytest
from fastapi import FastAPI
from legacy_support import LegacyCase
from pydantic import ValidationError
from test_legacy_recovery import case as case

from forge_api.cad_edits import dev_recovery, legacy_policy, legacy_recovery
from forge_api.cad_edits.legacy_contracts import LegacyRecoveryDenied
from forge_api.cad_edits.retained_contracts import IndependentOperationEvidence


def test_shipped_case_has_no_enrollment_or_auto_discovery(
    case: LegacyCase, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(legacy_policy, "_ENROLLMENT", None)

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("unenrolled policy accessed DB")

    monkeypatch.setattr(legacy_recovery, "validate_locked", forbidden)
    with pytest.raises(LegacyRecoveryDenied, match="legacy_case_not_enrolled"):
        case.recover()
    assert case.provider.calls == []
    policy = inspect.getsource(legacy_policy)
    assert "_ENROLLMENT: LegacyEnrollment | None = None" in policy
    for text in (
        "getenv",
        "read_text",
        "json.load(",
        "allow_legacy",
        "build_enrollment",
    ):
        assert text not in policy


def test_legacy_identity_cannot_be_a_v1_receipt(case: LegacyCase) -> None:
    with pytest.raises(ValidationError):
        IndependentOperationEvidence.model_validate_json(
            json.dumps(case.enrollment.model_dump(mode="json"))
        )


def test_orphan_helper_still_rejects_retained_record(case: LegacyCase) -> None:
    e = case.enrollment
    reference = dev_recovery.RecoveryReference(
        user=e.binding.user,
        session=e.binding.session,
        workspace_key=e.fence_workspace_key,
        record_id=e.record_id,
        created_at=e.created_at,
        settled=True,
    )
    before = case.snapshot()
    with pytest.raises(dev_recovery.RecoveryDenied, match="referenced_record_present"):
        dev_recovery.recover_orphaned_fence(
            case.harness.runtime.sessions, case.harness.runtime.settings, reference
        )
    assert case.snapshot() == before and not case.provider.calls


def test_private_modules_are_not_registered_and_release_imports_are_provider_free(
    case: LegacyCase,
) -> None:
    root = Path(__file__).resolve().parents[3]
    source = root / "apps/api/src/forge_api"
    allowed = {
        "legacy_contracts.py",
        "legacy_policy.py",
        "legacy_enrollment.py",
        "legacy_reader.py",
        "legacy_recovery.py",
        "legacy_release.py",
    }
    for path in source.rglob("*.py"):
        text = path.read_text()
        if path.name not in allowed:
            assert "legacy_recovery" not in text and "legacy_release" not in text
        else:
            assert (
                "SafeEditClient" not in text
                and "argparse" not in text
                and "__main__" not in text
            )
            assert (
                "RetainedRecoveryReference" not in text
                and "IndependentOperationEvidence" not in text
            )
    for name in (
        "legacy_release.py",
        "legacy_enrollment.py",
        "legacy_contracts.py",
        "legacy_policy.py",
    ):
        tree = ast.parse((source / "cad_edits" / name).read_text())
        modules = [
            n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
        ]
        modules += [
            a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names
        ]
        assert all(
            not any(
                x in module
                for x in (
                    "httpx",
                    "tokens",
                    "runtime",
                    "reader",
                    "provider",
                    "write_client",
                    "legacy_recovery",
                )
            )
            for module in modules
        )
    app = cast(FastAPI, case.harness.client.app)
    assert not any(
        "legacy" in path or "operator" in path for path in app.openapi()["paths"]
    )
    for directory in ("apps/web/src", "scripts"):
        for path in (root / directory).rglob("*"):
            if path.is_file() and path.suffix in (".py", ".ts", ".tsx", ".json"):
                assert "retire_legacy_record" not in path.read_text()
    assert set(inspect.signature(legacy_recovery.retire_legacy_record).parameters) == {
        "sessions",
        "settings",
        "tokens",
        "review",
        "transport",
    }
