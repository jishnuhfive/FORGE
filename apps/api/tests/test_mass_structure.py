"""Synthetic structure-only diagnostics; no real provider responses."""

import json
import logging
from copy import deepcopy
from typing import cast

import httpx2 as httpx
import pytest
from conftest import Harness
from pydantic import JsonValue
from test_cad_read import MASS, PATH, REF, CadProvider, fetch, transport

from forge_api.db.models import OnshapeAuthorization
from forge_api.integrations.onshape.client import OnshapeReadClient, ReadError
from forge_api.integrations.onshape.contracts import Operation
from forge_api.integrations.onshape.dev.mass_structure import describe_mass, mass_facts
from forge_api.integrations.onshape.normalize import normalize

# Live-observed shape only; every numeric value and identifier is invented.
LIVE_SHAPED_MASS: JsonValue = {
    "microversionId": "d" * 24,
    "bodies": {
        "-all-": {
            "mass": [8.0, 7.0, 9.0],
            "volume": [4.0, 3.0, 5.0],
            "periphery": [6.0, 5.0, 7.0],
            "centroid": [float(value) for value in range(-4, 5)],
            "inertia": [float(value) for value in range(27)],
            "hasMass": True,
            "massMissingCount": 0,
            "principalInertia": [6.0, 2.0, 4.0],
            "principalAxes": [
                {"x": 1.0, "y": 0.0, "z": 0.0, "btType": "BTVector3d-389"},
                {"x": 0.0, "y": 1.0, "z": 0.0},
                {"x": 0.0, "y": 0.0, "z": 1.0},
            ],
        }
    },
}


def failed_structure(raw: object) -> dict[str, object]:
    try:
        normalize(Operation.MASS, cast(JsonValue, raw))
    except ValueError as error:
        return cast(
            dict[str, object], json.loads(describe_mass(cast(JsonValue, raw), error))
        )
    raise AssertionError("Fixture must fail existing strict normalization")


@pytest.mark.parametrize(
    ("raw", "field", "reason"),
    [
        ({"bodies": []}, "bodies", "type_mismatch"),
        ({"bodies": {"synthetic-private-body": []}}, "bodies", "type_mismatch"),
        ({"bodies": {"-all-": {"mass": [1, 2]}}}, "mass", "length_limit"),
        ({"bodies": {"-all-": {"mass": [1, 2, 3]}}}, "mass", "invalid_bounds"),
        ({"bodies": {"-all-": {"mass": ["private-value"]}}}, "mass", "type_mismatch"),
        ({"bodies": {"-all-": {"mass": [float("inf")]}}}, "mass", "nonfinite_number"),
        ({"bodies": {"-all-": {"mass": [True]}}}, "mass", "type_mismatch"),
        ({"bodies": {"-all-": {"centroid": [0] * 10}}}, "centroid", "length_limit"),
        (
            {"bodies": {"-all-": {"inertia": {"private": 1}}}},
            "inertia",
            "type_mismatch",
        ),
        (
            {"bodies": {"-all-": {"principalInertia": [0] * 9}}},
            "principalInertia",
            "length_limit",
        ),
        (
            {"bodies": {"-all-": {"hasMass": "private-value"}}},
            "hasMass",
            "type_mismatch",
        ),
        (
            {"bodies": {"-all-": {"massMissingCount": -1}}},
            "massMissingCount",
            "numeric_bound",
        ),
    ],
)
def test_known_validation_reasons(raw: object, field: str, reason: str) -> None:
    report = failed_structure(raw)
    assert {"field": field, "reason": reason} in [
        {"field": item["field"], "reason": item["reason"]}
        for item in cast(list[dict[str, object]], report["validation"])
    ]
    assert "private" not in json.dumps(report)


