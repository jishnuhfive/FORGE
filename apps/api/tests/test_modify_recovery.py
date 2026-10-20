"""Synthetic recovery tests; no live CAD or AI transport."""

import json
from typing import Any

import pytest
from conftest import Harness
from sqlalchemy import select
from test_cad_read import REF
from test_modify_plan import PlanProvider, prepare, request_for
from test_modify_plan_routes import private_free
from test_safe_edit import running

from forge_api.cad_edits import plan_service, plan_storage, storage
from forge_api.cad_edits.domain import EditError
from forge_api.cad_edits.plans import OperationState, PlanPreview, PlanResult
from forge_api.db.models import AuditEvent, WriteFence, WriteRecord, now
from forge_api.integrations.onshape.service import ReadGate

PATH = "/api/modify/recovery"


def uncertain(h: Harness, kinds: tuple[str, ...] = ("SET_SUPPRESSED",)) -> PlanPreview:
    _, preview = prepare(h, kinds)
    with h.runtime.sessions.begin() as db:
        row = db.get(WriteRecord, preview.proposal_id)
        assert row
        plan = plan_storage.load(row).plan
        plan_storage.claim(db, row.id, row.user_id, row.session_hash, preview.digest)
    states: list[OperationState] = ["execution_uncertain"]
    states.extend("skipped" for _ in range(len(kinds) - 1))
    with h.runtime.sessions.begin() as db:
        plan_storage.finish(
            db,
            plan,
            PlanResult(
                state="execution_uncertain",
                operations=tuple(states),
            ),
        )
    return preview


def recovery(h: Harness, **extra: Any) -> Any:
    return h.client.post(
        PATH, json={"context": REF.model_dump(), **extra}, headers=h.headers()
    )


def reconcile(h: Harness, p: PlanPreview, body: object = None) -> Any:
    h.client.app.state.cad_gate = ReadGate()  # type: ignore[attr-defined]
    return h.client.post(
        f"/api/modify/plans/{p.proposal_id}/reconcile",
        json={} if body is None else body,
        headers=h.headers(),
    )


def current(provider: PlanProvider, suppressed: bool) -> None:
    provider.marker = "e" * 24
    provider.data["sourceMicroversion"] = provider.marker
    provider.data["features"][-1]["suppressed"] = suppressed
    identity = provider.data["features"][-1]["featureId"]
    if provider.data["featureStates"]:
        provider.data["featureStates"][identity]["inactive"] = suppressed


def test_no_fence_no_reads(harness: Harness) -> None:
    provider = PlanProvider()
    with running(harness, provider):
        assert recovery(harness).json() == {"state": "none"}
        assert provider.calls == []


def test_remount_discovery_is_private_and_cannot_approve(harness: Harness) -> None:
    provider = PlanProvider()
    with running(harness, provider):
        p = uncertain(harness)
        before = len(provider.calls)
        first = recovery(harness)
        assert first.status_code == 200
        assert first.headers["cache-control"] == "no-store"
        assert first.json() == recovery(harness).json()
        view = first.json()
        assert set(view) == {
            "state",
            "plan",
            "operations",
            "operation_states",
            "reconciliation",
        }
        assert view["plan"] == p.proposal_id
        assert view["reconciliation"] == "available"
        private_free(view)
        assert "digest" not in json.dumps(view)
        assert p.digest not in json.dumps(view)
        assert len(provider.calls) == before
        approved = harness.client.post(
            f"/api/modify/plans/{p.proposal_id}/approve",
            json={"digest": p.digest},
            headers=harness.headers(),
        )
        assert approved.status_code == 409
        assert approved.json()["detail"] == "proposal_used"
        assert provider.writes == 0


@pytest.mark.parametrize(
    "boundary", ["user", "session", "workspace", "element", "generation"]
)
def test_discovery_ownership(harness: Harness, boundary: str) -> None:
    provider = PlanProvider()
    with running(harness, provider):
        p = uncertain(harness)
        context = REF.model_dump()
        with harness.runtime.sessions.begin() as db:
            row = db.get(WriteRecord, p.proposal_id)
            assert row
            if boundary == "session":
                row.session_hash = "f" * 64
            elif boundary == "user":
                # Simulate a different current authenticated identity, without
                # introducing unrelated identity fixture requirements.
                from forge_api.db.models import User

                user = User(
                    stack="https://cad.onshape.com",
                    onshape_user_id="synthetic-other",
                    display_name="Other",
                )
                db.add(user)
                db.flush()
                row.user_id = user.id
            elif boundary == "generation":
                from forge_api.db.models import OnshapeAuthorization

                grant = db.scalar(select(OnshapeAuthorization))
                assert grant
                grant.generation = "synthetic-new-generation"
        if boundary in ("workspace", "element"):
            context["workspaceId" if boundary == "workspace" else "elementId"] = (
                "f" * 24
            )
        response = harness.client.post(
            PATH, json={"context": context}, headers=harness.headers()
        )
        assert response.json() == {"state": "none"}
        assert provider.writes == 0


