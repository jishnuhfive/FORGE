"""Omitted guards require independent evidence; synthetic data only, no CAD writes."""

import ast
import inspect
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
    M1,
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
    ParentSuppressionEvidence,
    fingerprint,
)
from forge_api.db.models import WriteFence, WriteRecord
from forge_api.integrations.onshape.write_evidence import project_write_evidence


def omitted_features() -> dict[str, Any]:
    data = features()
    data["featureStates"] = {}
    for feature in data["features"]:
        feature["suppressionState"] = None
        del feature["parentSuppressed"]
        del feature["suppressionConfigured"]
    return data


@pytest.mark.parametrize("parent_present", [False, True])
@pytest.mark.parametrize("configured_present", [False, True])
@pytest.mark.parametrize("ordinary", [False, True])
@pytest.mark.parametrize("complete_states", [False, True])
def test_modes_preserve_omissions_and_bind_independent_evidence(
    parent_present: bool,
    configured_present: bool,
    ordinary: bool,
    complete_states: bool,
) -> None:
    data = omitted_features()
    for index, feature in enumerate(data["features"]):
        if parent_present:
            feature["parentSuppressed"] = False
        if configured_present:
            feature["suppressionConfigured"] = False
        if ordinary:
            feature["suppressionState"] = features()["features"][index][
                "suppressionState"
            ]
    if complete_states:
        data["featureStates"] = features()["featureStates"]
    original = deepcopy(data)
    baseline = project_write_evidence(REF, M0, data, config(), bodies())
    assert (
        baseline.parent_suppression_evidence
        == (
            ParentSuppressionEvidence.EXPLICIT_FALSE
            if parent_present
            else ParentSuppressionEvidence.STRUCTURALLY_NOT_APPLICABLE,
        )
        * 3
    )
    assert (
        baseline.configured_suppression_evidence
        == (
            ConfiguredSuppressionEvidence.EXPLICIT_FALSE
            if configured_present
            else ConfiguredSuppressionEvidence.INDEPENDENTLY_PROVEN_UNCONFIGURED,
        )
        * 3
    )
    assert data == original
    assert baseline.fingerprint == fingerprint([data, config()])
    assert not hasattr(baseline, "parentSuppressed")
    assert not hasattr(baseline, "suppressionConfigured")


@pytest.mark.parametrize("position", [0, 1, 2])
@pytest.mark.parametrize("field", ["parentSuppressed", "suppressionConfigured"])
@pytest.mark.parametrize("value", [True, None, 0, 1, "false", [], {}])
def test_present_conflict_is_never_overridden_by_other_safe_evidence(
    position: int, field: str, value: Any
) -> None:
    data = omitted_features()
    data["features"][position][field] = value
    with pytest.raises(EditError):
        project_write_evidence(REF, M0, data, config(), bodies())


@pytest.mark.parametrize(
    "case",
    [
        "subfeatures",
        "folder",
        "container",
        "custom",
        "namespace",
        "incomplete",
        "revision",
        "skew",
        "rollback",
        "missing_suppressed",
        "suppressed",
        "missing_auxiliary",
        "expression",
        "configured",
        "parent",
        "unknown_auxiliary",
        "missing_return",
        "extra_state",
    ],
)
def test_structural_parent_mode_requires_entire_supported_complete_inventory(
    case: str,
) -> None:
    data = omitted_features()
    first = data["features"][0]
    if case == "subfeatures":
        first["subFeatures"] = [features()["features"][0]]
    elif case in ("folder", "container", "custom"):
        extra = deepcopy(first)
        extra["featureId"] = "synthetic-extra"
        extra["featureType"] = case
        data["features"].insert(1, extra)
        data["rollbackIndex"] = len(data["features"])
    elif case == "namespace":
        first["namespace"] = "synthetic-custom"
    elif case == "incomplete":
        data["isComplete"] = False
    elif case == "revision":
        data["sourceMicroversion"] = M1
    elif case == "skew":
        data["microversionSkew"] = True
    elif case == "rollback":
        data["rollbackIndex"] = 2
    elif case == "missing_suppressed":
        del first["suppressed"]
    elif case == "suppressed":
        first["suppressed"] = True
    elif case == "missing_auxiliary":
        del first["suppressionState"]
    elif case in ("expression", "configured", "parent"):
        first["suppressionState"] = {
            "btType": {
                "expression": "BTMSuppressionStateExpression-1811",
                "configured": "BTMSuppressionStateConfigured-2598",
                "parent": "BTMSuppressionStateParentSuppressed-5404",
            }[case]
        }
    elif case == "unknown_auxiliary":
        first["suppressionState"] = {"btType": "synthetic-unknown"}
    elif case == "missing_return":
        del first["returnAfterSubfeatures"]
    else:
        data["featureStates"] = {
            "synthetic-extra": {"featureStatus": "OK", "inactive": False}
        }
    with pytest.raises(EditError):
        project_write_evidence(REF, M0, data, config(), bodies())


