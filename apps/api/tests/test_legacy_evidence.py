"""Legacy evidence uses the unchanged deterministic projection and GET guard."""

from time import monotonic
from typing import Any

import httpx2 as httpx
import pytest
from legacy_support import LegacyCase
from sqlalchemy.orm import SessionTransaction
from test_legacy_recovery import case as case

from forge_api.cad_edits import legacy_contracts, legacy_recovery, legacy_release
from forge_api.cad_edits.legacy_contracts import (
    LegacyEvidence,
    LegacyRecoveryDenied,
    _LegacyRun,
)
from forge_api.cad_edits.legacy_enrollment import validate_locked
from forge_api.integrations.onshape.legacy_reader import LegacyEvidenceReader


def reader(case: LegacyCase) -> LegacyEvidenceReader:
    return LegacyEvidenceReader(
        case.enrollment.stack,
        case.enrollment.binding.context,
        case.harness.runtime.tokens.cached_read_credential(
            case.enrollment.binding.user,
            case.enrollment.current_generation,
            "OAuth2Read",
            capture_seconds=30,
        ),
        transport=httpx.MockTransport(case.provider.handle),
    )


def test_five_fixed_gets_distinct_closed_evidence_and_reader_closed(
    case: LegacyCase,
) -> None:
    owned = reader(case)
    evidence = owned.capture_legacy(
        case.enrollment, case.review, deadline=monotonic() + 30
    )
    assert type(evidence) is LegacyEvidence
    assert evidence.head_before == evidence.head_after == case.provider.marker
    assert evidence.baseline.suppressed is False
    assert owned._credential is None and owned._guard.closed
    assert len(case.provider.calls) == 5
    for request in case.provider.calls:
        assert request.method == "GET" and request.content == b""
        assert case.enrollment.binding.context.documentId in request.url.path
    before = len(case.provider.calls)
    with pytest.raises(LegacyRecoveryDenied):
        owned.capture_legacy(case.enrollment, case.review, deadline=monotonic() + 30)
    assert len(case.provider.calls) == before


