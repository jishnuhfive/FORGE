"""Closed development diagnostics; synthetic transports and temporary rows only."""

import json
from dataclasses import replace
from typing import Any

import httpx2 as httpx
import pytest
from server_depth_support import ServerCase
from test_server_depth_evidence import reader, saved
from test_server_depth_recovery import case as case

from forge_api.cad_edits.domain import EditError
from forge_api.cad_edits.quantity_recovery_evidence import classify_depth_comparison
from forge_api.integrations.onshape import depth_reader
from forge_api.integrations.onshape.depth_reader import DepthReadFailure
from forge_api.integrations.onshape.modify_evidence import (
    project_modify_evidence,
    verify_operation,
)


@pytest.mark.parametrize(
    "mutation,expected",
    [
        ("none", None),
        ("inventory", "inventory_mismatch"),
        ("configuration", "configuration_mismatch"),
        ("serialization", "serialization_mismatch"),
        ("library", "library_mismatch"),
        ("parent_suppression_evidence", "parent_suppression_mismatch"),
        ("configured_suppression_evidence", "configured_suppression_mismatch"),
        ("revision", "revision_mismatch"),
        ("preview", "preview_mismatch"),
        ("malformed", "unavailable"),
    ],
)
def test_classifier_matches_unchanged_verifier(
    case: ServerCase, mutation: str, expected: str | None
) -> None:
    captures: list[Any] = []
    original = case.provider.handle

    def capture(request: httpx.Request) -> httpx.Response:
        response = original(request)
        captures.append(response.json())
        return response

    r = reader(case, capture)
    evidence = r.capture(case.reference, saved(case))
    context = case.reference.approval.context
    before = project_modify_evidence(
        context, saved(case).plan.baseline.microversion, *captures[:3]
    )
    marker = evidence.head_before
    after = project_modify_evidence(context, marker, *captures[4:7])
    operation = saved(case).plan.operations[0]
    if mutation in (
        "serialization",
        "library",
        "parent_suppression_evidence",
        "configured_suppression_evidence",
    ):
        old = getattr(after.baseline, mutation)
        # Isolate each independent exact comparison, including evidence summaries.
        new = old + 1 if type(old) is int else "synthetic-different"
        after = replace(
            after, baseline=after.baseline.model_copy(update={mutation: new})
        )
    elif mutation == "inventory":
        inventory = after.inventory()
        inventory["syntheticMetadata"] = "PRIVATE-SENTINEL"
        after = replace(after, inventory_json=json.dumps(inventory))
    elif mutation == "configuration":
        configuration = json.loads(after.configuration_json)
        configuration["syntheticMetadata"] = "PRIVATE-SENTINEL"
        after = replace(after, configuration_json=json.dumps(configuration))
    elif mutation == "revision":
        marker = before.baseline.microversion
    elif mutation == "preview":
        operation = operation.model_copy(update={"preview": {}})
    elif mutation == "malformed":
        before = replace(before, inventory_json='{"features":[]}')
    assert classify_depth_comparison(before, after, operation, marker) == expected
    if expected is None:
        verify_operation(before, after, operation, marker)
    else:
        with pytest.raises((EditError, ValueError, TypeError, KeyError, IndexError)):
            verify_operation(before, after, operation, marker)