@pytest.mark.parametrize(
    "case",
    [
        "parameters",
        "current",
        "missing_parameters",
        "missing_current",
        "null_parameters",
        "null_current",
        "revision",
        "skew",
        "missing_skew",
        "missing_revision",
    ],
)
def test_omitted_configuration_guard_requires_exact_independent_endpoint_proof(
    case: str,
) -> None:
    cfg = config()
    if case == "parameters":
        cfg["configurationParameters"] = [{"synthetic": True}]
    elif case == "current":
        cfg["currentConfiguration"] = [{"synthetic": True}]
    elif case == "missing_parameters":
        del cfg["configurationParameters"]
    elif case == "missing_current":
        del cfg["currentConfiguration"]
    elif case == "null_parameters":
        cfg["configurationParameters"] = None
    elif case == "null_current":
        cfg["currentConfiguration"] = None
    elif case == "revision":
        cfg["sourceMicroversion"] = M1
    elif case == "skew":
        cfg["microversionSkew"] = True
    elif case == "missing_skew":
        del cfg["microversionSkew"]
    else:
        del cfg["sourceMicroversion"]
    with pytest.raises(EditError):
        project_write_evidence(REF, M0, omitted_features(), cfg, bodies())


class OmittedProvider(Provider):
    def __init__(self) -> None:
        super().__init__()
        self.data = omitted_features()


def test_full_omitted_mode_lifecycle_reproves_after_write(harness: Harness) -> None:
    fake = OmittedProvider()
    with running(harness, fake):
        proposal = prepare(harness)
        assert fake.writes == 0
        assert approve(harness, proposal)[-1]["state"] == "verified_success"
        approve(harness, proposal)
    assert fake.writes == 1
    for feature in fake.data["features"]:
        assert (
            "parentSuppressed" not in feature and "suppressionConfigured" not in feature
        )
    configurations = [r for r in fake.calls if r.url.path.endswith("/configuration")]
    assert (
        configurations[-1].method == "GET"
        and f"/m/{M1}/" in configurations[-1].url.path
    )
    with harness.runtime.sessions() as db:
        assert db.scalar(select(WriteFence)) is None


@pytest.mark.parametrize("field", ["parentSuppressed", "suppressionConfigured"])
def test_fresh_optional_field_presence_change_invalidates_approval(
    harness: Harness, field: str
) -> None:
    fake = OmittedProvider()
    with running(harness, fake):
        proposal = prepare(harness)
        fake.data["features"][0][field] = False
        assert approve(harness, proposal)[-1]["code"] == "model_changed"
    assert fake.writes == 0


@pytest.mark.parametrize(
    "case",
    [
        "parent_true",
        "configured_true",
        "parent_null",
        "configured_null",
        "parameters",
        "current",
        "revision",
        "skew",
        "subfeatures",
        "expression",
        "parent_appears_false",
        "configured_appears_false",
    ],
)
def test_post_write_unsafe_or_changed_guard_proof_stays_uncertain(
    harness: Harness, case: str
) -> None:
    class Changed(OmittedProvider):
        def handle(self, request: httpx.Request) -> httpx.Response:
            if self.marker == M1 and request.url.path.endswith("/configuration"):
                self.calls.append(request)
                cfg = config(M1)
                if case == "parameters":
                    cfg["configurationParameters"] = [{}]
                elif case == "current":
                    cfg["currentConfiguration"] = [{}]
                elif case == "revision":
                    cfg["sourceMicroversion"] = M0
                elif case == "skew":
                    cfg["microversionSkew"] = True
                return httpx.Response(200, json=cfg)
            response = super().handle(request)
            if request.method == "POST":
                feature = self.data["features"][-1]
                if case.startswith("parent_"):
                    feature["parentSuppressed"] = (
                        True
                        if case == "parent_true"
                        else None
                        if case == "parent_null"
                        else False
                    )
                elif case.startswith("configured_"):
                    feature["suppressionConfigured"] = (
                        True
                        if case == "configured_true"
                        else None
                        if case == "configured_null"
                        else False
                    )
                elif case == "subfeatures":
                    feature["subFeatures"] = [features()["features"][0]]
                elif case == "expression":
                    feature["suppressionState"] = {
                        "btType": "BTMSuppressionStateExpression-1811"
                    }
            return response

    fake = Changed()
    with running(harness, fake):
        proposal = prepare(harness)
        assert approve(harness, proposal)[-1]["state"] == "execution_uncertain"
        approve(harness, proposal)
    assert fake.writes == 1
    with harness.runtime.sessions() as db:
        assert db.scalar(select(WriteFence)) is not None


@pytest.mark.parametrize(
    "case", ["old_policy", "missing_parent_modes", "missing_configured_modes"]
)
def test_stored_guard_modes_and_policy_are_required(
    harness: Harness, case: str
) -> None:
    fake = OmittedProvider()
    with running(harness, fake):
        proposal = prepare(harness)
        with harness.runtime.sessions.begin() as db:
            row = db.get(WriteRecord, proposal["proposal_id"])
            assert row and row.payload
            raw = json.loads(row.payload)
            if case == "old_policy":
                raw["policy_version"] = "terminal-fillet-3"
            elif case == "missing_parent_modes":
                del raw["baseline"]["parent_suppression_evidence"]
            else:
                del raw["baseline"]["configured_suppression_evidence"]
            row.payload = json.dumps(raw)
            row.digest = fingerprint(raw)
            proposal["digest"] = row.digest
        assert approve(harness, proposal)[-1]["code"] == "proposal_tampered"
    assert fake.writes == 0


def test_critical_guard_reads_have_no_false_default() -> None:
    tree = ast.parse(inspect.getsource(project_write_evidence))
    guards = {"parentSuppressed", "suppressionConfigured"}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "get" or len(node.args) < 2:
            continue
        key, default = node.args[:2]
        if isinstance(key, ast.Constant) and key.value in guards:
            assert not (isinstance(default, ast.Constant) and default.value is False)
