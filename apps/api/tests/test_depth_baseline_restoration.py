"""Explicit baseline-restored administrative closure; synthetic provider/DB only."""

from copy import deepcopy
from typing import Any

import httpx2 as httpx
import pytest
import test_server_depth_recovery as recovery_tests
from conftest import Harness
from server_depth_support import ServerCase, review, seed_server
from sqlalchemy import select
from test_cad_read import REF
from test_modify_current_query_contracts import current_inventory
from test_modify_plan import PlanProvider
from test_modify_semantic_nodes import nodes
from test_modify_ui_conformance import param
from test_safe_edit import M0, bodies, config, running
from test_server_depth_console import console

from forge_api.cad_edits import depth_recovery, depth_release, plan_storage
from forge_api.cad_edits.depth_contracts import DepthRecoveryDenied, DepthRecoveryResult
from forge_api.cad_edits.domain import fingerprint
from forge_api.db.models import WriteFence, WriteRecord
from forge_api.integrations.onshape.modify_evidence import project_modify_raw_evidence


@pytest.fixture
def restored(harness: Harness) -> Any:
    provider = PlanProvider()
    provider.data = current_inventory()
    nodes(provider.data, "historical")
    original = deepcopy(provider.data)
    with running(harness, provider):
        case = seed_server(harness, provider)
        marker = provider.marker
        provider.data = deepcopy(original)
        provider.data["sourceMicroversion"] = marker
        nodes(provider.data, "restored")
        with harness.runtime.sessions.begin() as db:
            case.reference = depth_recovery._development_reference(
                db,
                harness.runtime.settings,
                review(harness).model_copy(update={"original_baseline_restored": True}),
            )
        yield case


def operator_recover(case: ServerCase) -> Any:
    return depth_recovery.recover_development_depth_incident(
        case.harness.runtime,
        review(case.harness).model_copy(update={"original_baseline_restored": True}),
        transport=httpx.MockTransport(case.provider.handle),
    )


def test_restored_closure_preserves_provenance_and_consumes_once(
    restored: ServerCase,
) -> None:
    result = operator_recover(restored)
    assert result.disposition == "independently_settled_original_baseline_restored"
    assert result.original_execution_outcome == "execution_uncertain"
    assert result.state == "operator_recovered"
    assert len(restored.provider.calls) == 8
    assert all(r.method == "GET" for r in restored.provider.calls)
    assert restored.provider.writes == 0
    with restored.harness.runtime.sessions() as db:
        row = db.get(WriteRecord, restored.reference.historical.record_id)
        assert row and row.payload == result.model_dump_json()
        assert row.digest == restored.reference.historical.plan_digest
        assert row.session_hash == restored.reference.historical.binding.session
        assert db.scalar(select(WriteFence)) is None
    snapshot = restored.snapshot()
    with pytest.raises(DepthRecoveryDenied):
        operator_recover(restored)
    assert restored.snapshot() == snapshot
    assert len(restored.provider.calls) == 8


@pytest.mark.parametrize(
    "mode", ["restored_default", "final_default", "final_restored"]
)
def test_modes_never_fall_back(restored: ServerCase, mode: str) -> None:
    if mode != "restored_default":
        param(restored.provider.data, 2, "depth")["expression"] = "30 mm"
    if mode != "final_restored":
        restored.reference = restored.reference.model_copy(
            update={
                "review": restored.reference.review.model_copy(
                    update={"original_baseline_restored": False}
                )
            }
        )
    before = restored.snapshot()
    if mode == "final_default":
        result = restored.recover()
        assert isinstance(result, DepthRecoveryResult)
        assert result.disposition == "independently_settled_current_state_matches"
        assert result.original_execution_outcome == "execution_uncertain"
    else:
        with pytest.raises(DepthRecoveryDenied):
            restored.recover()
        assert restored.snapshot() == before
    assert restored.provider.writes == 0


