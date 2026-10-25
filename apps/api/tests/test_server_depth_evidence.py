"""Read-only transport and unforgeable-by-serialization local handoff tests."""

from time import monotonic
from typing import Any

import httpx2 as httpx
import pytest
from pydantic import SecretStr, ValidationError
from server_depth_support import ServerCase as DepthCase
from test_server_depth_recovery import case as case

from forge_api.cad_edits import depth_contracts, depth_release, plan_storage
from forge_api.cad_edits.depth_contracts import (
    DepthRecoveryDenied,
    VerifiedDepthRecoveryEvidence,
)
from forge_api.db.models import WriteRecord
from forge_api.integrations.onshape.client import MAX_BYTES
from forge_api.integrations.onshape.depth_reader import (
    DepthEvidenceReader,
    _PinnedGetTransport,
)


def saved(c: DepthCase) -> Any:
    with c.harness.runtime.sessions() as db:
        row = db.get(WriteRecord, c.reference.historical.record_id)
        assert row
        return plan_storage.load(row)


def reader(c: DepthCase, handler: Any = None) -> DepthEvidenceReader:
    return DepthEvidenceReader(
        c.reference.review.stack,
        c.reference.approval.context,
        SecretStr("synthetic-read"),
        saved(c).plan.baseline.microversion,
        transport=httpx.MockTransport(handler or c.provider.handle),
    )


def test_fixed_eight_gets_complete_pinned_projection_and_closed_reader(
    case: DepthCase,
) -> None:
    r = reader(case)
    evidence = r.capture(case.reference, saved(case))
    marker = evidence.head_before
    calls = case.provider.calls
    assert len(calls) == 8
    assert [c.method for c in calls] == ["GET"] * 8
    assert [c.url.path.rsplit("/", 1)[-1] for c in calls] == [
        "features",
        "configuration",
        "bodydetails",
        "currentmicroversion",
        "features",
        "configuration",
        "bodydetails",
        "currentmicroversion",
    ]
    assert all(f"/m/{marker}/" in str(c.url) for c in calls[4:7])
    assert dict(calls[4].url.params) == {
        "includeGeometryIds": "false",
        "noSketchGeometry": "false",
        "rollbackBarIndex": "-1",
    }
    assert dict(calls[6].url.params) == {"includeGeometricData": "false"}
    assert r._credential is None and r._guard.closed
    assert evidence.baseline.suppressed is False
    historical = saved(case).plan.baseline.microversion
    assert all(f"/m/{historical}/" in str(c.url) for c in calls[:3])
    assert "synthetic-read" not in evidence.model_dump_json()
    with pytest.raises(DepthRecoveryDenied):
        r.capture(case.reference, saved(case))
    with pytest.raises(ValidationError):
        VerifiedDepthRecoveryEvidence.model_validate(
            {**evidence.model_dump(), "raw_provider_payload": {}}
        )
    with pytest.raises(ValidationError):
        evidence.user = "changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    "method", ["POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE", "CONNECT"]
)
def test_transport_blocks_every_non_get_without_io(
    case: DepthCase, method: str
) -> None:
    c = case.reference.approval.context
    guard = _PinnedGetTransport(
        "https://cad.onshape.com",
        c,
        saved(case).plan.baseline.microversion,
        httpx.MockTransport(case.provider.handle),
    )
    with pytest.raises(DepthRecoveryDenied):
        guard.handle_request(httpx.Request(method, guard.urls[0]))
    assert not case.provider.calls


