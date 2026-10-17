"""Explicit unavailable evidence for the sole suppression operation; synthetic only."""

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

from forge_api.cad_edits.domain import EditError, FeatureStateEvidence, fingerprint
from forge_api.core.config import Settings
from forge_api.db.models import WriteFence, WriteRecord
from forge_api.integrations.onshape.eligibility import (
    MISSING,
    EligibilityRejected,
    Reason,
)
from forge_api.integrations.onshape.write_client import SafeEditClient
from forge_api.integrations.onshape.write_evidence import project_write_evidence


def empty_features() -> dict[str, Any]:
    data = features()
    data["featureStates"] = {}
    return data


@pytest.mark.parametrize("complete", [False, True])
def test_explicit_modes_bind_raw_inventory_without_inventing_state(
    complete: bool,
) -> None:
    data = features() if complete else empty_features()
    original = deepcopy(data)
    baseline = project_write_evidence(REF, M0, data, config(), bodies())
    assert baseline.feature_state_evidence is (
        FeatureStateEvidence.COMPLETE
        if complete
        else FeatureStateEvidence.UNAVAILABLE_EMPTY
    )
    assert baseline.fingerprint == fingerprint([data, config()])
    assert data == original
    assert not hasattr(baseline, "featureStatus") and not hasattr(baseline, "inactive")
    other = project_write_evidence(
        REF, M0, empty_features() if complete else features(), config(), bodies()
    )
    assert baseline != other and baseline.fingerprint != other.fingerprint
    assert baseline.definitions == other.definitions


@pytest.mark.parametrize(
    "value",
    [
        MISSING,
        None,
        [],
        "",
        False,
        0,
        {"wrong-key": {"featureStatus": "OK", "inactive": False}},
    ],
)
def test_missing_null_malformed_wrong_map_rejects(value: Any) -> None:
    data = empty_features()
    if value is MISSING:
        del data["featureStates"]
    else:
        data["featureStates"] = value
    with pytest.raises(EligibilityRejected) as caught:
        project_write_evidence(REF, M0, data, config(), bodies())
    assert caught.value.diagnostic.reason in (Reason.STATES, Reason.STATE_COVERAGE)


@pytest.mark.parametrize(
    "case",
    [
        "target_missing",
        "target_suppressed",
        "no_body",
        "multiple_bodies",
        "body_revision",
        "namespace",
        "nonterminal",
        "configured",
        "incomplete",
        "source_revision",
        "skew",
        "rollback",
        "count",
        "duplicate_id",
        "unbounded_id",
        "custom",
        "bt_type",
        "subfeatures",
        "parent",
        "configured_suppression",
        "dynamic_suppression",
        "suppression_fields",
        "return",
        "body_type",
        "body_error",
        "body_ambiguous",
        "body_deleted",
        "config_revision",
        "serialization",
        "library",
    ],
)
def test_empty_map_never_bypasses_other_hard_invariants(case: str) -> None:
    data, cfg, body = empty_features(), config(), bodies()
    target = data["features"][-1]
    if case == "target_missing":
        del target["suppressed"]
    elif case == "target_suppressed":
        target["suppressed"] = True
    elif case == "no_body":
        body["bodies"] = []
    elif case == "multiple_bodies":
        body["bodies"].append({"id": "synthetic-second", "type": "SOLID"})
    elif case == "body_revision":
        body["microversionId"]["theId"] = M1
    elif case == "namespace":
        target["namespace"] = "synthetic-custom"
    elif case == "nonterminal":
        data["features"].reverse()
    elif case == "configured":
        cfg["configurationParameters"] = [{}]
    elif case == "incomplete":
        data["isComplete"] = False
    elif case == "source_revision":
        data["sourceMicroversion"] = M1
    elif case == "skew":
        data["microversionSkew"] = True
    elif case == "rollback":
        data["rollbackIndex"] = 2
    elif case == "count":
        data["features"].pop(0)
    elif case == "duplicate_id":
        target["featureId"] = data["features"][0]["featureId"]
    elif case == "unbounded_id":
        target["featureId"] = "x" * 257
    elif case == "custom":
        target["featureType"] = "synthetic-custom"
    elif case == "bt_type":
        target["btType"] = "synthetic-custom"
    elif case == "subfeatures":
        target["subFeatures"] = [{}]
    elif case == "parent":
        target["parentSuppressed"] = True
    elif case == "configured_suppression":
        target["suppressionConfigured"] = True
    elif case == "dynamic_suppression":
        target["suppressionState"]["btType"] = "BTMSuppressionStateExpression-1811"
    elif case == "suppression_fields":
        target["suppressionState"]["unknown"] = False
    elif case == "return":
        target["returnAfterSubfeatures"] = True
    elif case == "body_type":
        body["bodies"][0]["type"] = "SHEET"
    elif case == "body_error":
        body["errorEnum"] = "UNKNOWN"
    elif case == "body_ambiguous":
        body["microversionId"]["ambiguous"] = True
    elif case == "body_deleted":
        body["microversionId"]["deleted"] = True
    elif case == "config_revision":
        cfg["sourceMicroversion"] = M1
    elif case == "serialization":
        data["serializationVersion"] = None
    elif case == "library":
        data["libraryVersion"] = True
    with pytest.raises(EditError):
        project_write_evidence(REF, M0, data, cfg, body)


