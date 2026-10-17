"""Synthetic response indices; no captured CAD or provider mutations."""

from copy import deepcopy
from typing import Any

import pytest
from test_cad_read import REF
from test_safe_edit import M0, bodies, config, features

from forge_api.integrations.onshape.eligibility import (
    MISSING,
    EligibilityRejected,
    Reason,
)
from forge_api.integrations.onshape.write_evidence import project_write_evidence


def inventory(count: int) -> dict[str, Any]:
    data = features()
    if count == 4:
        extra = deepcopy(data["features"][1])
        extra["featureId"] = "synthetic-extra-extrude"
        data["features"].insert(2, extra)
        data["featureStates"][extra["featureId"]] = {
            "featureStatus": "OK",
            "inactive": False,
        }
    assert len(data["features"]) == count
    data["rollbackIndex"] = count
    return data


@pytest.mark.parametrize("count", [3, 4])
def test_response_rollback_at_exact_feature_count_is_eligible(count: int) -> None:
    result = project_write_evidence(REF, M0, inventory(count), config(), bodies())
    assert result.position == count and result.suppressed is False


@pytest.mark.parametrize("count", [3, 4])
def test_response_explicit_openapi_end_sentinel_remains_valid(count: int) -> None:
    data = inventory(count)
    data["rollbackIndex"] = -1
    result = project_write_evidence(REF, M0, data, config(), bodies())
    assert result.position == count


@pytest.mark.parametrize("count", [3, 4])
@pytest.mark.parametrize(
    "bad",
    [
        "zero",
        "before_end",
        "after_end",
        "missing",
        "null",
        "true",
        "false",
        "string",
        "float",
        "negative",
        "large",
    ],
)
def test_response_non_end_or_non_integer_rollback_rejects(count: int, bad: str) -> None:
    data = inventory(count)
    value = {
        "zero": 0,
        "before_end": count - 1,
        "after_end": count + 1,
        "missing": MISSING,
        "null": None,
        "true": True,
        "false": False,
        "string": str(count),
        "float": float(count),
        "negative": -2,
        "large": 100,
    }[bad]
    if value is MISSING:
        data.pop("rollbackIndex")
    else:
        data["rollbackIndex"] = value
    with pytest.raises(EligibilityRejected) as caught:
        project_write_evidence(REF, M0, data, config(), bodies())
    assert caught.value.code == "unsupported_target"
    assert caught.value.diagnostic.reason == Reason.ROLLBACK
    assert caught.value.diagnostic.field == "rollbackIndex"
    assert caught.value.diagnostic.expected == "end_of_list"


@pytest.mark.parametrize("count", [3, 4])
def test_exact_end_does_not_allow_incomplete_inventory(count: int) -> None:
    data = inventory(count)
    data["isComplete"] = False
    with pytest.raises(EligibilityRejected) as caught:
        project_write_evidence(REF, M0, data, config(), bodies())
    assert caught.value.diagnostic.reason == Reason.INCOMPLETE


@pytest.mark.parametrize("count", [3, 4])
def test_exact_end_does_not_bypass_next_eligibility_check(count: int) -> None:
    data = inventory(count)
    data["features"][-1]["namespace"] = None
    with pytest.raises(EligibilityRejected) as caught:
        project_write_evidence(REF, M0, data, config(), bodies())
    assert caught.value.diagnostic.reason == Reason.NAMESPACE
    assert caught.value.diagnostic.position == count