@pytest.mark.parametrize("kind", ["SET_SUPPRESSED", "SET_UNSUPPRESSED"])
def test_success_closes_current_state_only_and_allows_fresh_plan(
    harness: Harness, kind: str
) -> None:
    provider = PlanProvider()
    if kind == "SET_UNSUPPRESSED":
        current(provider, True)
    with running(harness, provider):
        p = uncertain(harness, (kind,))
        with pytest.raises(EditError, match="workspace_fenced"):
            plan_service.discover(request_for(harness), harness.runtime, REF)
        current(provider, kind == "SET_SUPPRESSED")
        before = len(provider.calls)
        response = reconcile(harness, p)
        assert response.status_code == 200
        assert response.json() == {
            "state": "reconciled_current_state",
            "operations": ["execution_uncertain"],
        }
        assert "verified_success" not in response.text
        assert all(c.method == "GET" for c in provider.calls[before:])
        assert provider.writes == 0
        with harness.runtime.sessions() as db:
            assert db.scalar(select(WriteFence)) is None
            row = db.get(WriteRecord, p.proposal_id)
            assert row and row.payload and "baseline" not in row.payload
            assert db.scalar(
                select(AuditEvent).where(
                    AuditEvent.kind == "write_current_state_reconciled"
                )
            )
        assert recovery(harness).json() == {"state": "none"}
        assert (
            plan_service.status(
                request_for(harness), harness.runtime, p.proposal_id
            ).state
            == "reconciled_current_state"
        )
        harness.client.app.state.cad_gate = ReadGate()  # type: ignore[attr-defined]
        plan_service.discover(request_for(harness), harness.runtime, REF)
        assert reconcile(harness, p).status_code == 409