def test_structure_never_copies_values_unknown_names_ids_or_error_context() -> None:
    private = "synthetic-private-body"
    raw: JsonValue = {
        "microversionId": "a" * 24,
        "private-top-field": "synthetic-token",
        "bodies": {
            private: {
                "mass": ["synthetic-private-value"],
                "volume": [98765.4321, 98764.4321, 98766.4321],
                "centroid": [76543.21] * 9,
                "inertia": [65432.1] * 27,
                "principalInertia": [54321.9] * 3,
                "principalAxes": [
                    {
                        "x": 43210.9,
                        "y": 32109.8,
                        "z": 21098.7,
                        "btType": "private-type",
                        "private-axis-field": "secret",
                    }
                ],
                "hasMass": True,
                "massMissingCount": 123456,
                "private-body-field": "https://private.invalid/raw?token=secret",
            }
        },
    }
    report = failed_structure(raw)
    text = json.dumps(report)
    for value in (
        private,
        "private-",
        "synthetic-token",
        "secret",
        "https:",
        "a" * 24,
        "98765",
        "76543",
        "65432",
        "54321",
        "43210",
        "123456",
    ):
        assert value not in text
    fields = {
        item["field"]: item for item in cast(list[dict[str, object]], report["fields"])
    }
    assert fields["volume"] == {
        "field": "volume",
        "type": "array",
        "length": 3,
        "items": ["number"],
    }
    assert fields["principalAxes.x"] == {"field": "principalAxes.x", "type": "number"}
    assert fields["hasMass"]["type"] == "boolean"
    assert fields["periphery"]["type"] == "absent"
    assert report["recordKind"] == "body"


def test_aggregate_is_classified_without_echoing_any_body_key() -> None:
    report = failed_structure({"bodies": {"-all-": {"mass": [1, 2]}}})
    assert report["recordKind"] == "aggregate"
    assert "-all-" not in json.dumps(report)


def test_output_is_bounded_even_for_many_records_and_validation_failures() -> None:
    raw = {
        "bodies": {
            f"private-{index}": {"mass": ["private"] * 4} for index in range(2000)
        }
    }
    report = failed_structure(raw)
    assert len(json.dumps(report, separators=(",", ":"))) <= 4096
    assert len(cast(list[object], report["validation"])) == 8
    assert "private" not in json.dumps(report)


@pytest.mark.parametrize("environment", ["development", "test", "production"])
def test_header_only_in_development_and_proof_unchanged(
    harness: Harness,
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    harness.login()
    monkeypatch.setattr(harness.runtime.settings, "environment", environment)
    provider = CadProvider()
    provider.responses["mass"] = {
        "bodies": {"private-body": {"mass": ["private-token"]}}
    }
    with (
        caplog.at_level(logging.INFO, logger="forge.onshape.read"),
        transport(harness, provider),
    ):
        response = fetch(harness)
    data = response.json()
    assert data["mass"]["status"] == "provider_failure"
    assert data["mass"]["code"] == "invalid_response"
    assert (
        data["features"]["count"] == 2
        and data["parts"]["count"] == 1
        and data["bodies"]["count"] == 1
    )
    assert data["has_mass"] is None
    assert set(data) == {
        "schema_version",
        "request_id",
        "captured_at",
        "consistency",
        "features",
        "parts",
        "bodies",
        "mass",
        "has_mass",
    }
    header = response.headers.get("X-Forge-Mass-Structure")
    if environment == "development":
        assert header and len(header) <= 4096
        assert json.loads(header)["diagnostic"] == "forge-mass-structure-v1"
    else:
        assert header is None
    assert "private" not in response.text + str(header) + caplog.text
    assert len(provider.calls) == 4


def test_no_diagnostic_for_successful_mass_or_unsigned_requests(
    harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(harness.runtime.settings, "environment", "development")
    assert (
        harness.client.get(PATH, params=REF.model_dump()).headers.get(
            "X-Forge-Mass-Structure"
        )
        is None
    )
    harness.login()
    with transport(harness, CadProvider()):
        response = fetch(harness)
    assert response.json()["mass"]["status"] == "success"
    assert response.headers.get("X-Forge-Mass-Structure") is None


@pytest.mark.parametrize("mode", ["json", "metadata"])
def test_transport_failures_are_sanitized_without_raw_body(mode: str) -> None:
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200,
                content=b"private-provider-body",
                headers={
                    "Content-Type": "application/json"
                    if mode == "json"
                    else "text/html"
                },
            )
        )
    ) as transport_client:
        client = OnshapeReadClient(
            "https://cad.onshape.com/api",
            transport_client,
            mass_diagnostic=describe_mass,
        )
        with pytest.raises(ReadError, match="invalid_response"):
            client.mass(REF, "synthetic-token", "0" * 32)
    assert client.mass_structure is not None
    assert json.loads(client.mass_structure)["reason"] == (
        "invalid_json_or_normalization" if mode == "json" else "transport_metadata"
    )
    assert "private" not in client.mass_structure