@pytest.mark.parametrize(
    "bad",
    ["host", "scheme", "port", "path", "query", "body", "credentials", "fragment"],
)
def test_transport_rejects_any_unreviewed_request(case: DepthCase, bad: str) -> None:
    guard = _PinnedGetTransport(
        "https://cad.onshape.com",
        case.reference.approval.context,
        saved(case).plan.baseline.microversion,
        httpx.MockTransport(case.provider.handle),
    )
    url, content = guard.urls[0], b""
    if bad == "host":
        url = url.replace("cad.onshape.com", "evil.invalid")
    elif bad == "scheme":
        url = url.replace("https:", "http:")
    elif bad == "port":
        url = url.replace("cad.onshape.com", "cad.onshape.com:8443")
    elif bad == "path":
        url = url.replace("/features?", "/features/updates?")
    elif bad == "query":
        url += "?extra=true"
    elif bad == "credentials":
        url = url.replace("https://", "https://user:password@")
    elif bad == "fragment":
        url += "#extra"
    else:
        content = b"{}"
    with pytest.raises(DepthRecoveryDenied):
        guard.handle_request(httpx.Request("GET", url, content=content))
    assert case.provider.calls == []


@pytest.mark.parametrize(
    "bad",
    [
        "redirect",
        "unauthorized",
        "forbidden",
        "rate",
        "server",
        "malformed",
        "duplicate",
        "mime",
        "encoding",
        "oversize_declared",
        "oversize_actual",
        "timeout",
        "head_mismatch",
        "head_shape",
        "head_id",
    ],
)
def test_capture_failure_closes_and_never_retries(case: DepthCase, bad: str) -> None:
    calls: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if bad in ("head_shape", "head_id") and len(calls) < 4:
            return case.provider.handle(request)
        if bad == "timeout":
            raise httpx.ReadTimeout("synthetic")
        if bad == "head_mismatch" and len(calls) == 8:
            return httpx.Response(200, json={"microversion": "f" * 24})
        if bad == "head_mismatch":
            return case.provider.handle(request)
        if bad in ("redirect", "unauthorized", "forbidden", "rate", "server"):
            return httpx.Response(
                {
                    "redirect": 302,
                    "unauthorized": 401,
                    "forbidden": 403,
                    "rate": 429,
                    "server": 503,
                }[bad],
                headers={"location": "https://evil.invalid"},
                json={},
            )
        if bad == "malformed":
            return httpx.Response(
                200, content=b"not-json", headers={"content-type": "application/json"}
            )
        if bad == "duplicate":
            return httpx.Response(
                200,
                content=b'{"microversion":1,"microversion":2}',
                headers={"content-type": "application/json"},
            )
        if bad == "head_shape":
            return httpx.Response(200, json=[])
        if bad == "head_id":
            return httpx.Response(200, json={"microversion": "wrong"})
        if bad == "mime":
            return httpx.Response(
                200, content=b"{}", headers={"content-type": "text/plain"}
            )
        if bad == "encoding":
            return httpx.Response(
                200,
                content=b"{}",
                headers={
                    "content-type": "application/json",
                    "content-encoding": "unsupported",
                },
            )
        if bad == "oversize_declared":
            return httpx.Response(
                200,
                content=b"{}",
                headers={
                    "content-type": "application/json",
                    "content-length": str(MAX_BYTES + 1),
                },
            )
        response = httpx.Response(
            200,
            content=b" " * (MAX_BYTES + 1),
            headers={"content-type": "application/json"},
        )
        del response.headers["content-length"]
        return response

    r = reader(case, respond)
    before = case.snapshot()
    with pytest.raises(DepthRecoveryDenied):
        r.capture(case.reference, saved(case))
    assert len(calls) == (
        8 if bad == "head_mismatch" else 4 if bad in ("head_shape", "head_id") else 1
    )
    assert r._credential is None and r._guard.closed
    assert case.snapshot() == before