@pytest.mark.parametrize(
    "difference",
    [
        "depth",
        "quantity_value",
        "quantity_units",
        "query",
        "unknown_node",
        "name",
        "other_feature",
        "identity",
        "order",
        "suppressed",
        "missing_parameter",
        "duplicate_parameter",
        "unknown_parameter",
        "wrong_type",
        "missing_node",
        "invalid_node",
        "feature_states",
        "library",
        "serialization",
        "configuration",
        "body",
        "head",
        "history",
        "parent",
        "configured",
    ],
)
def test_every_mismatch_keeps_record_and_fence(
    restored: ServerCase, difference: str
) -> None:
    p = restored.provider
    target = p.data["features"][1]
    if difference == "depth":
        param(p.data, 2, "depth")["expression"] = "21 mm"
    elif difference in ("quantity_value", "quantity_units"):
        param(p.data, 2, "depth")[difference.removeprefix("quantity_")] = (
            999 if difference.endswith("value") else "mm"
        )
    elif difference == "query":
        param(p.data, 2, "entities")["queries"][0]["queryString"] = "private-unapproved"
    elif difference == "unknown_node":
        target["private-unknown"] = {"nodeId": "private-value"}
    elif difference == "name":
        target["name"] = "private-changed"
    elif difference == "other_feature":
        p.data["features"][0]["name"] = "private-changed"
    elif difference == "identity":
        target["featureId"] = "private-other"
    elif difference == "order":
        p.data["features"].reverse()
    elif difference == "suppressed":
        p.data["features"][-1]["suppressed"] = True
    elif difference == "missing_parameter":
        target["parameters"].pop()
    elif difference == "duplicate_parameter":
        target["parameters"].append(deepcopy(target["parameters"][0]))
    elif difference == "unknown_parameter":
        target["parameters"].append({"parameterId": "private-unknown", "value": False})
    elif difference == "wrong_type":
        param(p.data, 2, "depth")["btType"] = "private-type"
    elif difference == "missing_node":
        param(p.data, 2, "depth").pop("nodeId")
    elif difference == "invalid_node":
        param(p.data, 2, "depth")["nodeId"] = None
    elif difference == "feature_states":
        p.data["featureStates"] = {}
    elif difference == "library":
        p.data["libraryVersion"] += 1
    elif difference == "serialization":
        p.data["serializationVersion"] = "private-version"
    elif difference in ("parent", "configured"):
        target[
            "isSuppressedByParent"
            if difference == "parent"
            else "isSuppressedConfigured"
        ] = True
    original = p.handle

    def changed(request: httpx.Request) -> httpx.Response:
        response = original(request)
        data = response.json()
        historical = f"/m/{M0}/" in request.url.path
        if (
            difference == "history"
            and historical
            and request.url.path.endswith("features")
        ):
            data["features"][1]["name"] = "private-history"
        if not historical:
            if difference == "configuration" and request.url.path.endswith(
                "configuration"
            ):
                data["private-unknown"] = True
            if difference == "body" and request.url.path.endswith("bodydetails"):
                data = {}
            if (
                difference == "head"
                and request.url.path.endswith("currentmicroversion")
                and len(p.calls) == 8
            ):
                data["microversion"] = "f" * 24
        return httpx.Response(200, json=data)

    p.handle = changed  # type: ignore[method-assign]
    before = restored.snapshot()
    with pytest.raises(DepthRecoveryDenied) as error:
        restored.recover()
    assert "private-" not in str(error.value)
    assert restored.snapshot() == before
    assert len(p.calls) <= 8 and p.writes == 0