def test_documented_fixture_still_normalizes_without_parser_changes() -> None:
    assert normalize(Operation.MASS, cast(JsonValue, MASS)).normalized


def live_style_missing_mass() -> JsonValue:
    """Verified live shape with invented numbers, unavailable density and no IDs."""
    raw = deepcopy(LIVE_SHAPED_MASS)
    body = cast(
        dict[str, JsonValue],
        cast(dict[str, JsonValue], cast(dict[str, JsonValue], raw)["bodies"])["-all-"],
    )
    body.update(mass=[0.0, -0.125, 0.25], hasMass=False, massMissingCount=2)
    return raw


def test_live_style_missing_mass_normalizes_without_a_physical_zero_estimate() -> None:
    from forge_api.integrations.onshape.models import MassSummary

    raw = live_style_missing_mass()
    result = normalize(Operation.MASS, raw)
    item = cast(list[MassSummary], result.normalized)[0]
    assert item.has_mass is False and item.mass is None
    assert item.mass_missing_count == 2
    assert item.volume and item.volume.model_dump() == {
        "nominal": 4.0,
        "lower": 3.0,
        "upper": 5.0,
    }
    assert item.centroid_provider_values == [float(v) for v in range(-4, 5)]
    assert item.inertia_provider_values == [float(v) for v in range(27)]
    assert item.principal_inertia_provider_values == [6.0, 2.0, 4.0]
    assert item.units == "provider_native_unverified" and result.raw == raw


