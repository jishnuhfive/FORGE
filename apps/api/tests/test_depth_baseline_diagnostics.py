"""One-attempt baseline/current diagnostics using synthetic providers only."""

from enum import Enum
from typing import Any

import httpx2 as httpx
import pytest
from server_depth_support import ServerCase
from test_depth_session_preparation import session_state
from test_server_depth_evidence import reader, saved
from test_server_depth_recovery import case as case

from forge_api.cad_edits import depth_recovery
from forge_api.cad_edits.depth_baseline_diagnostics import FIELDS, baseline_differences
from forge_api.cad_edits.domain import Baseline
from forge_api.db.models import OnshapeAuthorization
from forge_api.integrations.onshape import depth_reader
from forge_api.integrations.onshape.depth_reader import DepthBaselineDiagnostic

PRIVATE = "PRIVATE-DO-NOT-EMIT"
BASE = "depth_recovery:diagnostic:historical_baseline_mismatch:"
DIGESTS = "definitions_digest_mismatch,full_evidence_digest_mismatch"


def alternate(field: str, value: Any) -> Any:
    if field == "context":
        return value.model_copy(update={"elementId": "f" * 24})
    if field == "microversion":
        return "f" * 24
    if field in ("definitions", "fingerprint"):
        return "f" * 64
    if isinstance(value, Enum):
        return next(item for item in type(value) if item != value)
    if isinstance(value, tuple):
        return tuple(alternate(field, item) for item in value)
    if type(value) is bool:
        return not value
    if isinstance(value, int):
        return value + 1
    return PRIVATE


@pytest.mark.parametrize("field,category", FIELDS)
def test_each_baseline_component_is_independent_and_closed(
    case: ServerCase,
    field: str,
    category: str,
) -> None:
    original = saved(case).plan.baseline
    changed = original.model_copy(
        update={field: alternate(field, getattr(original, field))}
    )
    assert changed != original
    assert baseline_differences(original, changed) == (category,)
    assert baseline_differences(changed, original) == (category,)
    assert PRIVATE not in repr(baseline_differences(original, changed))


def test_exhaustive_fields_deterministic_set_and_equal_state(case: ServerCase) -> None:
    assert {field for field, _ in FIELDS} == set(Baseline.model_fields)
    assert len({code for _, code in FIELDS}) == len(FIELDS)
    original = saved(case).plan.baseline
    updates = {
        field: alternate(field, getattr(original, field))
        for field, _ in reversed(FIELDS)
    }
    assert baseline_differences(original, original) == ()
    assert baseline_differences(original, original.model_copy(update=updates)) == tuple(
        c for _, c in FIELDS
    )


def preserved(case: ServerCase) -> tuple[object, ...]:
    runtime = case.harness.runtime
    with runtime.sessions() as db:
        grant = db.get(OnshapeAuthorization, case.reference.approval.user)
        assert grant
        grant_state = (grant.status, grant.generation, grant.encrypted_refresh_token)
    credential = runtime.tokens.cached_read_credential(
        case.reference.approval.user,
        case.reference.review.current_generation,
        "OAuth2Read",
        capture_seconds=30,
    )
    return case.snapshot(), session_state(case), grant_state, credential


def no_release(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("Diagnostic mismatch must never create evidence or release")

    monkeypatch.setattr(depth_reader, "VerifiedDepthRecoveryEvidence", forbidden)
    monkeypatch.setattr(depth_recovery, "release_depth_record", forbidden)


@pytest.mark.parametrize(
    "mode", ["inventory", "all_comparisons", "typed_only", "empty_classifier"]
)
def test_combined_diagnostics_always_deny_and_preserve_authority(
    case: ServerCase,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    mode: str,
) -> None:
    original = case.provider.handle
    calls = 0

    def respond(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        data = original(request).json()
        if calls == 1 and mode != "typed_only":
            data["features"][0]["name"] = PRIVATE
        if calls == 3 and mode == "typed_only":
            data["microversionId"].update(ambiguous=False, deleted=False)
        if mode == "all_comparisons":
            if calls == 5:
                data["serializationVersion"] = PRIVATE
                data["libraryVersion"] += 1
            if calls == 6:
                data[PRIVATE] = PRIVATE
        return httpx.Response(200, json=data)

    if mode == "empty_classifier":
        monkeypatch.setattr(depth_reader, "baseline_differences", lambda *args: ())
    case.provider.handle = respond  # type: ignore[method-assign]
    no_release(monkeypatch)
    before = preserved(case)
    with pytest.raises(DepthBaselineDiagnostic) as error:
        case.recover()
    if mode == "typed_only":
        expected = (
            BASE + "body_revision_evidence_mismatch;current_comparison:exact_match"
        )
    elif mode == "all_comparisons":
        expected = (
            BASE
            + DIGESTS
            + (
                ";current_comparison:serialization_mismatch,library_mismatch,inventory_mismatch,"
                "configuration_mismatch:non_target_feature_changed,unknown_provider_metadata_changed"
            )
        )
    else:
        expected = (
            BASE
            + ("" if mode == "empty_classifier" else DIGESTS)
            + ";current_comparison:inventory_mismatch:non_target_feature_changed"
        )
    assert str(error.value) == expected
    assert PRIVATE not in str(error.value) + caplog.text
    assert calls == 8 and case.provider.writes == 0
    assert preserved(case) == before


@pytest.mark.parametrize(
    "index,mode,stage,category",
    [
        (4, "shape", "current_head", "provider_response"),
        (4, "transport", "current_head", "transport"),
        (5, "provider", "current_features", "provider_response"),
        (5, "shape", "current_feature_projection", "unavailable"),
        (6, "shape", "current_configuration_projection", "unavailable"),
        (7, "shape", "current_body_projection", "body_invalid"),
        (8, "head", "final_head", "changed"),
        (5, "deadline", "current_features", "deadline"),
    ],
)
def test_current_failure_is_combined_with_historical_mismatch(
    case: ServerCase,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    index: int,
    mode: str,
    stage: str,
    category: str,
) -> None:
    original = case.provider.handle
    calls = 0
    clock = [100.0]
    monkeypatch.setattr(depth_reader, "monotonic", lambda: clock[0])

    def respond(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == index and mode == "transport":
            raise httpx.ReadTimeout(PRIVATE)
        if calls == index and mode == "provider":
            return httpx.Response(503, text=PRIVATE)
        data = original(request).json()
        if calls == 1:
            data["features"][0]["name"] = PRIVATE
        if calls == index:
            if mode == "shape":
                data = {PRIVATE: PRIVATE}
            elif mode == "head":
                data = {"microversion": "f" * 24}
            elif mode == "deadline":
                clock[0] += 31
        return httpx.Response(200, json=data)

    case.provider.handle = respond  # type: ignore[method-assign]
    no_release(monkeypatch)
    before = preserved(case)
    with pytest.raises(DepthBaselineDiagnostic) as error:
        case.recover()
    comparison = (
        ";current_comparison:inventory_mismatch:non_target_feature_changed"
        if index == 8
        else ""
    )
    assert (
        str(error.value)
        == BASE + DIGESTS + comparison + ";current_capture:" + stage + ":" + category
    )
    assert PRIVATE not in str(error.value) + caplog.text
    assert calls == (7 if mode == "shape" and index > 4 else index)
    assert calls <= 8 and case.provider.writes == 0
    assert preserved(case) == before


def test_matching_history_still_uses_normal_evidence_path(case: ServerCase) -> None:
    evidence = reader(case).capture(case.reference, saved(case))
    assert evidence.head_before == evidence.head_after
    assert len(case.provider.calls) == 8