@pytest.mark.parametrize(
    "change",
    [
        "suppression",
        "definition",
        "identity",
        "serialization",
        "library",
        "parent",
        "configuration",
        "partial_states",
        "body",
    ],
)
def test_mismatch_retains_fence_and_performs_zero_writes(
    harness: Harness, change: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = PlanProvider()
    with running(harness, provider):
        p = uncertain(harness)
        current(provider, True)
        if change == "suppression":
            current(provider, False)
        elif change == "definition":
            provider.data["features"][0]["name"] = "Unrelated edit"
        elif change == "identity":
            provider.data["features"][-1]["featureId"] = "synthetic-replaced"
        elif change == "serialization":
            provider.data["serializationVersion"] = "different"
        elif change == "library":
            provider.data["libraryVersion"] += 1
        elif change == "parent":
            provider.data["features"][-1]["parentSuppressed"] = True
        elif change == "partial_states":
            provider.data["featureStates"] = {"unknown": {}}
        elif change == "configuration":
            import test_modify_plan
            from test_safe_edit import config

            monkeypatch.setattr(
                test_modify_plan,
                "config",
                lambda marker: {**config(marker), "currentConfiguration": ["changed"]},
            )
        elif change == "body":
            import test_modify_plan
            from test_safe_edit import bodies

            monkeypatch.setattr(
                test_modify_plan,
                "bodies",
                lambda marker, **kw: {**bodies(marker, **kw), "errorEnum": "ERROR"},
            )
        before = len(provider.calls)
        response = reconcile(harness, p)
        assert response.status_code == 409
        assert response.json() == {"detail": "recovery_required"}
        assert provider.writes == 0
        assert all(c.method == "GET" for c in provider.calls[before:])
        with harness.runtime.sessions() as db:
            assert db.scalar(select(WriteFence)) is not None
        with pytest.raises(EditError, match="workspace_fenced"):
            plan_service.discover(request_for(harness), harness.runtime, REF)


@pytest.mark.parametrize(
    "kinds",
    [
        ("RENAME_FEATURE",),
        ("SET_EXTRUDE_DEPTH",),
        ("SET_FILLET_RADIUS",),
        ("SET_EXTRUDE_DEPTH", "SET_SUPPRESSED"),
    ],
)
def test_manual_cases_never_read_or_write(
    harness: Harness, kinds: tuple[str, ...]
) -> None:
    provider = PlanProvider()
    with running(harness, provider):
        p = uncertain(harness, kinds)
        assert recovery(harness).json()["reconciliation"] == "manual_required"
        before = len(provider.calls)
        assert reconcile(harness, p).json() == {"detail": "recovery_required"}
        assert len(provider.calls) == before
        assert provider.writes == 0


def test_live_fence_retains_bounded_evidence_until_safe_resolution(
    harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = PlanProvider()
    with running(harness, provider):
        p = uncertain(harness)
        with harness.runtime.sessions.begin() as db:
            row = db.get(WriteRecord, p.proposal_id)
            assert row
            row.purge_at = now() - 1
            db.flush()
            storage.cleanup(db)
            assert row.payload is not None
        assert recovery(harness).json()["plan"] == p.proposal_id
        at = now() + 7 * 24 * 60 * 60 + 1
        monkeypatch.setattr(storage, "now", lambda: at)
        view = recovery(harness).json()
        assert view["state"] == "execution_uncertain"
        assert view["plan"] == p.proposal_id
        with harness.runtime.sessions() as db:
            row = db.get(WriteRecord, p.proposal_id)
            assert row and row.payload
            assert db.scalar(select(WriteFence))
            assert len(row.payload.encode()) < 32768
        assert provider.writes == 0


@pytest.mark.parametrize(
    "extra",
    [
        {"digest": "d" * 64},
        {"plan": "p" * 43},
        {"operation": "SET_SUPPRESSED"},
        {"approved": True},
        {"target": "t" * 43},
    ],
)
def test_closed_recovery_and_reconcile_bodies(
    harness: Harness, extra: dict[str, object]
) -> None:
    with running(harness, PlanProvider()):
        p = uncertain(harness)
        assert recovery(harness, **extra).status_code == 400
        assert reconcile(harness, p, extra).status_code == 400


@pytest.mark.parametrize("guard", ["csrf", "origin", "unauthenticated", "query"])
def test_recovery_and_reconcile_guard(harness: Harness, guard: str) -> None:
    provider = PlanProvider()
    with running(harness, provider):
        p = uncertain(harness)
        headers = harness.headers()
        query = ""
        if guard == "csrf":
            headers.pop("X-CSRF-Token")
        elif guard == "origin":
            headers["Origin"] = "https://untrusted.invalid"
        elif guard == "unauthenticated":
            harness.client.cookies.clear()
        else:
            query = "?approved=true"
        for path, body in [
            (PATH, {"context": REF.model_dump()}),
            (f"/api/modify/plans/{p.proposal_id}/reconcile", {}),
        ]:
            response = harness.client.post(path + query, json=body, headers=headers)
            assert response.status_code == (
                401 if guard == "unauthenticated" else 400 if guard == "query" else 403
            )
        assert provider.writes == 0


def test_resolved_records_are_eventually_purged(harness: Harness) -> None:
    provider = PlanProvider()
    with running(harness, provider):
        p = uncertain(harness)
        current(provider, True)
        assert reconcile(harness, p).status_code == 200
        with harness.runtime.sessions.begin() as db:
            row = db.get(WriteRecord, p.proposal_id)
            assert row
            row.purge_at = now() - 1
            db.flush()
            storage.cleanup(db)
            assert db.get(WriteRecord, p.proposal_id) is None
            assert db.scalar(select(WriteFence)) is None


def test_expired_claim_is_discovered_but_never_resumed(
    harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = PlanProvider()
    with running(harness, provider):
        _, p = prepare(harness, ("SET_SUPPRESSED",))
        with harness.runtime.sessions.begin() as db:
            row = db.get(WriteRecord, p.proposal_id)
            assert row
            plan_storage.claim(db, row.id, row.user_id, row.session_hash, p.digest)
            at = row.created_at + 151
        monkeypatch.setattr(storage, "now", lambda: at)
        result = recovery(harness).json()
        assert result["state"] == "execution_uncertain"
        assert result["operation_states"] == ["execution_uncertain"]
        assert provider.writes == 0


@pytest.mark.parametrize("change", ["session", "grant", "head"])
def test_authority_or_head_change_during_inspection_cannot_release(
    harness: Harness, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    from forge_api.cad_edits import plan_recovery
    from forge_api.db.models import OnshapeAuthorization, Session

    provider = PlanProvider()
    with running(harness, provider):
        p = uncertain(harness)
        current(provider, True)
        original = plan_service._capture

        def capture(*args: Any, **kwargs: Any) -> Any:
            evidence = original(*args, **kwargs)
            with harness.runtime.sessions.begin() as db:
                if change == "session":
                    row = db.scalar(select(Session))
                    assert row
                    row.revoked_at = now()
                elif change == "grant":
                    grant = db.scalar(select(OnshapeAuthorization))
                    assert grant
                    grant.generation = "synthetic-new-generation"
            if change == "head":
                provider.marker = "d" * 24
                provider.data["sourceMicroversion"] = provider.marker
            return evidence

        monkeypatch.setattr(plan_service, "_capture", capture)
        harness.client.app.state.cad_gate = ReadGate()  # type: ignore[attr-defined]
        with pytest.raises(EditError):
            plan_recovery.reconcile(
                request_for(harness), harness.runtime, p.proposal_id
            )
        with harness.runtime.sessions() as db:
            assert db.scalar(select(WriteFence))
        assert provider.writes == 0