@pytest.mark.parametrize(
    "change",
    [
        "suppression",
        "identity",
        "position",
        "definition",
        "serialization",
        "library",
        "body",
        "config",
        "states",
        "parent",
        "configured",
        "ambiguous",
    ],
)
def test_deterministic_projection_disagreement_preserves_fence(
    case: DepthCase, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    p = case.provider
    if change == "suppression":
        p.data["features"][-1]["suppressed"] = True
    elif change == "identity":
        p.data["features"][-1]["featureId"] = "synthetic-replacement"
    elif change == "position":
        p.data["features"].insert(0, p.data["features"][0].copy())
    elif change == "definition":
        p.data["features"][0]["name"] = "Unrelated change"
    elif change == "serialization":
        p.data["serializationVersion"] = "different"
    elif change == "library":
        p.data["libraryVersion"] += 1
    elif change == "states":
        p.data["featureStates"] = {"unknown": {}}
    elif change == "parent":
        p.data["features"][-1]["parentSuppressed"] = True
    elif change == "configured":
        p.data["features"][-1]["suppressionConfigured"] = True
    elif change == "ambiguous":
        p.data["features"][-1]["featureType"] = "extrude"
    else:
        import test_modify_plan
        from test_safe_edit import bodies, config

        if change == "body":
            monkeypatch.setattr(
                test_modify_plan,
                "bodies",
                lambda marker, **kw: {**bodies(marker, **kw), "errorEnum": "ERROR"},
            )
        else:
            monkeypatch.setattr(
                test_modify_plan,
                "config",
                lambda marker: {**config(marker), "currentConfiguration": ["changed"]},
            )
    before = case.snapshot()
    with pytest.raises(DepthRecoveryDenied):
        case.recover()
    assert case.snapshot() == before and p.writes == 0


@pytest.mark.parametrize(
    "change",
    [
        "copy",
        "deserialize",
        "record",
        "context",
        "user",
        "generation",
        "payload",
        "reference",
        "head",
        "stale",
        "future",
        "used",
        "cross_run",
        "unregistered",
    ],
)
def test_only_exact_registered_fresh_evidence_object_is_accepted(
    case: DepthCase, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    h, ref = case.harness, case.reference
    before = case.snapshot()
    with pytest.raises(DepthRecoveryDenied), h.runtime.sessions.begin() as db:
        run, _ = depth_release.lock_depth_record(
            db, h.runtime.settings, ref, started=monotonic()
        )
        evidence = reader(case).capture(ref, saved(case))
        if change != "unregistered":
            run.register(evidence)
        if change == "copy":
            evidence = evidence.model_copy()
        elif change == "deserialize":
            evidence = VerifiedDepthRecoveryEvidence.model_validate_json(
                evidence.model_dump_json()
            )
        elif change in (
            "record",
            "context",
            "user",
            "generation",
            "payload",
            "reference",
            "head",
        ):
            field = {
                "record": "record_id",
                "context": "context",
                "user": "user",
                "generation": "current_generation",
                "payload": "payload_fingerprint",
                "reference": "reference_fingerprint",
                "head": "head_after",
            }[change]
            value = (
                ref.approval.context.model_copy(update={"elementId": "f" * 24})
                if change == "context"
                else "f" * 43
                if change == "record"
                else "f" * 64
                if change in ("payload", "reference")
                else "f" * 24
                if change == "head"
                else "synthetic-other"
            )
            altered = evidence.model_copy(update={field: value})
            # Even explicitly trying to register substituted scope is rejected.
            other_run, _ = depth_release.lock_depth_record(
                db, h.runtime.settings, ref, started=run.started
            )
            other_run.register(altered)
            evidence = altered
        elif change in ("stale", "future"):
            monkeypatch.setattr(
                depth_contracts,
                "monotonic",
                lambda: evidence.finished_monotonic + (6 if change == "stale" else -1),
            )
        elif change == "used":
            run.consume(db, evidence)
        elif change == "cross_run":
            run, _ = depth_release.lock_depth_record(
                db, h.runtime.settings, ref, started=monotonic()
            )
        depth_release.release_depth_record(db, h.runtime.settings, run, evidence)
    assert case.snapshot() == before


def test_cross_transaction_handoff_rejected(case: DepthCase) -> None:
    h, ref = case.harness, case.reference
    with h.runtime.sessions.begin() as db:
        run, _ = depth_release.lock_depth_record(
            db, h.runtime.settings, ref, started=monotonic()
        )
        evidence = reader(case).capture(ref, saved(case))
        run.register(evidence)
    before = case.snapshot()
    with pytest.raises(DepthRecoveryDenied), h.runtime.sessions.begin() as other:
        depth_release.release_depth_record(other, h.runtime.settings, run, evidence)
    assert case.snapshot() == before


def test_total_capture_deadline_is_enforced_without_retry(
    case: DepthCase, monkeypatch: pytest.MonkeyPatch
) -> None:
    from forge_api.integrations.onshape import depth_reader

    clock = [100.0]
    monkeypatch.setattr(depth_reader, "monotonic", lambda: clock[0])

    def slow(request: httpx.Request) -> httpx.Response:
        response = case.provider.handle(request)
        clock[0] += 31
        return response

    r = reader(case, slow)
    with pytest.raises(DepthRecoveryDenied):
        r.capture(case.reference, saved(case))
    assert len(case.provider.calls) == 1 and r._credential is None


def test_exhausted_run_budget_never_starts_capture(case: DepthCase) -> None:
    r = reader(case)
    with pytest.raises(DepthRecoveryDenied):
        r.capture(case.reference, saved(case), deadline=monotonic() - 1)
    assert not case.provider.calls and r._credential is None and r._guard.closed


@pytest.mark.parametrize(
    "change",
    [
        "historical_source",
        "historical_definition",
        "current_depth",
        "current_metadata",
        "settlement",
        "target",
        "quantity",
    ],
)
def test_depth_specific_evidence_is_not_substitutable(
    case: DepthCase, change: str
) -> None:
    from copy import deepcopy

    ref = case.reference
    original = case.provider.handle
    historical = saved(case).plan.baseline.microversion
    if change == "settlement":
        case.reference = ref.model_copy(
            update={"settlement": ref.settlement.model_copy(update={"settled": False})}
        )
    elif change in ("target", "quantity"):
        field, value = (
            ("target_feature_id", "other-feature")
            if change == "target"
            else ("quantity", "31 mm")
        )
        case.reference = ref.model_copy(
            update={"approval": ref.approval.model_copy(update={field: value})}
        )

    def handle(request: httpx.Request) -> httpx.Response:
        response = original(request)
        is_historical = f"/m/{historical}/" in request.url.path
        if request.url.path.endswith("/features"):
            data = deepcopy(response.json())
            if change == "historical_source" and is_historical:
                data["sourceMicroversion"] = "f" * 24
            elif change == "historical_definition" and is_historical:
                data["features"][1]["name"] = "Other"
            elif change == "current_depth" and not is_historical:
                data["features"][1]["parameters"][-1]["expression"] = "31 mm"
            elif change == "current_metadata" and not is_historical:
                data["features"][1]["unexpected"] = True
            return httpx.Response(200, json=data)
        return response

    case.provider.handle = handle  # type: ignore[method-assign]
    before = case.snapshot()
    with pytest.raises(DepthRecoveryDenied):
        case.recover()
    assert case.snapshot() == before and case.provider.writes == 0


def test_absent_provider_ack_is_not_invented(case: DepthCase) -> None:
    from sqlalchemy import delete

    from forge_api.db.models import AuditEvent

    with case.harness.runtime.sessions.begin() as db:
        db.execute(
            delete(AuditEvent).where(AuditEvent.kind == "write_provider_acknowledged")
        )
    result = case.recover()
    assert result.original_execution_outcome == "execution_uncertain"  # type: ignore[attr-defined]
    with case.harness.runtime.sessions() as db:
        assert not list(
            db.query(AuditEvent).filter(
                AuditEvent.kind == "write_provider_acknowledged"
            )
        )