@pytest.mark.parametrize("position", [0, 1, 2])
@pytest.mark.parametrize("value", [MISSING, None, True, 0, "false"])
def test_empty_mode_requires_every_explicit_unsuppressed_field(
    position: int, value: Any
) -> None:
    data = empty_features()
    if value is MISSING:
        del data["features"][position]["suppressed"]
    else:
        data["features"][position]["suppressed"] = value
    with pytest.raises(EligibilityRejected) as caught:
        project_write_evidence(REF, M0, data, config(), bodies())
    assert caught.value.diagnostic.reason == Reason.SUPPRESSED
    assert caught.value.diagnostic.position == position + 1


@pytest.mark.parametrize(
    "complete_before,complete_after",
    [(False, False), (False, True), (True, False), (True, True)],
)
def test_verified_mock_dispatch_in_both_modes(
    harness: Harness, complete_before: bool, complete_after: bool
) -> None:
    class ChangingProvider(Provider):
        def handle(self, request: httpx.Request) -> httpx.Response:
            response = super().handle(request)
            if request.method == "POST":
                self.data["featureStates"] = (
                    features()["featureStates"] if complete_after else {}
                )
                if complete_after:
                    self.data["featureStates"]["synthetic-feature-2"]["inactive"] = True
            return response

    fake = ChangingProvider()
    if complete_before:
        fake.data["featureStates"] = features()["featureStates"]
    with running(harness, fake):
        proposal = prepare(harness)
        assert fake.writes == 0
        result = approve(harness, proposal)
    assert result[-1] == {"type": "result", "state": "verified_success"}
    assert fake.writes == 1
    assert fake.calls[-5].method == "GET"


@pytest.mark.parametrize(
    "case", ["mode", "definition", "identity", "suppressed", "head", "configuration"]
)
def test_empty_approval_fresh_read_changes_reject_without_dispatch(
    harness: Harness, case: str
) -> None:
    changed_configuration = False

    class FreshProvider(Provider):
        def handle(self, request: httpx.Request) -> httpx.Response:
            if changed_configuration and request.url.path.endswith("/configuration"):
                self.calls.append(request)
                data = config(self.marker)
                data["currentConfiguration"] = [{"synthetic": True}]
                return httpx.Response(200, json=data)
            return super().handle(request)

    fake = FreshProvider()
    with running(harness, fake):
        proposal = prepare(harness)
        if case == "mode":
            fake.data["featureStates"] = features()["featureStates"]
        elif case == "definition":
            fake.data["features"][0]["parameters"] = [{"synthetic": True}]
        elif case == "identity":
            fake.data["features"][-1]["featureId"] = "synthetic-replaced"
        elif case == "suppressed":
            fake.data["features"][-1]["suppressed"] = True
        elif case == "head":
            fake.marker = M1
            fake.data["sourceMicroversion"] = M1
        else:
            changed_configuration = True
        result = approve(harness, proposal)
    assert result[-1].get("state") != "verified_success"
    assert fake.writes == 0