@pytest.mark.parametrize("environment", ["development", "production"])
def test_live_style_missing_mass_is_successful_safe_snapshot(
    harness: Harness,
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    harness.login()
    monkeypatch.setattr(harness.runtime.settings, "environment", environment)
    provider = CadProvider()
    provider.responses["mass"] = live_style_missing_mass()
    with transport(harness, provider):
        response = fetch(harness)
    data = response.json()
    assert all(
        data[name]["status"] == "success"
        for name in ("features", "parts", "bodies", "mass")
    )
    assert data["mass"]["code"] == "ok" and data["has_mass"] is False
    assert data["features"]["count"] == 2
    assert data["parts"]["count"] == 1 and data["bodies"]["count"] == 1
    assert response.headers.get("X-Forge-Mass-Structure") is None
    assert len(provider.calls) == 4
    assert all(
        value not in response.text
        for value in (
            "-0.125",
            "0.25",
            "nominal",
            "volume",
            "principalAxes",
            "microversionId",
        )
    )


@pytest.mark.parametrize(("missing", "availability"), [(0, True), (1, None)])
def test_assigned_and_partial_mass_snapshot_availability(
    harness: Harness,
    missing: int,
    availability: bool | None,
) -> None:
    harness.login()
    provider = CadProvider()
    provider.responses["mass"] = {
        "bodies": {
            "-all-": {
                "mass": [2, -1, 3],
                "hasMass": True,
                "massMissingCount": missing,
            }
        }
    }
    with transport(harness, provider):
        response = fetch(harness)
    data = response.json()
    assert data["mass"]["status"] == "success"
    assert data["has_mass"] is availability
    assert response.headers.get("X-Forge-Mass-Structure") is None


@pytest.mark.parametrize(
    "body",
    [
        {"mass": [-1, -2, 0], "hasMass": False},
        {"mass": [1, 2, 3]},
        {"mass": [3, 1, 2]},
        {"mass": []},
        {"mass": [2]},
        {"mass": [0, -1, 1], "hasMass": "false"},
        {"mass": [0, -1, 1], "massMissingCount": -1},
        {"mass": [0, -1, 1], "massMissingCount": True},
    ],
)
def test_scalar_repair_keeps_api_validation_failures_strict(
    harness: Harness,
    body: JsonValue,
) -> None:
    harness.login()
    provider = CadProvider()
    provider.responses["mass"] = {"bodies": {"private-body": body}}
    with transport(harness, provider):
        data = fetch(harness).json()
    assert data["mass"]["status"] == "provider_failure"
    assert data["mass"]["code"] == "invalid_response" and data["has_mass"] is None
    assert data["features"]["status"] == data["parts"]["status"] == "success"
    assert data["bodies"]["status"] == "success"
    assert "private-body" not in json.dumps(data)


def test_disconnect_after_mass_failure_discards_diagnostic(
    harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = harness.login()
    monkeypatch.setattr(harness.runtime.settings, "environment", "development")
    provider = CadProvider()
    provider.responses["mass"] = {
        "bodies": {"private-body": {"mass": ["private-token"]}}
    }

    def handle(request: httpx.Request) -> httpx.Response:
        response = provider.handle(request)
        if request.url.path.endswith("massproperties"):
            with harness.runtime.sessions.begin() as db:
                grant = db.get(OnshapeAuthorization, user)
                assert grant
                grant.status = "disconnected"
                grant.encrypted_refresh_token = None
        return response

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        harness.client.app.state.cad_transport = client  # type: ignore[attr-defined]
        response = fetch(harness)
    assert len(provider.calls) == 4
    assert response.headers.get("X-Forge-Mass-Structure") is None
    assert response.json()["mass"]["code"] == "connection_required"
    assert "private" not in response.text


def test_client_clears_failed_structure_before_next_mass_read() -> None:
    provider = CadProvider()
    provider.responses["mass"] = {"bodies": []}
    with httpx.Client(
        transport=httpx.MockTransport(provider.handle)
    ) as transport_client:
        client = OnshapeReadClient(
            "https://cad.onshape.com/api",
            transport_client,
            mass_diagnostic=describe_mass,
        )
        with pytest.raises(ReadError, match="invalid_response"):
            client.mass(REF, "synthetic-token", "0" * 32)
        assert client.mass_structure
        provider.responses["mass"] = MASS
        client.mass(REF, "synthetic-token", "1" * 32)
        assert client.mass_structure is None


def test_live_shaped_fixture_already_normalizes_with_distinct_component_semantics() -> (
    None
):
    from forge_api.integrations.onshape.models import MassSummary

    normalized = cast(
        list[MassSummary], normalize(Operation.MASS, LIVE_SHAPED_MASS).normalized
    )[0]
    assert normalized.mass and normalized.mass.model_dump() == {
        "nominal": 8.0,
        "lower": 7.0,
        "upper": 9.0,
    }
    assert normalized.volume and normalized.volume.model_dump() == {
        "nominal": 4.0,
        "lower": 3.0,
        "upper": 5.0,
    }
    assert normalized.centroid_provider_values == [
        float(value) for value in range(-4, 5)
    ]
    assert normalized.inertia_provider_values == [float(value) for value in range(27)]
    # This ordering would fail scalar bounds, but principal inertia is a vector.
    assert normalized.principal_inertia_provider_values == [6.0, 2.0, 4.0]
    assert normalized.units == "provider_native_unverified"


@pytest.mark.parametrize("field", ["mass", "volume", "periphery"])
@pytest.mark.parametrize(
    "values", [[-1.0, -2.0, 0.0], [1.0, 2.0, 3.0], [3.0, 1.0, 2.0]]
)
def test_live_shaped_bounds_failure_names_exact_scalar_without_values(
    field: str, values: list[float]
) -> None:
    raw = deepcopy(LIVE_SHAPED_MASS)
    body = cast(
        dict[str, JsonValue],
        cast(dict[str, JsonValue], cast(dict[str, JsonValue], raw)["bodies"])["-all-"],
    )
    body[field] = cast(JsonValue, values)
    report = failed_structure(raw)
    validation = cast(list[dict[str, object]], report["validation"])
    assert len(validation) == 1
    assert validation[0]["field"] == field
    assert validation[0]["reason"] == "invalid_bounds"
    assert all(
        set(entry) == {"field", "reason", "failedPredicates", "comparisons"}
        for entry in validation
    )


def test_both_invalid_scalars_are_reported_and_private_body_key_is_not() -> None:
    raw = {"bodies": {"private-body-id": {"mass": [1, 2, 3], "volume": [3, 1, 2]}}}
    report = failed_structure(raw)
    assert [
        {"field": item["field"], "reason": item["reason"]}
        for item in cast(list[dict[str, object]], report["validation"])
    ] == [
        {"field": "mass", "reason": "invalid_bounds"},
        {"field": "volume", "reason": "invalid_bounds"},
    ]
    assert "private-body-id" not in json.dumps(report)


@pytest.mark.parametrize("key", ["private-body", "mass"])
def test_field_error_uses_failed_record_not_sampled_aggregate(key: str) -> None:
    report = failed_structure(
        {
            "bodies": {
                "-all-": {"mass": [3, 2, 4], "volume": [3, 2, 4]},
                key: {"volume": [3, 4, 5]},
            }
        }
    )
    assert report["recordKind"] == "aggregate"
    assert report["validation"] == [
        {
            "field": "volume",
            "reason": "invalid_bounds",
            "failedPredicates": ["bounds_order"],
            "comparisons": {
                "position0_vs_position1": "less",
                "position0_vs_position2": "less",
                "position1_vs_position2": "less",
            },
        }
    ]
    assert "private-body" not in json.dumps(report)


def test_body_key_equal_to_safe_field_is_never_used_as_validation_field() -> None:
    report = failed_structure({"bodies": {"mass": []}})
    assert report["validation"] == [{"field": "bodies", "reason": "type_mismatch"}]


@pytest.mark.parametrize("field", ["mass", "volume", "periphery"])
@pytest.mark.parametrize("environment", ["development", "production"])
def test_snapshot_names_exact_scalar_only_in_development(
    harness: Harness, monkeypatch: pytest.MonkeyPatch, field: str, environment: str
) -> None:
    harness.login()
    monkeypatch.setattr(harness.runtime.settings, "environment", environment)
    provider = CadProvider()
    provider.responses["mass"] = {
        "bodies": {"private-body": {field: [123.5, 124.5, 125.5]}}
    }
    with transport(harness, provider):
        response = fetch(harness)
    assert response.json()["mass"]["code"] == "invalid_response"
    header = response.headers.get("X-Forge-Mass-Structure")
    if environment == "development":
        assert header
        assert json.loads(header)["validation"] == [
            {
                "field": field,
                "reason": "invalid_bounds",
                "failedPredicates": ["bounds_order"],
                "comparisons": {
                    "position0_vs_position1": "less",
                    "position0_vs_position2": "less",
                    "position1_vs_position2": "less",
                },
            }
        ]
        assert "123.5" not in header and "private-body" not in header
    else:
        assert header is None
    assert "123.5" not in response.text


@pytest.mark.parametrize("field", ["mass", "volume", "periphery"])
@pytest.mark.parametrize(
    ("values", "predicates", "comparisons"),
    [
        ([-1.0, -2.0, 0.0], ["negative_nominal"], ["greater", "less", "less"]),
        ([1.0, 2.0, 3.0], ["bounds_order"], ["less", "less", "less"]),
        ([3.0, 1.0, 2.0], ["bounds_order"], ["greater", "greater", "less"]),
        (
            [-3.0, -1.0, -2.0],
            ["negative_nominal"],
            ["less", "less", "greater"],
        ),
        ([-1.0, -1.0, -1.0], ["negative_nominal"], ["equal", "equal", "equal"]),
    ],
)
def test_exact_bounds_predicates_and_value_free_pairwise_comparisons(
    field: str, values: list[float], predicates: list[str], comparisons: list[str]
) -> None:
    report = failed_structure({"bodies": {"private-record": {field: values}}})
    assert report["validation"] == [
        {
            "field": field,
            "reason": "invalid_bounds",
            "failedPredicates": predicates,
            "comparisons": dict(
                zip(
                    (
                        "position0_vs_position1",
                        "position0_vs_position2",
                        "position1_vs_position2",
                    ),
                    comparisons,
                    strict=True,
                )
            ),
        }
    ]
    assert "private-record" not in json.dumps(report)


def test_length_failure_has_no_comparisons_or_bounds_predicate() -> None:
    report = failed_structure({"bodies": {"-all-": {"mass": [-1, -2]}}})
    assert report["validation"] == [
        {
            "field": "mass",
            "reason": "length_limit",
        }
    ]


def test_predicate_capture_never_copies_numeric_values_secrets_or_unknown_keys() -> (
    None
):
    report = failed_structure(
        {
            "microversionId": "a" * 24,
            "token": "synthetic-access-refresh-secret",
            "bodies": {
                "private-selection-body": {
                    "mass": [-12345.67, -12346.78, -12344.56],
                    "volume": [76543.21, 76544.32, 76545.43],
                    "private-field": "https://private.invalid/?secret=synthetic",
                }
            },
        }
    )
    text = json.dumps(report)
    assert "negative_nominal" in text and "bounds_order" in text
    for forbidden in (
        "12345",
        "12346",
        "12344",
        "76543",
        "76544",
        "76545",
        "private",
        "token",
        "secret",
        "https:",
        "a" * 24,
    ):
        assert forbidden not in text


def test_comparison_metadata_remains_bounded_for_many_failed_records() -> None:
    report = failed_structure(
        {
            "bodies": {
                f"private-{i}": {"mass": [-1, 2, 3], "volume": [-2, 3, 4]}
                for i in range(2000)
            }
        }
    )
    assert len(json.dumps(report, separators=(",", ":"))) <= 4096
    assert len(cast(list[object], report["validation"])) == 8
    assert "private" not in json.dumps(report)


@pytest.mark.parametrize(
    ("values", "signs"),
    [
        ([0.0, -1.0, 1.0], ["zero", "negative", "positive"]),
        ([2.0, -0.5, 3.0], ["positive", "negative", "positive"]),
        ([-2.0, -3.0, -1.0], ["negative", "negative", "negative"]),
        ([-1.0, -2.0, 0.0], ["negative", "negative", "zero"]),
        ([0.0, -1.0, 0.0], ["zero", "negative", "zero"]),
    ],
)
@pytest.mark.parametrize(("has_mass", "missing"), [(False, 1), (True, 0)])
def test_only_signs_and_authorized_availability_facts_from_failed_mass(
    values: list[float], signs: list[str], has_mass: bool, missing: int
) -> None:
    report = mass_facts(
        {
            "mass": cast(JsonValue, values),
            "hasMass": has_mass,
            "massMissingCount": missing,
        }
    )
    assert report["massSigns"] == dict(
        zip(
            ("position0", "position1", "position2"),
            signs,
            strict=True,
        )
    )
    assert report["hasMass"] is has_mass
    assert report["massMissingCountCategory"] == (
        "zero" if missing == 0 else "positive"
    )
    assert "private-record" not in json.dumps(report)


@pytest.mark.parametrize(
    "values",
    [
        [0, -1],
        [0, -1, "private"],
        [0, -1, True],
        [0, -1, float("nan")],
        [0, -1, float("inf")],
    ],
)
def test_sign_capture_does_not_classify_malformed_or_nonfinite_values(
    values: JsonValue,
) -> None:
    assert mass_facts({"mass": values}) == {}


@pytest.mark.parametrize(
    ("flag", "missing"), [("false", -1), (0, True), (None, "1"), ([], 1.0)]
)
def test_availability_capture_does_not_coerce_or_echo_invalid_fields(
    flag: JsonValue,
    missing: JsonValue,
) -> None:
    assert mass_facts({"hasMass": flag, "massMissingCount": missing}) == {}


def test_sign_and_availability_capture_uses_first_failed_record_not_aggregate() -> None:
    report = failed_structure(
        {
            "bodies": {
                "-all-": {"mass": [2, 1, 3], "hasMass": True, "massMissingCount": 0},
                "private-first": {
                    "mass": [-1, -2, 1],
                    "hasMass": False,
                    "massMissingCount": 1,
                },
                "private-second": {
                    "mass": [-2, -3, -1],
                    "hasMass": True,
                    "massMissingCount": 0,
                },
            }
        }
    )
    assert report["massSigns"] == {
        "position0": "negative",
        "position1": "negative",
        "position2": "positive",
    }
    assert report["hasMass"] is False
    assert report["massMissingCountCategory"] == "positive"
    assert "private" not in json.dumps(report)


def test_sign_capture_is_not_added_for_volume_failure() -> None:
    report = failed_structure(
        {
            "bodies": {
                "-all-": {
                    "mass": [2, 1, 3],
                    "volume": [0, 1, 2],
                    "hasMass": True,
                    "massMissingCount": 1,
                }
            }
        }
    )
    assert {"massSigns", "hasMass", "massMissingCountCategory"}.isdisjoint(report)


def test_sign_capture_never_copies_numeric_values_ids_secrets_or_urls() -> None:
    report = failed_structure(
        {
            "bodies": {
                "private-selection-id": {
                    "mass": [-1.123, -65432.123, 87654.321],
                    "hasMass": False,
                    "massMissingCount": 54321,
                    "access_token": "synthetic-access-secret",
                    "refresh_token": "synthetic-refresh-secret",
                    "client_secret": "synthetic-client-secret",
                    "documentId": "a" * 24,
                    "workspaceId": "b" * 24,
                    "elementId": "c" * 24,
                    "url": "https://private.invalid/?token=synthetic",
                }
            }
        }
    )
    text = json.dumps(report)
    assert report["massMissingCountCategory"] == "positive"
    for value in (
        "65432",
        "1.123",
        "87654",
        "54321",
        "private",
        "secret",
        "token",
        "https:",
        "a" * 24,
        "b" * 24,
        "c" * 24,
    ):
        assert value not in text
    assert len(json.dumps(report, separators=(",", ":"))) <= 4096


@pytest.mark.parametrize("environment", ["development", "production"])
def test_snapshot_emits_authorized_signs_only_in_development(
    harness: Harness,
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    harness.login()
    monkeypatch.setattr(harness.runtime.settings, "environment", environment)
    provider = CadProvider()
    provider.responses["mass"] = {
        "bodies": {
            "-all-": {
                "mass": [-1, -2, 1],
                "hasMass": False,
                "massMissingCount": 1,
            }
        }
    }
    with transport(harness, provider):
        response = fetch(harness)
    data = response.json()
    assert data["mass"]["code"] == "invalid_response"
    assert data["features"]["count"] == 2
    assert data["parts"]["count"] == 1 and data["bodies"]["count"] == 1
    assert data["has_mass"] is None
    assert {"massSigns", "hasMass", "massMissingCountCategory"}.isdisjoint(data)
    header = response.headers.get("X-Forge-Mass-Structure")
    if environment == "development":
        assert header
        report = json.loads(header)
        assert report["massSigns"] == {
            "position0": "negative",
            "position1": "negative",
            "position2": "positive",
        }
        assert report["hasMass"] is False
        assert report["massMissingCountCategory"] == "positive"
        assert len(header) <= 4096
    else:
        assert header is None


@pytest.mark.parametrize("values", [None, [0.0, -1.0, 1.0], [2.0, 1.0, 3.0]])
def test_false_mass_and_positive_missing_count_keep_snapshot_sections_valid(
    harness: Harness,
    values: JsonValue,
) -> None:
    harness.login()
    provider = CadProvider()
    provider.responses["mass"] = {
        "bodies": {
            "-all-": {
                "mass": values,
                "volume": [4.0, 3.0, 5.0],
                "hasMass": False,
                "massMissingCount": 2,
            }
        }
    }
    with transport(harness, provider):
        response = fetch(harness)
    data = response.json()
    assert all(
        data[name]["status"] == "success"
        for name in ("features", "parts", "bodies", "mass")
    )
    assert data["features"]["count"] == 2
    assert data["parts"]["count"] == 1 and data["bodies"]["count"] == 1
    assert data["has_mass"] is False
    assert response.headers.get("X-Forge-Mass-Structure") is None