@pytest.mark.parametrize(
    "index,mutation,expected",
    [
        (1, "transport", "historical_features:transport"),
        (1, "provider", "historical_features:provider_response"),
        (1, "malformed", "historical_features:provider_response"),
        (1, "shape", "historical_projection:unavailable"),
        (1, "name", "historical_projection:baseline_mismatch"),
        (2, "provider", "historical_configuration:provider_response"),
        (3, "provider", "historical_body:provider_response"),
        (4, "shape", "current_head:provider_response"),
        (5, "provider", "current_features:provider_response"),
        (5, "shape", "current_feature_projection:unavailable"),
        (6, "provider", "current_configuration:provider_response"),
        (6, "shape", "current_configuration_projection:unavailable"),
        (7, "provider", "current_body:provider_response"),
        (7, "shape", "current_body_projection:body_invalid"),
        (5, "name", "comparison:inventory_mismatch:non_target_feature_changed"),
        (6, "metadata", "comparison:configuration_mismatch"),
        (5, "serialization", "comparison:serialization_mismatch"),
        (5, "library", "comparison:library_mismatch"),
        (5, "parentSuppressed", "comparison:parent_suppression_mismatch"),
        (5, "suppressionConfigured", "comparison:configured_suppression_mismatch"),
        (8, "head", "final_head:changed"),
        (8, "provider", "final_head:provider_response"),
    ],
)
def test_closed_stage_output_preserves_incident_and_fence(
    case: ServerCase,
    caplog: pytest.LogCaptureFixture,
    index: int,
    mutation: str,
    expected: str,
) -> None:
    original = case.provider.handle
    count = 0

    def respond(request: httpx.Request) -> httpx.Response:
        nonlocal count
        count += 1
        if count != index:
            return original(request)
        if mutation == "transport":
            raise httpx.ReadTimeout("PRIVATE-SENTINEL")
        if mutation == "provider":
            return httpx.Response(503, text="PRIVATE-SENTINEL")
        if mutation == "malformed":
            return httpx.Response(
                200,
                content=b"PRIVATE-SENTINEL",
                headers={"content-type": "application/json"},
            )
        if mutation == "shape":
            return httpx.Response(200, json={"private": "PRIVATE-SENTINEL"})
        if mutation == "head":
            return httpx.Response(200, json={"microversion": "f" * 24})
        data = original(request).json()
        if mutation == "name":
            data["features"][0]["name"] = "PRIVATE-SENTINEL"
        elif mutation in ("parentSuppressed", "suppressionConfigured"):
            for feature in data["features"]:
                feature.pop(mutation, None)
        elif mutation == "metadata":
            data["private"] = "PRIVATE-SENTINEL"
        elif mutation == "serialization":
            data["serializationVersion"] = "PRIVATE-SENTINEL"
        elif mutation == "library":
            data["libraryVersion"] += 1
        return httpx.Response(200, json=data)

    case.provider.handle = respond  # type: ignore[method-assign]
    snapshot = case.snapshot()
    with pytest.raises(DepthReadFailure) as error:
        case.recover()
    assert str(error.value) == "depth_recovery:" + expected
    assert "PRIVATE-SENTINEL" not in str(error.value) + caplog.text
    assert case.snapshot() == snapshot
    assert case.provider.writes == 0
    assert count <= 8


def test_expired_capture_closed_deadline_label(case: ServerCase) -> None:
    snapshot = case.snapshot()
    r = reader(case)
    with pytest.raises(DepthReadFailure, match="historical_features:deadline"):
        r.capture(case.reference, saved(case), deadline=0)
    assert not case.provider.calls and case.snapshot() == snapshot


def test_classifier_never_overrides_authoritative_rejection(
    case: ServerCase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def reject(*args: object) -> None:
        raise EditError("verification_failed")

    monkeypatch.setattr(depth_reader, "check_depth_recovery_state", reject)
    monkeypatch.setattr(depth_reader, "classify_depth_comparison", lambda *args: None)
    snapshot = case.snapshot()
    with pytest.raises(DepthReadFailure, match="comparison:unavailable"):
        case.recover()
    assert case.snapshot() == snapshot and case.provider.writes == 0


def test_stream_deadline_is_classified_without_retry(
    case: ServerCase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = [100.0]
    monkeypatch.setattr(depth_reader, "monotonic", lambda: clock[0])
    original = case.provider.handle

    def slow(request: httpx.Request) -> httpx.Response:
        response = original(request)
        clock[0] += 31
        return response

    case.provider.handle = slow  # type: ignore[method-assign]
    snapshot = case.snapshot()
    with pytest.raises(DepthReadFailure, match="historical_features:deadline"):
        case.recover()
    assert len(case.provider.calls) == 1
    assert case.snapshot() == snapshot and case.provider.writes == 0
