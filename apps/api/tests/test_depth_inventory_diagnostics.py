"""Synthetic inventory-only diagnostics; no real provider or incident access."""

import json
from copy import deepcopy
from dataclasses import replace
from typing import Any

import httpx2 as httpx
import pytest
from server_depth_support import ServerCase
from test_modify_plan import inventory
from test_server_depth_console import console
from test_server_depth_evidence import reader, saved
from test_server_depth_recovery import case as case

from forge_api.cad_edits.depth_inventory_diagnostics import ORDER, inventory_differences
from forge_api.cad_edits.domain import EditError
from forge_api.cad_edits.quantity_recovery_evidence import classify_depth_inventory
from forge_api.integrations.onshape.modify_evidence import (
    project_modify_evidence,
    verify_operation,
)

PRIVATE = "PRIVATE-SENTINEL-DO-NOT-EMIT"


def mutate(data: dict[str, Any], category: str) -> None:
    feature = data["features"][1]
    params = feature["parameters"]
    depth = next(p for p in params if p["parameterId"] == "depth")
    if category == "feature_count_changed":
        data["features"].pop()
    elif category == "feature_order_or_identity_changed":
        data["features"].reverse()
    elif category == "non_target_feature_changed":
        data["features"][0]["name"] = PRIVATE
    elif category == "target_name_changed":
        feature["name"] = PRIVATE
    elif category == "target_suppression_changed":
        feature["suppressed"] = True
    elif category == "target_definition_metadata_changed":
        feature["namespace"] = PRIVATE
    elif category == "target_parameter_count_changed":
        params.pop(0)
    elif category == "target_parameter_order_changed":
        params.reverse()
    elif category == "target_parameter_type_or_shape_changed":
        depth["btType"] = PRIVATE
    elif category == "target_depth_expression_unexpected":
        depth["expression"] = PRIVATE
    elif category == "target_depth_parameter_metadata_changed":
        depth["isInteger"] = False  # Non-node metadata stays write-critical.
    elif category == "other_target_parameter_metadata_changed":
        params[0]["value"] = PRIVATE
    elif category == "feature_states_changed":
        data["featureStates"] = {PRIVATE: {PRIVATE: PRIVATE}}
    elif category == "source_revision_metadata_changed":
        data["sourceMicroversion"] = PRIVATE
    else:
        data[PRIVATE] = {PRIVATE: PRIVATE}


@pytest.mark.parametrize("category", ORDER)
def test_every_fixed_category_is_type_sensitive_and_private(category: str) -> None:
    expected = inventory()
    actual = deepcopy(expected)
    mutate(actual, category)
    original = deepcopy((expected, actual))
    differences = inventory_differences(
        expected, actual, expected["features"][1]["featureId"]
    )
    assert category in differences
    assert all(c in ORDER for c in differences)
    assert differences == tuple(c for c in ORDER if c in differences)
    assert PRIVATE not in repr(differences)
    assert (expected, actual) == original  # diagnostic cannot normalize inputs


def test_complete_deduplicated_set_and_order_do_not_depend_on_dictionary_order() -> (
    None
):
    expected = inventory()
    actual = deepcopy(expected)
    categories = (
        "non_target_feature_changed",
        "target_name_changed",
        "target_suppression_changed",
        "target_depth_expression_unexpected",
        "feature_states_changed",
        "source_revision_metadata_changed",
        "unknown_provider_metadata_changed",
    )
    for category in reversed(categories):
        mutate(actual, category)
    actual[PRIVATE + "other"] = PRIVATE
    assert (
        inventory_differences(expected, actual, expected["features"][1]["featureId"])
        == categories
    )
    reordered = dict(reversed(list(actual.items())))
    assert (
        inventory_differences(expected, reordered, expected["features"][1]["featureId"])
        == categories
    )


@pytest.mark.parametrize(
    "location", ["inventory", "target", "parameter", "nested_query", "state"]
)
@pytest.mark.parametrize("mode", ["addition", "removal", "value"])
def test_unknown_keys_are_only_generic(location: str, mode: str) -> None:
    expected = inventory()
    target = expected["features"][1]
    container = {
        "state": next(iter(expected["featureStates"].values())),
        "inventory": expected,
        "target": target,
        "parameter": target["parameters"][-1],
        "nested_query": target["parameters"][2]["queries"][0],
    }[location]
    if mode != "addition":
        container[PRIVATE] = "old-private"
    actual = deepcopy(expected)
    other = {
        "state": next(iter(actual["featureStates"].values())),
        "inventory": actual,
        "target": actual["features"][1],
        "parameter": actual["features"][1]["parameters"][-1],
        "nested_query": actual["features"][1]["parameters"][2]["queries"][0],
    }[location]
    if mode == "removal":
        del other[PRIVATE]
    else:
        other[PRIVATE] = PRIVATE
    expected_codes = (("feature_states_changed",) if location == "state" else ()) + (
        "unknown_provider_metadata_changed",
    )
    assert (
        inventory_differences(expected, actual, target["featureId"]) == expected_codes
    )