@pytest.mark.parametrize(
    "case",
    [
        "suppressed",
        "identity",
        "order",
        "definition",
        "library",
        "serialization",
        "partial",
        "error",
        "inactive",
        "missing_inactive",
        "body",
    ],
)
def test_empty_mode_post_write_mismatch_never_verified_or_retried(
    harness: Harness, case: str
) -> None:
    class InvalidAfter(Provider):
        def handle(self, request: httpx.Request) -> httpx.Response:
            if (
                self.marker == M1
                and request.url.path.endswith("/bodydetails")
                and case == "body"
            ):
                self.calls.append(request)
                data = bodies(M1)
                data["bodies"] = []
                return httpx.Response(200, json=data)
            response = super().handle(request)
            if request.method == "POST":
                target = self.data["features"][-1]
                if case == "suppressed":
                    target["suppressed"] = False
                elif case == "identity":
                    target["featureId"] = "synthetic-replaced"
                elif case == "order":
                    self.data["features"][0:2] = reversed(self.data["features"][0:2])
                elif case == "definition":
                    self.data["features"][0]["parameters"] = [{"synthetic": True}]
                elif case == "library":
                    self.data["libraryVersion"] += 1
                elif case == "serialization":
                    self.data["serializationVersion"] = "synthetic-new"
                elif case in ("partial", "error", "inactive", "missing_inactive"):
                    self.data["featureStates"] = features()["featureStates"]
                    self.data["featureStates"]["synthetic-feature-2"]["inactive"] = True
                    if case == "partial":
                        del self.data["featureStates"]["synthetic-feature-0"]
                    elif case == "error":
                        self.data["featureStates"]["synthetic-feature-0"][
                            "featureStatus"
                        ] = "ERROR"
                    elif case == "inactive":
                        self.data["featureStates"]["synthetic-feature-0"][
                            "inactive"
                        ] = True
                    else:
                        del self.data["featureStates"]["synthetic-feature-0"][
                            "inactive"
                        ]
            return response

    fake = InvalidAfter()
    with running(harness, fake):
        proposal = prepare(harness)
        assert approve(harness, proposal)[-1]["state"] == "execution_uncertain"
        approve(harness, proposal)
    assert fake.writes == 1
    with harness.runtime.sessions() as db:
        assert db.scalar(select(WriteFence)) is not None


def test_old_policy_record_cannot_execute(harness: Harness) -> None:
    import json

    fake = Provider()
    with running(harness, fake):
        proposal = prepare(harness)
        with harness.runtime.sessions.begin() as db:
            row = db.get(WriteRecord, proposal["proposal_id"])
            assert row and row.payload
            raw = json.loads(row.payload)
            raw["policy_version"] = "terminal-fillet-1"
            row.payload = json.dumps(raw)
            row.digest = fingerprint(raw)
            proposal["digest"] = row.digest
        assert approve(harness, proposal)[-1]["code"] == "proposal_tampered"
    assert fake.writes == 0


def test_duplicate_provider_state_key_rejects_before_projection() -> None:
    fake = Provider()

    def read(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        if request.url.path.endswith("/features"):
            return httpx.Response(
                200,
                content=b'{"featureStates":{"synthetic-feature-0":{},"synthetic-feature-0":{}}}',
                headers={"content-type": "application/json"},
            )
        return fake.handle(request)

    with (
        httpx.Client(transport=httpx.MockTransport(read)) as transport,
        pytest.raises(EditError),
    ):
        SafeEditClient(Settings(_env_file=None), transport, "synthetic-token").evidence(
            REF
        )
