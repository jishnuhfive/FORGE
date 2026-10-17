"""Sanitized suppression evidence; synthetic CAD only and no inferred Booleans."""

import json
from copy import deepcopy
from typing import Any

import httpx2 as httpx
import pytest
from conftest import Harness
from sqlalchemy import select
from test_cad_read import REF
from test_safe_edit import (
    M0,
    Provider,
    approve,
    bodies,
    config,
    features,
    prepare,
    running,
)

from forge_api.cad_edits.domain import (
    ConfiguredSuppressionEvidence,
    EditError,
    FeatureStateEvidence,
    ParentSuppressionEvidence,
    SuppressionAuxEvidence,
)
from forge_api.db.models import WriteFence
from forge_api.integrations.onshape.dev.safe_edit import coverage, suppression_coverage
from forge_api.integrations.onshape.eligibility import (
    MISSING,
    EligibilityRejected,
    Reason,
)
from forge_api.integrations.onshape.write_evidence import project_write_evidence


def report(data: dict[str, Any]) -> dict[str, Any]:
    return suppression_coverage(data, coverage(data, M0, 100)).model_dump(mode="json")


@pytest.mark.parametrize(
    "raw,shape,kind",
    [
        (None, "null", None),
        (MISSING, "missing", None),
        ([], "other", None),
        ("private-synthetic-string", "other", None),
        (1, "other", None),
        (False, "other", None),
        ({}, "object", "unknown"),
        ({"btType": "BTMSuppressionState-1924"}, "object", "ordinary"),
        ({"btType": "BTMSuppressionStateConfigured-2598"}, "object", "configured"),
        ({"btType": "BTMSuppressionStateExpression-1811"}, "object", "expression"),
        ({"btType": "BTMSuppressionStateParentSuppressed-5404"}, "object", "parent"),
        ({"btType": "private-synthetic-type"}, "object", "unknown"),
    ],
)
def test_diagnostic_reports_fixed_shape_and_subtype_categories(
    raw: Any, shape: str, kind: str | None
) -> None:
    data = features()
    for feature in data["features"]:
        if raw is MISSING:
            del feature["suppressionState"]
        else:
            feature["suppressionState"] = raw
    result = report(data)
    assert [p["category"] for p in result["positions"]] == [
        "sketch",
        "extrude",
        "fillet",
    ]
    assert [p["position"] for p in result["positions"]] == [1, 2, 3]
    assert all(
        p["shape"] == shape and p["bt_type"] == kind for p in result["positions"]
    )
    encoded = json.dumps(result)
    assert "private-synthetic" not in encoded and "synthetic-feature-" not in encoded


@pytest.mark.parametrize(
    "raw,present,actual_type,value",
    [
        (MISSING, False, "missing", None),
        (None, True, "null", None),
        (False, True, "boolean", False),
        (True, True, "boolean", True),
        (0, True, "integer", None),
        ("false", True, "string", None),
        ([], True, "array", None),
    ],
)
def test_diagnostic_boolean_missing_null_and_false_are_distinct(
    raw: Any, present: bool, actual_type: str, value: bool | None
) -> None:
    data = features()
    for field in ("suppressed", "parentSuppressed", "suppressionConfigured"):
        if raw is MISSING:
            del data["features"][0][field]
        else:
            data["features"][0][field] = raw
    result = report(data)["positions"][0]
    for field in ("suppressed", "parent_suppressed", "suppression_configured"):
        assert result[field] == {
            "present": present,
            "actual_type": actual_type,
            "value": value,
        }


def test_suppression_diagnostic_is_limited_to_positions_one_through_three() -> None:
    data = features()
    data["features"].append(
        {
            "featureId": "private-synthetic-fourth",
            "featureType": "fillet",
            "suppressionState": {"btType": "private-synthetic-type"},
        }
    )
    assert len(report(data)["positions"]) == 3


@pytest.mark.parametrize("complete_states", [False, True])
@pytest.mark.parametrize("null_position", [None, 0, 1, 2])
def test_explicit_null_and_ordinary_modes_do_not_synthesize_state(
    complete_states: bool, null_position: int | None
) -> None:

    data = features()
    if not complete_states:
        data["featureStates"] = {}
    for index, feature in enumerate(data["features"]):
        if null_position is None or index == null_position:
            feature["suppressionState"] = None
    original = deepcopy(data)
    baseline = project_write_evidence(REF, M0, data, config(), bodies())
    assert baseline.suppression_aux_evidence == tuple(
        SuppressionAuxEvidence.NULL_UNAVAILABLE
        if null_position is None or i == null_position
        else SuppressionAuxEvidence.ORDINARY_OBJECT
        for i in range(3)
    )
    assert baseline.feature_state_evidence is (
        FeatureStateEvidence.COMPLETE
        if complete_states
        else FeatureStateEvidence.UNAVAILABLE_EMPTY
    )
    assert data == original
    assert not hasattr(baseline, "inactive")


@pytest.mark.parametrize("position", [0, 1, 2])
@pytest.mark.parametrize(
    "field", ["suppressed", "parentSuppressed", "suppressionConfigured"]
)
@pytest.mark.parametrize("value", [MISSING, None, True, 0, "false"])
def test_null_auxiliary_never_supplies_any_missing_or_unsafe_hard_boolean(
    position: int, field: str, value: Any
) -> None:

    data = features()
    feature = data["features"][position]
    feature["suppressionState"] = None
    if value is MISSING:
        del feature[field]
    else:
        feature[field] = value
    if value is MISSING and field != "suppressed":
        baseline = project_write_evidence(REF, M0, data, config(), bodies())
        if field == "parentSuppressed":
            assert baseline.parent_suppression_evidence[position] is (
                ParentSuppressionEvidence.STRUCTURALLY_NOT_APPLICABLE
            )
        else:
            assert baseline.configured_suppression_evidence[position] is (
                ConfiguredSuppressionEvidence.INDEPENDENTLY_PROVEN_UNCONFIGURED
            )
        assert field not in feature
        return
    with pytest.raises(EligibilityRejected) as caught:
        project_write_evidence(REF, M0, data, config(), bodies())
    assert (
        caught.value.diagnostic.reason
        == {
            "suppressed": Reason.SUPPRESSED,
            "parentSuppressed": Reason.PARENT,
            "suppressionConfigured": Reason.CONFIGURED_SUPPRESSION,
        }[field]
    )
    assert caught.value.diagnostic.position == position + 1