@pytest.mark.parametrize("category", (None, *ORDER))
def test_differential_with_authoritative_verifier(
    case: ServerCase, category: str | None
) -> None:
    snapshot = case.snapshot()
    captures: list[Any] = []
    original = case.provider.handle

    def capture(request: httpx.Request) -> httpx.Response:
        response = original(request)
        captures.append(response.json())
        return response

    evidence = reader(case, capture).capture(case.reference, saved(case))
    assert len(captures) == 8
    context = case.reference.approval.context
    before = project_modify_evidence(
        context, saved(case).plan.baseline.microversion, *captures[:3]
    )
    after = project_modify_evidence(context, evidence.head_before, *captures[4:7])
    operation = saved(case).plan.operations[0]
    if category:
        raw = after.inventory()
        mutate(raw, category)
        after = replace(after, inventory_json=json.dumps(raw))
        with pytest.raises(EditError, match="verification_failed"):
            verify_operation(before, after, operation, evidence.head_before)
        assert category in classify_depth_inventory(
            before, after, operation, evidence.head_before
        )
        # Rechecking after classification still rejects; no input mutation/authority.
        with pytest.raises(EditError, match="verification_failed"):
            verify_operation(before, after, operation, evidence.head_before)
    else:
        verify_operation(before, after, operation, evidence.head_before)
        assert (
            classify_depth_inventory(before, after, operation, evidence.head_before)
            == ()
        )
        verify_operation(before, after, operation, evidence.head_before)

    assert case.snapshot() == snapshot and case.provider.writes == 0


def test_one_operator_attempt_reports_all_differences_without_more_gets(
    case: ServerCase,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    original = case.provider.handle
    count = 0

    def respond(request: httpx.Request) -> httpx.Response:
        nonlocal count
        count += 1
        response = original(request)
        if count == 5:
            data = response.json()
            for category in (
                "non_target_feature_changed",
                "target_name_changed",
                "target_depth_parameter_metadata_changed",
                "unknown_provider_metadata_changed",
            ):
                mutate(data, category)
            return httpx.Response(200, json=data)
        return response

    case.provider.handle = respond  # type: ignore[method-assign]
    monkeypatch.setattr(
        console, "recover_development_depth_incident", lambda *a, **kw: case.recover()
    )
    answers = iter(
        ["DISPOSABLE SETTLED DRAINED AUTHORIZE", case.reference.review.stack, ""]
    )
    output: list[str] = []
    snapshot = case.snapshot()
    result = console.operator_attempt(
        case.harness.runtime,
        ask=lambda _: next(answers),
        private=lambda _: (
            "Synthetic independent settlement review; all writers drained."
        ),
        report=output.append,
    )
    assert result == 1
    assert output[-1] == (
        "DENIED depth_recovery:comparison:inventory_mismatch:"
        "non_target_feature_changed,target_name_changed,target_parameter_type_or_shape_changed,"
        "target_depth_parameter_metadata_changed,unknown_provider_metadata_changed"
    )
    assert PRIVATE not in repr(output) + caplog.text
    assert count == 7  # existing rejection occurs before the final head GET
    assert case.provider.writes == 0 and case.snapshot() == snapshot


@pytest.mark.parametrize("container", ["features", "parameters", "query"])
@pytest.mark.parametrize("remove", [False, True])
def test_unmatched_structures_cannot_hide_unknown_fields(
    container: str, remove: bool
) -> None:
    expected = inventory()
    actual = deepcopy(expected)
    if container == "features":
        actual["features"].append({"featureId": PRIVATE, PRIVATE: PRIVATE})
    elif container == "parameters":
        actual["features"][1]["parameters"].append(
            {"parameterId": PRIVATE, PRIVATE: PRIVATE}
        )
    else:
        actual["features"][1]["parameters"][2]["queries"].append({PRIVATE: PRIVATE})
    if remove:
        expected, actual = actual, expected
    result = inventory_differences(
        expected, actual, expected["features"][1]["featureId"]
    )
    assert "unknown_provider_metadata_changed" in result
    assert PRIVATE not in repr(result)