@pytest.mark.parametrize(
    "change",
    [
        "suppression",
        "identity",
        "position",
        "definition",
        "serialization",
        "library",
        "config",
        "body",
        "states",
        "parent",
        "configured",
        "ambiguous",
        "head",
    ],
)
def test_fresh_evidence_disagreement_rolls_back(
    case: LegacyCase, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    p = case.provider
    if change == "suppression":
        p.data["features"][-1]["suppressed"] = True
        p.data["featureStates"][p.data["features"][-1]["featureId"]]["inactive"] = True
    elif change == "identity":
        p.data["features"][-1]["featureId"] = "synthetic-other"
    elif change == "position":
        p.data["features"].insert(0, p.data["features"][0].copy())
    elif change == "definition":
        p.data["features"][0]["name"] = "Unrelated change"
    elif change == "serialization":
        p.data["serializationVersion"] = "other"
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
        handler = p.handle

        def invalid(request: Any) -> Any:
            response = handler(request)
            data = response.json()
            if change == "config" and request.url.path.endswith("/configuration"):
                data["currentConfiguration"] = ["changed"]
            elif change == "body" and request.url.path.endswith("/bodydetails"):
                data["errorEnum"] = "ERROR"
            elif (
                change == "head"
                and request.url.path.endswith("/currentmicroversion")
                and len(p.calls) == 5
            ):
                data["microversion"] = "f" * 24
            return httpx.Response(200, json=data)

        monkeypatch.setattr(p, "handle", invalid)
    before = case.snapshot()
    with pytest.raises(LegacyRecoveryDenied):
        case.recover()
    assert case.snapshot() == before and p.writes == 0


@pytest.mark.parametrize(
    "change",
    [
        "copy",
        "deserialize",
        "cross_run",
        "unregistered",
        "used",
        "stale",
        "future",
        "enrollment",
        "review",
        "head",
        "context",
        "baseline_context",
        "capture_age",
    ],
)
def test_only_registered_same_run_single_use_evidence_releases(
    case: LegacyCase, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    h = case.harness
    before = case.snapshot()
    with pytest.raises(LegacyRecoveryDenied), h.runtime.sessions.begin() as db:
        row, s, _ = validate_locked(
            db, h.runtime.settings, case.enrollment, case.review
        )
        transaction = db.get_transaction()
        assert transaction and row.payload
        run = _LegacyRun(
            db, transaction, case.enrollment, case.review, s, row.payload, monotonic()
        )
        evidence = reader(case).capture_legacy(
            case.enrollment, case.review, deadline=monotonic() + 30
        )
        if change in (
            "enrollment",
            "review",
            "head",
            "context",
            "baseline_context",
            "capture_age",
        ):
            fields: dict[str, Any] = {}
            if change in ("enrollment", "review"):
                fields[change + "_fingerprint"] = "0" * 64
            elif change == "head":
                fields["head_after"] = "f" * 24
            elif change == "context":
                fields["context"] = evidence.context.model_copy(
                    update={"elementId": "f" * 24}
                )
            elif change == "baseline_context":
                fields["baseline"] = evidence.baseline.model_copy(
                    update={
                        "context": evidence.baseline.context.model_copy(
                            update={"elementId": "f" * 24}
                        )
                    }
                )
            else:
                fields["finished_monotonic"] = evidence.started_monotonic + 31
            run.register(evidence.model_copy(update=fields))
        if change != "unregistered":
            run.register(evidence)
        if change == "copy":
            evidence = evidence.model_copy()
        elif change == "deserialize":
            evidence = LegacyEvidence.model_validate_json(evidence.model_dump_json())
        elif change == "cross_run":
            run = _LegacyRun(
                db,
                transaction,
                case.enrollment,
                case.review,
                s,
                row.payload,
                monotonic(),
            )
        elif change == "used":
            run.consume(db, evidence)
        elif change in ("stale", "future"):
            monkeypatch.setattr(
                legacy_contracts,
                "monotonic",
                lambda: evidence.finished_monotonic + (6 if change == "stale" else -1),
            )
        legacy_release.release_legacy_record(db, h.runtime.settings, run, evidence)
    assert case.snapshot() == before


def test_evidence_cannot_cross_transactions(case: LegacyCase) -> None:
    h = case.harness
    with h.runtime.sessions.begin() as db:
        row, s, _ = validate_locked(
            db, h.runtime.settings, case.enrollment, case.review
        )
        transaction = db.get_transaction()
        assert transaction and row.payload
        run = _LegacyRun(
            db, transaction, case.enrollment, case.review, s, row.payload, monotonic()
        )
        evidence = reader(case).capture_legacy(
            case.enrollment, case.review, deadline=monotonic() + 30
        )
        run.register(evidence)
    before = case.snapshot()
    with pytest.raises(LegacyRecoveryDenied), h.runtime.sessions.begin() as other:
        legacy_release.release_legacy_record(other, h.runtime.settings, run, evidence)
    assert case.snapshot() == before


def test_exhausted_capture_budget_never_reads(case: LegacyCase) -> None:
    owned = reader(case)
    with pytest.raises(LegacyRecoveryDenied):
        owned.capture_legacy(case.enrollment, case.review, deadline=monotonic() - 1)
    assert case.provider.calls == [] and owned._credential is None


def test_reader_is_closed_before_release(
    case: LegacyCase, monkeypatch: pytest.MonkeyPatch
) -> None:
    capture = LegacyEvidenceReader.capture_legacy
    release = legacy_release.release_legacy_record
    readers: list[LegacyEvidenceReader] = []

    def captured(self: Any, *args: Any, **kwargs: Any) -> Any:
        readers.append(self)
        return capture(self, *args, **kwargs)

    def released(*args: Any) -> Any:
        assert len(readers) == 1 and readers[0]._credential is None
        assert readers[0]._guard.closed
        return release(*args)

    monkeypatch.setattr(LegacyEvidenceReader, "capture_legacy", captured)
    monkeypatch.setattr(legacy_recovery, "release_legacy_record", released)
    case.recover()


def test_lost_commit_reply_does_not_retry(
    case: LegacyCase, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = SessionTransaction.__exit__

    def lost(self: Any, *args: Any, **kwargs: Any) -> Any:
        result = original(self, *args, **kwargs)
        if len(case.provider.calls) == 5 and not self.nested:
            raise RuntimeError("synthetic lost commit reply")
        return result

    with monkeypatch.context() as patch:
        patch.setattr(SessionTransaction, "__exit__", lost)
        with pytest.raises(RuntimeError, match="lost commit reply"):
            case.recover()
    committed = case.snapshot()
    assert committed[0][0] == "operator_recovered"
    with pytest.raises(LegacyRecoveryDenied):
        case.recover()
    assert case.snapshot() == committed and len(case.provider.calls) == 5


@pytest.mark.parametrize(
    "failure",
    ["redirect", "unavailable", "malformed", "oversized", "encoding", "timeout"],
)
def test_reader_failure_has_no_retry_or_release(
    case: LegacyCase, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    def fail(request: httpx.Request) -> httpx.Response:
        case.provider.calls.append(request)
        if failure == "timeout":
            raise httpx.ReadTimeout("synthetic private error")
        if failure == "redirect":
            return httpx.Response(302, headers={"location": "https://other.example"})
        if failure == "unavailable":
            return httpx.Response(503, json={})
        if failure == "malformed":
            return httpx.Response(
                200, content=b"{", headers={"content-type": "application/json"}
            )
        if failure == "oversized":
            return httpx.Response(200, json={}, headers={"content-length": "2097153"})
        return httpx.Response(200, json={}, headers={"content-encoding": "gzip"})

    monkeypatch.setattr(case.provider, "handle", fail)
    before = case.snapshot()
    with pytest.raises(LegacyRecoveryDenied):
        case.recover()
    assert case.snapshot() == before and len(case.provider.calls) == 1


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_inherited_transport_blocks_mutations_before_io(
    case: LegacyCase, method: str
) -> None:
    from forge_api.cad_edits.retained_contracts import RetainedRecoveryDenied

    owned = reader(case)
    try:
        with pytest.raises(RetainedRecoveryDenied):
            owned._guard.handle_request(httpx.Request(method, owned._guard.urls[0]))
        assert case.provider.calls == []
    finally:
        owned.close()
