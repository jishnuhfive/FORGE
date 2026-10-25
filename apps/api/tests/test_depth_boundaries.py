"""Private capability boundaries and strict V1 operation/journal eligibility."""

import ast
import json
from pathlib import Path
from typing import Any, cast

import pytest
from depth_support import DepthCase
from fastapi import FastAPI
from test_depth_recovery import case as case

from forge_api.cad_edits import depth_recovery, depth_release, plan_storage
from forge_api.cad_edits.depth_contracts import (
    DepthRecoveryDenied,
)
from forge_api.cad_edits.plans import StoredPlan
from forge_api.db.models import AuditEvent, OnshapeAuthorization, WriteRecord, now


@pytest.mark.parametrize(
    "change",
    [
        "rename",
        "suppression",
        "radius",
        "batch",
        "nonterminal",
        "wrong_type",
        "preview",
        "unverified",
        "claimed_journal",
    ],
)
def test_v1_rejects_every_unsupported_operation_or_journal(
    case: DepthCase, change: str
) -> None:
    with case.harness.runtime.sessions() as db:
        row = db.get(WriteRecord, case.reference.historical.record_id)
        assert row
        value = plan_storage.load(row).model_dump(mode="json")
    op = value["plan"]["operations"][0]
    if change in ("rename", "suppression", "radius"):
        kind = {
            "rename": "RENAME_FEATURE",
            "suppression": "SET_SUPPRESSED",
            "radius": "SET_FILLET_RADIUS",
        }[change]
        op["operation"] = {
            "type": kind,
            "target": op["target"]["handle"],
            **(
                {"new_name": "New"}
                if change == "rename"
                else {}
                if change == "suppression"
                else {"quantity": "4 mm"}
            ),
        }
        op["preview"]["type"] = kind
    elif change == "batch":
        value["plan"]["operations"].append(op.copy())
        value["result"]["operations"].append("execution_uncertain")
    elif change == "nonterminal":
        op["target"]["position"] -= 1
    elif change == "wrong_type":
        op["target"]["feature_type"] = "fillet"
    elif change == "same_state":
        value["plan"]["baseline"]["suppressed"] = True
    elif change == "preview":
        op["preview"]["position"] += 1
    elif change == "unverified":
        value["result"]["operations"] = ["verified_success"]
    else:
        value["result"] = {"state": "claimed", "operations": ["executing"]}
    saved = StoredPlan.model_validate_json(json.dumps(value))
    before = case.snapshot()
    with pytest.raises(DepthRecoveryDenied):
        depth_release._eligible(saved)
    assert case.snapshot() == before and not case.provider.calls


@pytest.mark.parametrize(
    "change", ["writes", "environment", "generation", "payload", "conflict", "audit"]
)
def test_post_capture_revalidation_fails_closed(
    case: DepthCase, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    original = depth_release.release_depth_record
    before = case.snapshot()

    def release(db: Any, settings: Any, run: Any, evidence: Any) -> Any:
        if change == "writes":
            settings.forge_cad_writes_enabled = True
        elif change == "environment":
            settings.environment = "production"
        elif change == "generation":
            grant = db.get(OnshapeAuthorization, case.reference.independent.user)
            assert grant
            grant.generation = "synthetic-changed"
        elif change == "payload":
            row = db.get(WriteRecord, case.reference.historical.record_id)
            assert row and row.payload
            row.payload += (
                " "  # Canonically same plan; exact raw snapshot still rejects.
            )
        elif change == "conflict":
            db.add(
                WriteRecord(
                    id="f" * 43,
                    user_id=case.reference.independent.user,
                    session_hash=case.reference.historical.binding.session,
                    state="pending",
                    digest="a" * 64,
                    payload=None,
                    created_at=now(),
                    expires_at=now() + 120,
                    purge_at=now() + 900,
                )
            )
        else:
            db.add(
                AuditEvent(
                    user_id=case.reference.independent.user,
                    kind="write_verified",
                    outcome="ok",
                    created_at=now(),
                )
            )
        db.flush()
        return original(db, settings, run, evidence)

    monkeypatch.setattr(depth_recovery, "release_depth_record", release)
    with pytest.raises(DepthRecoveryDenied):
        case.recover()
    assert case.snapshot() == before


def test_internal_modules_have_no_public_or_mutation_registration(
    case: DepthCase,
) -> None:
    root = Path(__file__).resolve().parents[3]
    source = root / "apps/api/src/forge_api"
    allowed_callers = {
        "depth_contracts.py",
        "depth_release.py",
        "depth_recovery.py",
        "depth_reader.py",
        "quantity_recovery_evidence.py",
    }
    for path in source.rglob("*.py"):
        if path.name not in allowed_callers:
            assert "depth_recovery" not in path.read_text()
            assert "depth_release" not in path.read_text()
        if path.name in allowed_callers:
            text = path.read_text()
            assert "SafeEditClient" not in text
            assert "__main__" not in text and "argparse" not in text
    release = source / "cad_edits/depth_release.py"
    imports = [
        n.module or ""
        for n in ast.walk(ast.parse(release.read_text()))
        if isinstance(n, ast.ImportFrom)
    ]
    assert all(
        not any(
            x in module
            for x in (
                "tokens",
                "runtime",
                "reader",
                "write_client",
                "depth_recovery",
                "provider",
            )
        )
        for module in imports
    )
    app = cast(FastAPI, case.harness.client.app)
    assert not any(
        "retained" in path or "operator" in path for path in app.openapi()["paths"]
    )
    for path in (root / "apps/web/src").rglob("*"):
        if path.is_file():
            assert "operator_recovered" not in path.read_text()
            assert "recover_depth_record" not in path.read_text()


def test_unrelated_user_work_is_not_recovery_authority_or_global_blocker(
    case: DepthCase,
) -> None:
    from forge_api.db.models import User

    with case.harness.runtime.sessions.begin() as db:
        user = User(
            stack=case.reference.review.stack,
            onshape_user_id="synthetic-unrelated",
            display_name="Other",
        )
        db.add(user)
        db.flush()
        db.add(
            WriteRecord(
                id="f" * 43,
                user_id=user.id,
                session_hash="a" * 64,
                state="pending",
                digest="a" * 64,
                payload=None,
                created_at=now(),
                expires_at=now() + 120,
                purge_at=now() + 900,
            )
        )
    case.recover()
