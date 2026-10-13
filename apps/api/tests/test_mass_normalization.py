"""Synthetic scalar contract cases; no numeric values from live CAD data."""

from typing import cast

import pytest
from pydantic import JsonValue, ValidationError

from forge_api.integrations.onshape.contracts import Operation
from forge_api.integrations.onshape.models import MassBody, MassSummary
from forge_api.integrations.onshape.normalize import normalize


def summary(body: JsonValue) -> MassSummary:
    return cast(
        list[MassSummary],
        normalize(Operation.MASS, {"bodies": {"-all-": body}}).normalized,
    )[0]


@pytest.mark.parametrize("field", ["mass", "volume", "periphery"])
@pytest.mark.parametrize(
    "values",
    [
        [8.0, 7.0, 9.0],
        [8.0, 8.0, 9.0],
        [8.0, 7.0, 8.0],
        [8.0, 8.0, 8.0],
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 1.0],
        [0.0, -1.0, 1.0],
        [2.0, -0.1, 3.0],
        [2.0, 1.0, 8.0],
        [1.0, 1.0 - 1e-15, 1.0 + 1e-15],
    ],
)
def test_provider_order_and_equal_zero_asymmetric_or_narrow_bounds(
    field: str, values: list[float]
) -> None:
    normalized = summary({field: cast(JsonValue, values)})
    if field == "periphery":
        assert MassBody.model_validate({field: values}).periphery == values
    else:
        estimate = normalized.mass if field == "mass" else normalized.volume
        assert estimate and estimate.model_dump() == {
            "nominal": values[0],
            "lower": values[1],
            "upper": values[2],
        }
    assert normalized.units == "provider_native_unverified"


@pytest.mark.parametrize("field", ["mass", "volume", "periphery"])
@pytest.mark.parametrize("values", [[1, 2, 3], [3, 1, 2], [-1, -2, 0]])
def test_inverted_bounds_and_negative_physical_nominal_stay_rejected(
    field: str, values: list[int]
) -> None:
    with pytest.raises(ValidationError):
        summary({field: cast(JsonValue, values)})


@pytest.mark.parametrize("field", ["mass", "volume", "periphery"])
@pytest.mark.parametrize("position", [0, 1, 2])
@pytest.mark.parametrize("nonfinite", [float("nan"), float("inf"), -float("inf")])
def test_every_nonfinite_scalar_position_is_rejected(
    field: str, position: int, nonfinite: float
) -> None:
    values = [2.0, 1.0, 3.0]
    values[position] = nonfinite
    with pytest.raises(ValidationError):
        summary({field: cast(JsonValue, values)})


@pytest.mark.parametrize("field", ["mass", "volume", "periphery"])
@pytest.mark.parametrize("values", [[], [2], [1, 2], [1, 0, 2, 3], "2"])
def test_wrong_scalar_lengths_and_string_container_are_rejected(
    field: str, values: JsonValue
) -> None:
    with pytest.raises(ValidationError):
        summary({field: values})


@pytest.mark.parametrize("field", ["mass", "volume", "periphery"])
@pytest.mark.parametrize("position", [0, 1, 2])
@pytest.mark.parametrize("malformed", ["2", True])
def test_numeric_strings_and_booleans_are_not_coerced(
    field: str, position: int, malformed: JsonValue
) -> None:
    values: list[JsonValue] = [2.0, 1.0, 3.0]
    values[position] = malformed
    with pytest.raises(ValidationError):
        summary({field: values})


@pytest.mark.parametrize("flag", ["false", 0, 1, [], {}])
def test_malformed_has_mass_is_rejected(flag: JsonValue) -> None:
    with pytest.raises(ValidationError):
        MassBody.model_validate({"hasMass": flag})


@pytest.mark.parametrize("count", [-1, 1.5, 1.0, True, "0", [], {}])
def test_malformed_missing_count_is_rejected(count: JsonValue) -> None:
    with pytest.raises(ValidationError):
        MassBody.model_validate({"massMissingCount": count})


@pytest.mark.parametrize("count", [0, 1, 2])
def test_false_mass_flag_suppresses_estimate_and_preserves_volume_and_missing_count(
    count: int,
) -> None:
    missing = summary({"hasMass": False, "massMissingCount": count})
    assert missing.has_mass is False and missing.mass is None
    assert missing.mass_missing_count == count
    supplied = summary(
        {
            "hasMass": False,
            "mass": [0, -1, 1],
            "volume": [4, -1, 5],
            "massMissingCount": count,
        }
    )
    assert supplied.has_mass is False
    assert supplied.mass is None and supplied.mass_missing_count == count
    assert supplied.volume and supplied.volume.nominal == 4
    assert supplied.volume.lower == -1 and supplied.volume.upper == 5


def test_missing_and_null_estimates_stay_unknown() -> None:
    assert summary({}).mass is None
    assert summary({"mass": None}).mass is None


def test_assigned_mass_with_zero_missing_count_keeps_physical_estimate() -> None:
    result = summary({"mass": [2, 1, 3], "hasMass": True, "massMissingCount": 0})
    assert result.has_mass is True
    assert result.mass and result.mass.model_dump() == {
        "nominal": 2.0,
        "lower": 1.0,
        "upper": 3.0,
    }


@pytest.mark.parametrize("record", [None, [], "private", {"hasMass": "false"}])
def test_malformed_aggregate_records_remain_rejected(record: JsonValue) -> None:
    with pytest.raises(ValidationError):
        summary(record)