@pytest.mark.parametrize("position", [0, 1, 2])
@pytest.mark.parametrize(
    "raw",
    [
        MISSING,
        [],
        "synthetic-invalid",
        0,
        False,
        {},
        {"btType": "BTMSuppressionStateExpression-1811"},
        {"btType": "BTMSuppressionStateConfigured-2598"},
        {"btType": "BTMSuppressionStateParentSuppressed-5404"},
        {"btType": "synthetic-unknown"},
        {"btType": "BTMSuppressionState-1924"},
        {"btType": "BTMSuppressionState-1924", "suppressionConfigured": None},
        {"btType": "BTMSuppressionState-1924", "suppressionConfigured": 0},
        {"btType": "BTMSuppressionState-1924", "suppressionConfigured": True},
        {
            "btType": "BTMSuppressionState-1924",
            "suppressionConfigured": False,
            "unknown": False,
        },
    ],
)
def test_missing_malformed_specialized_or_unknown_auxiliary_rejects(
    position: int, raw: Any
) -> None:

    data = features()
    if raw is MISSING:
        del data["features"][position]["suppressionState"]
    else:
        data["features"][position]["suppressionState"] = raw
    with pytest.raises(EditError):
        project_write_evidence(REF, M0, data, config(), bodies())


def test_observed_missing_guards_require_independent_modes_without_synthesis() -> None:

    data = features()
    data["featureStates"] = {}
    for feature in data["features"]:
        feature["suppressionState"] = None
        del feature["parentSuppressed"]
        del feature["suppressionConfigured"]
    original = deepcopy(data)
    baseline = project_write_evidence(REF, M0, data, config(), bodies())
    assert (
        baseline.parent_suppression_evidence
        == (ParentSuppressionEvidence.STRUCTURALLY_NOT_APPLICABLE,) * 3
    )
    assert (
        baseline.configured_suppression_evidence
        == (ConfiguredSuppressionEvidence.INDEPENDENTLY_PROVEN_UNCONFIGURED,) * 3
    )
    assert data == original


@pytest.mark.parametrize(
    "after_kind", ["null", "ordinary", "expression", "configured", "parent", "unknown"]
)
def test_post_write_null_verifies_but_unexpected_auxiliary_change_stays_uncertain(
    harness: Harness, after_kind: str
) -> None:

    class ProviderWithNull(Provider):
        def __init__(self) -> None:
            super().__init__()
            for feature in self.data["features"]:
                feature["suppressionState"] = None

        def handle(self, request: httpx.Request) -> httpx.Response:
            response = super().handle(request)
            if request.method == "POST" and after_kind != "null":
                kinds = {
                    "ordinary": "BTMSuppressionState-1924",
                    "expression": "BTMSuppressionStateExpression-1811",
                    "configured": "BTMSuppressionStateConfigured-2598",
                    "parent": "BTMSuppressionStateParentSuppressed-5404",
                    "unknown": "synthetic-unknown",
                }
                self.data["features"][-1]["suppressionState"] = {
                    "btType": kinds[after_kind],
                    "suppressionConfigured": False,
                }
            return response

    fake = ProviderWithNull()
    with running(harness, fake):
        proposal = prepare(harness)
        result = approve(harness, proposal)
        assert result[-1]["state"] == (
            "verified_success" if after_kind == "null" else "execution_uncertain"
        )
        approve(harness, proposal)
    assert fake.writes == 1
    with harness.runtime.sessions() as db:
        assert (db.scalar(select(WriteFence)) is None) is (after_kind == "null")


def test_fresh_auxiliary_change_invalidates_approval_before_dispatch(
    harness: Harness,
) -> None:

    fake = Provider()
    for feature in fake.data["features"]:
        feature["suppressionState"] = None
    with running(harness, fake):
        proposal = prepare(harness)
        fake.data["features"][0]["suppressionState"] = features()["features"][0][
            "suppressionState"
        ]
        assert approve(harness, proposal)[-1]["code"] == "model_changed"
    assert fake.writes == 0


@pytest.mark.parametrize("case", ["old_policy", "missing_modes"])
def test_old_or_incomplete_auxiliary_evidence_record_cannot_execute(
    harness: Harness, case: str
) -> None:
    from forge_api.cad_edits.domain import fingerprint
    from forge_api.db.models import WriteRecord

    fake = Provider()
    with running(harness, fake):
        proposal = prepare(harness)
        with harness.runtime.sessions.begin() as db:
            row = db.get(WriteRecord, proposal["proposal_id"])
            assert row and row.payload
            raw = json.loads(row.payload)
            if case == "old_policy":
                raw["policy_version"] = "terminal-fillet-2"
            else:
                del raw["baseline"]["suppression_aux_evidence"]
            row.payload = json.dumps(raw)
            row.digest = fingerprint(raw)
            proposal["digest"] = row.digest
        assert approve(harness, proposal)[-1]["code"] == "proposal_tampered"
    assert fake.writes == 0