@pytest.mark.parametrize("difference", [None, "history"])
def test_legacy_raw_binding_before_restored_semantic_comparison(
    restored: ServerCase, difference: str | None
) -> None:
    p = restored.provider
    # Reacquire the invented original fixture locally, not through a real provider.
    historical = current_inventory()
    nodes(historical, "historical")
    with restored.harness.runtime.sessions.begin() as db:
        row = db.get(WriteRecord, restored.reference.historical.record_id)
        assert row
        saved = plan_storage.load(row)
        plan = saved.plan.model_copy(
            update={
                "policy_version": "modify-a1-1",
                "baseline": project_modify_raw_evidence(
                    REF, M0, historical, config(), bodies(explicit_flags=False)
                ).baseline,
            }
        )
        row.payload = saved.model_copy(update={"plan": plan}).model_dump_json()
        row.digest = fingerprint(plan.model_dump(mode="json"))
        restored.reference = depth_recovery._development_reference(
            db,
            restored.harness.runtime.settings,
            review(restored.harness).model_copy(
                update={"original_baseline_restored": True}
            ),
        )
    if difference:
        original = p.handle

        def changed(request: httpx.Request) -> httpx.Response:
            response = original(request)
            if f"/m/{M0}/" in request.url.path and request.url.path.endswith(
                "features"
            ):
                data = response.json()
                nodes(data, "changed-history")
                return httpx.Response(200, json=data)
            return response

        p.handle = changed  # type: ignore[method-assign]
        before = restored.snapshot()
        with pytest.raises(DepthRecoveryDenied):
            restored.recover()
        assert restored.snapshot() == before
    else:
        assert (
            operator_recover(restored).disposition
            == "independently_settled_original_baseline_restored"
        )
    assert p.writes == 0


@pytest.mark.parametrize(
    "change",
    [
        "env_production",
        "writes_on",
        "active_session",
        "wrong_session_user",
        "generation",
        "fence_missing",
        "conflict",
        "digest",
        "binding",
        "desired",
        "writers_drained",
        "upstream_settled",
    ],
)
def test_same_preflight_guards(restored: ServerCase, change: str) -> None:
    recovery_tests.test_preflight_denies_without_provider_calls_or_mutations(
        restored, change
    )


@pytest.mark.parametrize(
    "stage", ["before_update", "after_update", "after_delete", "audit", "commit"]
)
def test_same_atomic_rollback(
    restored: ServerCase, monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    recovery_tests.test_atomic_failure_restores_original_fence_and_record(
        restored, monkeypatch, stage
    )


def test_review_mode_is_bound_to_registered_evidence(
    restored: ServerCase, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = depth_release.release_depth_record

    def release(db: Any, settings: Any, run: Any, evidence: Any) -> Any:
        run.reference = run.reference.model_copy(
            update={
                "review": run.reference.review.model_copy(
                    update={"original_baseline_restored": False}
                )
            }
        )
        return original(db, settings, run, evidence)

    monkeypatch.setattr(depth_recovery, "release_depth_record", release)
    before = restored.snapshot()
    with pytest.raises(DepthRecoveryDenied, match="evidence_reference_mismatch"):
        restored.recover()
    assert restored.snapshot() == before


def test_console_explicit_restoration_choice_and_pinned_review(
    restored: ServerCase, monkeypatch: pytest.MonkeyPatch
) -> None:
    answers = iter(
        [
            "RESTORED BASELINE SETTLED DRAINED AUTHORIZE",
            restored.reference.review.stack,
            "",
        ]
    )
    output: list[str] = []
    original = depth_recovery.recover_development_depth_incident

    def recover(runtime: Any, reviewed: Any, **kw: Any) -> Any:
        assert reviewed.original_baseline_restored
        assert kw["incident"].reference.review.original_baseline_restored
        return original(
            runtime,
            reviewed,
            **kw,
            transport=httpx.MockTransport(restored.provider.handle),
        )

    monkeypatch.setattr(console, "recover_development_depth_incident", recover)
    assert (
        console.operator_attempt(
            restored.harness.runtime,
            ask=lambda _: next(answers),
            private=lambda _: "Synthetic independently reviewed upstream settlement",
            report=output.append,
        )
        == 0
    )
    assert output[-1] == "disposition=independently_settled_original_baseline_restored"


def test_closure_confirmation_uses_one_atomic_timestamp(
    restored: ServerCase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from forge_api.db.models import AuditEvent, now

    # Deterministically model a clock tick between tombstone construction and
    # audit insertion, without sleeps or weakening the exact confirmation check.
    closure_time = now() - 1
    monkeypatch.setattr(depth_release, "now", lambda: closure_time)
    result = operator_recover(restored)
    assert result.recovered_at == closure_time
    with restored.harness.runtime.sessions() as db:
        event = db.scalar(
            select(AuditEvent).where(
                AuditEvent.kind == "write_depth_development_recovery"
            )
        )
        assert event and event.created_at == result.recovered_at
