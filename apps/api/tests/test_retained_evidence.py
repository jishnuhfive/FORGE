"""Read-only transport and unforgeable-by-serialization local handoff tests."""

from time import monotonic
from typing import Any

import httpx2 as httpx
import pytest
from pydantic import SecretStr, ValidationError
from retained_support import RetainedCase
from test_retained_recovery import case as case

from forge_api.cad_edits import retained_contracts, retained_release
from forge_api.cad_edits.retained_contracts import (
    RetainedRecoveryDenied,
    VerifiedRetainedRecoveryEvidence,
)
from forge_api.integrations.onshape.client import MAX_BYTES
from forge_api.integrations.onshape.retained_reader import (
    RetainedEvidenceReader,
    _PinnedGetTransport,
)


def reader(c: RetainedCase, handler: Any = None) -> RetainedEvidenceReader:
    return RetainedEvidenceReader(
        c.reference.review.stack,
        c.reference.independent.context,
        SecretStr("synthetic-read"),
        transport=httpx.MockTransport(handler or c.provider.handle),
    )


def test_fixed_five_gets_complete_pinned_projection_and_closed_reader(
    case: RetainedCase,
) -> None:
    r = reader(case)
    evidence = r.capture(case.reference)
    marker = evidence.head_before
    calls = case.provider.calls
    assert len(calls) == 5
    assert [c.method for c in calls] == ["GET"] * 5
    assert [c.url.path.rsplit("/", 1)[-1] for c in calls] == [
        "currentmicroversion",
        "features",
        "configuration",
        "bodydetails",
        "currentmicroversion",
    ]
    assert all(f"/m/{marker}/" in str(c.url) for c in calls[1:4])
    assert dict(calls[1].url.params) == {
        "includeGeometryIds": "false",
        "noSketchGeometry": "false",
        "rollbackBarIndex": "-1",
    }
    assert dict(calls[3].url.params) == {"includeGeometricData": "false"}
    assert r._credential is None and r._guard.closed
    assert evidence.baseline.suppressed is True
    assert "synthetic-read" not in evidence.model_dump_json()
    with pytest.raises(RetainedRecoveryDenied):
        r.capture(case.reference)
    with pytest.raises(ValidationError):
        VerifiedRetainedRecoveryEvidence.model_validate(
            {**evidence.model_dump(), "raw_provider_payload": {}}
        )
    with pytest.raises(ValidationError):
        evidence.user = "changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    "method", ["POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE", "CONNECT"]
)
def test_transport_blocks_every_non_get_without_io(
    case: RetainedCase, method: str
) -> None:
    c = case.reference.independent.context
    guard = _PinnedGetTransport(
        "https://cad.onshape.com", c, httpx.MockTransport(case.provider.handle)
    )
    with pytest.raises(RetainedRecoveryDenied):
        guard.handle_request(httpx.Request(method, guard.urls[0]))
    assert not case.provider.calls


@pytest.mark.parametrize(
    "bad",
    ["host", "scheme", "port", "path", "query", "body", "credentials", "fragment"],
)
def test_transport_rejects_any_unreviewed_request(case: RetainedCase, bad: str) -> None:
    guard = _PinnedGetTransport(
        "https://cad.onshape.com",
        case.reference.independent.context,
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
        url = url.replace("currentmicroversion", "features/updates")
    elif bad == "query":
        url += "?extra=true"
    elif bad == "credentials":
        url = url.replace("https://", "https://user:password@")
    elif bad == "fragment":
        url += "#extra"
    else:
        content = b"{}"
    with pytest.raises(RetainedRecoveryDenied):
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
def test_capture_failure_closes_and_never_retries(case: RetainedCase, bad: str) -> None:
    calls: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if bad == "timeout":
            raise httpx.ReadTimeout("synthetic")
        if bad == "head_mismatch" and len(calls) == 5:
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
    with pytest.raises(RetainedRecoveryDenied):
        r.capture(case.reference)
    assert len(calls) == (5 if bad == "head_mismatch" else 1)
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
    case: RetainedCase, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    p = case.provider
    if change == "suppression":
        p.data["features"][-1]["suppressed"] = False
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
    with pytest.raises(RetainedRecoveryDenied):
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
    case: RetainedCase, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    h, ref = case.harness, case.reference
    before = case.snapshot()
    with pytest.raises(RetainedRecoveryDenied), h.runtime.sessions.begin() as db:
        run, _ = retained_release.lock_retained_record(
            db, h.runtime.settings, ref, started=monotonic()
        )
        evidence = reader(case).capture(ref)
        if change != "unregistered":
            run.register(evidence)
        if change == "copy":
            evidence = evidence.model_copy()
        elif change == "deserialize":
            evidence = VerifiedRetainedRecoveryEvidence.model_validate_json(
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
                ref.independent.context.model_copy(update={"elementId": "f" * 24})
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
            other_run, _ = retained_release.lock_retained_record(
                db, h.runtime.settings, ref, started=run.started
            )
            other_run.register(altered)
            evidence = altered
        elif change in ("stale", "future"):
            monkeypatch.setattr(
                retained_contracts,
                "monotonic",
                lambda: evidence.finished_monotonic + (6 if change == "stale" else -1),
            )
        elif change == "used":
            run.consume(db, evidence)
        elif change == "cross_run":
            run, _ = retained_release.lock_retained_record(
                db, h.runtime.settings, ref, started=monotonic()
            )
        retained_release.release_retained_record(db, h.runtime.settings, run, evidence)
    assert case.snapshot() == before


def test_cross_transaction_handoff_rejected(case: RetainedCase) -> None:
    h, ref = case.harness, case.reference
    with h.runtime.sessions.begin() as db:
        run, _ = retained_release.lock_retained_record(
            db, h.runtime.settings, ref, started=monotonic()
        )
        evidence = reader(case).capture(ref)
        run.register(evidence)
    before = case.snapshot()
    with pytest.raises(RetainedRecoveryDenied), h.runtime.sessions.begin() as other:
        retained_release.release_retained_record(
            other, h.runtime.settings, run, evidence
        )
    assert case.snapshot() == before


def test_total_capture_deadline_is_enforced_without_retry(
    case: RetainedCase, monkeypatch: pytest.MonkeyPatch
) -> None:
    from forge_api.integrations.onshape import retained_reader

    clock = [100.0]
    monkeypatch.setattr(retained_reader, "monotonic", lambda: clock[0])

    def slow(request: httpx.Request) -> httpx.Response:
        response = case.provider.handle(request)
        clock[0] += 31
        return response

    r = reader(case, slow)
    with pytest.raises(RetainedRecoveryDenied):
        r.capture(case.reference)
    assert len(case.provider.calls) == 1 and r._credential is None


def test_exhausted_run_budget_never_starts_capture(case: RetainedCase) -> None:
    r = reader(case)
    with pytest.raises(RetainedRecoveryDenied):
        r.capture(case.reference, deadline=monotonic() - 1)
    assert not case.provider.calls and r._credential is None and r._guard.closed
