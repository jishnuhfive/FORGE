"""Exact immutable body revision proof; synthetic providers, never live CAD."""

import ast
import inspect
import json
import logging
import textwrap
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
from test_safe_edit_guard_evidence import OmittedProvider

from forge_api.cad_edits.domain import BodyRevisionEvidence, EditError, fingerprint
from forge_api.core.config import Settings
from forge_api.db.models import WriteFence, WriteRecord
from forge_api.integrations.onshape.dev.safe_edit import CoverageClient, body_coverage
from forge_api.integrations.onshape.eligibility import MISSING
from forge_api.integrations.onshape.write_client import SafeEditClient
from forge_api.integrations.onshape.write_evidence import project_write_evidence


@pytest.mark.parametrize("field", ["ambiguous", "deleted"])
@pytest.mark.parametrize(
    "value,category",
    [
        (MISSING, "missing"),
        (False, "false"),
        (True, "true"),
        (None, "null"),
        (0, "wrong_type"),
        (1, "wrong_type"),
        ("private-synthetic-value", "wrong_type"),
        ([], "wrong_type"),
        ({"private-synthetic-key": True}, "wrong_type"),
    ],
)
def test_body_diagnostic_distinguishes_missing_false_and_malformed(
    field: str, value: Any, category: str
) -> None:
    data = bodies()
    if value is MISSING:
        del data["microversionId"][field]
    else:
        data["microversionId"][field] = value
    report = body_coverage(data, M0).model_dump()
    assert report[field] == category
    assert report["the_id"] == "present"
    assert report["the_id_matches_requested"] is True
    assert report["body_count"] == 1
    assert report["body_type"] == "SOLID"
    assert report["error_enum"] == "NO_ERROR"
    serialized = json.dumps(report)
    assert M0 not in serialized and "private-synthetic" not in serialized


@pytest.mark.parametrize("marker", [MISSING, None, [], "private-synthetic-marker", {}])
def test_body_diagnostic_never_echoes_bad_marker(marker: Any) -> None:
    data = bodies()
    if marker is MISSING:
        del data["microversionId"]
    else:
        data["microversionId"] = marker
    report = body_coverage(data, M0)
    assert report.the_id == "missing"
    assert not report.the_id_matches_requested
    assert report.ambiguous == report.deleted == "missing"
    assert "private-synthetic" not in report.model_dump_json()


def test_body_diagnostic_categories_never_echo_unknown_body_or_error() -> None:
    data = bodies()
    data["bodies"][0]["type"] = "private-synthetic-type"
    data["errorEnum"] = "private-synthetic-error"
    data["microversionId"]["theId"] = "private-synthetic-revision"
    report = body_coverage(data, M0)
    assert report.body_type == report.error_enum == "other"
    assert report.the_id == "present" and not report.the_id_matches_requested
    assert "private-synthetic" not in report.model_dump_json()


@pytest.mark.parametrize("head_changed", [False, True])
def test_body_diagnostic_only_after_head_bracketing_and_never_private_values(
    head_changed: bool, caplog: pytest.LogCaptureFixture
) -> None:
    fake = Provider()
    heads = 0

    def read(request: httpx.Request) -> httpx.Response:
        nonlocal heads
        assert request.method == "GET"
        if request.url.path.endswith("/currentmicroversion"):
            heads += 1
            return httpx.Response(
                200, json={"microversion": M1 if heads == 2 and head_changed else M0}
            )
        return fake.handle(request)

    with (
        httpx.Client(transport=httpx.MockTransport(read)) as transport,
        caplog.at_level(logging.WARNING, logger="forge.onshape.safe_edit"),
    ):
        client = CoverageClient(Settings(_env_file=None), transport, "synthetic-token")
        if head_changed:
            with pytest.raises(EditError, match="model_changed"):
                client.evidence(REF)
        else:
            client.evidence(REF)
    reports = [
        json.loads(r.message.split("metadata=")[1])
        for r in caplog.records
        if r.message.startswith("safe_edit_body_coverage ")
    ]
    assert len(reports) == int(not head_changed)
    if reports:
        assert reports[0]["the_id_matches_requested"] is True
    for private in (
        M0,
        M1,
        REF.documentId,
        "synthetic-body",
        "synthetic-token",
        "https://",
    ):
        assert private not in caplog.text


@pytest.mark.parametrize("explicit_flags", [False, True])
@pytest.mark.parametrize("after", [False, True])
def test_body_modes_preserve_provider_omissions_and_exact_new_revision(
    explicit_flags: bool, after: bool
) -> None:
    marker = M1 if after else M0
    data = features()
    data["sourceMicroversion"] = marker
    if after:
        data["features"][-1]["suppressed"] = True
        data["featureStates"]["synthetic-feature-2"]["inactive"] = True
    body = bodies(marker, explicit_flags=explicit_flags)
    original = deepcopy(body)
    baseline = project_write_evidence(
        REF,
        marker,
        data,
        config(marker),
        body,
        after=after,
        pinned_body_microversion=marker,
    )
    assert baseline.body_revision_evidence == (
        BodyRevisionEvidence.EXPLICIT_CLEAN_FLAGS
        if explicit_flags
        else BodyRevisionEvidence.EXACT_PINNED_ID_FLAGS_UNAVAILABLE
    )
    assert baseline.microversion == marker and baseline.suppressed is after
    assert body == original
    assert ("ambiguous" in body["microversionId"]) is explicit_flags
    assert ("deleted" in body["microversionId"]) is explicit_flags
    assert "ambiguous" not in baseline.model_dump_json()
    assert "deleted" not in baseline.model_dump_json()


@pytest.mark.parametrize("pin", [None, M1, "", True])
def test_unavailable_flags_need_transport_proof_not_just_matching_response_id(
    pin: Any,
) -> None:
    with pytest.raises(EditError):
        project_write_evidence(
            REF,
            M0,
            features(),
            config(),
            bodies(explicit_flags=False),
            pinned_body_microversion=pin,
        )


@pytest.mark.parametrize("field", ["ambiguous", "deleted"])
@pytest.mark.parametrize("other", [False, MISSING])
@pytest.mark.parametrize("value", [True, None, 0, 1, 0.0, "false", [], {}])
def test_negative_or_malformed_flags_reject_even_with_exact_pinned_id(
    field: str, other: Any, value: Any
) -> None:
    body = bodies()
    body["microversionId"][field] = value
    other_field = "deleted" if field == "ambiguous" else "ambiguous"
    if other is MISSING:
        del body["microversionId"][other_field]
    else:
        body["microversionId"][other_field] = other
    with pytest.raises(EditError):
        project_write_evidence(
            REF, M0, features(), config(), body, pinned_body_microversion=M0
        )


INVALID_BODY_CASES = [
    "missing_marker",
    "null_marker",
    "array_marker",
    "scalar_marker",
    "missing_id",
    "null_id",
    "bool_id",
    "array_id",
    "empty_id",
    "mismatched_id",
    "ambiguous_true",
    "deleted_true",
    "ambiguous_null",
    "deleted_null",
    "ambiguous_wrong_type",
    "deleted_wrong_type",
    "mixed_ambiguous",
    "mixed_deleted",
    "no_body",
    "multiple_bodies",
    "non_solid",
    "missing_type",
    "body_error",
    "missing_error",
]


def change_body(data: dict[str, Any], case: str) -> None:
    marker = data["microversionId"]
    if case == "missing_marker":
        del data["microversionId"]
    elif case.endswith("_marker"):
        data["microversionId"] = {
            "null_marker": None,
            "array_marker": [],
            "scalar_marker": "private-synthetic-marker",
        }[case]
    elif case == "missing_id":
        del marker["theId"]
    elif case.endswith("_id"):
        marker["theId"] = {
            "null_id": None,
            "bool_id": True,
            "array_id": [],
            "empty_id": "",
            "mismatched_id": "f" * 24,
        }[case]
    elif case.startswith(("ambiguous_", "deleted_")):
        field, shape = case.split("_", 1)
        marker[field] = {"true": True, "null": None, "wrong_type": "false"}[shape]
    elif case.startswith("mixed_"):
        marker[case.removeprefix("mixed_")] = False
    elif case == "no_body":
        data["bodies"] = []
    elif case == "multiple_bodies":
        data["bodies"].append({"id": "synthetic-second-body", "type": "SOLID"})
    elif case == "non_solid":
        data["bodies"][0]["type"] = "SURFACE"
    elif case == "missing_type":
        del data["bodies"][0]["type"]
    elif case == "body_error":
        data["errorEnum"] = "UNKNOWN"
    elif case == "missing_error":
        del data["errorEnum"]
    else:
        raise AssertionError("unknown synthetic case")


@pytest.mark.parametrize("case", INVALID_BODY_CASES)
@pytest.mark.parametrize("after", [False, True])
def test_missing_flags_never_bypass_marker_body_or_error_invariants(
    case: str, after: bool
) -> None:
    marker = M1 if after else M0
    body = bodies(marker, explicit_flags=False)
    change_body(body, case)
    data = features()
    data["sourceMicroversion"] = marker
    data["featureStates"] = {}
    data["features"][-1]["suppressed"] = after
    with pytest.raises(EditError):
        project_write_evidence(
            REF,
            marker,
            data,
            config(marker),
            body,
            after=after,
            pinned_body_microversion=marker,
        )


class BodyProvider(OmittedProvider):
    def __init__(self) -> None:
        super().__init__()
        self.explicit_before = False
        self.explicit_after = False
        self.before_case = ""
        self.after_case = ""

    def handle(self, request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/bodydetails"):
            self.calls.append(request)
            assert request.method == "GET" and f"/m/{self.marker}/" in request.url.path
            after = self.marker == M1
            data = bodies(
                self.marker,
                explicit_flags=self.explicit_after if after else self.explicit_before,
            )
            case = self.after_case if after else self.before_case
            if case:
                change_body(data, case)
            return httpx.Response(200, json=data)
        return super().handle(request)


@pytest.mark.parametrize("before", [False, True])
@pytest.mark.parametrize("after", [False, True])
def test_mock_lifecycle_reproves_body_mode_at_exact_acknowledged_new_revision(
    harness: Harness, before: bool, after: bool
) -> None:
    fake = BodyProvider()
    fake.explicit_before, fake.explicit_after = before, after
    with running(harness, fake):
        proposal = prepare(harness)
        with harness.runtime.sessions() as db:
            row = db.get(WriteRecord, proposal["proposal_id"])
            assert row and row.payload
            raw = json.loads(row.payload)
            expected = (
                "EXPLICIT_CLEAN_FLAGS"
                if before
                else "EXACT_PINNED_ID_FLAGS_UNAVAILABLE"
            )
            assert raw["baseline"]["body_revision_evidence"] == expected
            assert "synthetic-body" not in row.payload
            changed = deepcopy(raw)
            changed["baseline"]["body_revision_evidence"] = "INVALID"
            assert fingerprint(changed) != proposal["digest"]
        assert approve(harness, proposal)[-1]["state"] == "verified_success"
        approve(harness, proposal)
    assert fake.writes == 1
    with harness.runtime.sessions() as db:
        assert db.scalar(select(WriteFence)) is None
    reads = [
        r
        for r in fake.calls
        if r.method == "GET" and not r.url.path.endswith("/currentmicroversion")
    ]
    assert all(f"/m/{M1}/" in r.url.path for r in reads[-3:])


def test_fresh_body_mode_change_invalidates_approval_without_dispatch(
    harness: Harness,
) -> None:
    fake = BodyProvider()
    with running(harness, fake):
        proposal = prepare(harness)
        fake.explicit_before = True
        assert approve(harness, proposal)[-1]["code"] == "model_changed"
    assert fake.writes == 0


@pytest.mark.parametrize("case", INVALID_BODY_CASES)
def test_post_write_invalid_body_evidence_retains_fence_and_never_retries(
    harness: Harness, case: str
) -> None:
    fake = BodyProvider()
    fake.after_case = case
    with running(harness, fake):
        proposal = prepare(harness)
        assert approve(harness, proposal)[-1]["state"] == "execution_uncertain"
        approve(harness, proposal)
    assert fake.writes == 1
    with harness.runtime.sessions() as db:
        assert db.scalar(select(WriteFence)) is not None


@pytest.mark.parametrize("case", ["old_policy", "missing_mode", "invalid_mode"])
def test_old_or_missing_body_policy_cannot_dispatch(
    harness: Harness, case: str
) -> None:
    fake = BodyProvider()
    with running(harness, fake):
        proposal = prepare(harness)
        with harness.runtime.sessions.begin() as db:
            row = db.get(WriteRecord, proposal["proposal_id"])
            assert row and row.payload
            raw = json.loads(row.payload)
            if case == "old_policy":
                raw["policy_version"] = "terminal-fillet-4"
            elif case == "missing_mode":
                del raw["baseline"]["body_revision_evidence"]
            else:
                raw["baseline"]["body_revision_evidence"] = "INVALID"
            row.payload = json.dumps(raw)
            row.digest = fingerprint(raw)
            proposal["digest"] = row.digest
        assert approve(harness, proposal)[-1]["code"] == "proposal_tampered"
    assert fake.writes == 0


@pytest.mark.parametrize("case", INVALID_BODY_CASES)
def test_fresh_invalid_body_read_never_dispatches(harness: Harness, case: str) -> None:
    fake = BodyProvider()
    with running(harness, fake):
        proposal = prepare(harness)
        fake.before_case = case
        assert approve(harness, proposal)[-1].get("state") != "verified_success"
    assert fake.writes == 0


def test_unavailable_body_mode_comes_from_fixed_pinned_reads_and_equal_heads() -> None:
    fake = BodyProvider()
    with httpx.Client(transport=httpx.MockTransport(fake.handle)) as transport:
        result = SafeEditClient(
            Settings(_env_file=None), transport, "synthetic-token"
        ).evidence(REF)
    assert (
        result.body_revision_evidence
        == BodyRevisionEvidence.EXACT_PINNED_ID_FLAGS_UNAVAILABLE
    )
    assert [r.url.path.rsplit("/", 1)[-1] for r in fake.calls] == [
        "currentmicroversion",
        "features",
        "configuration",
        "bodydetails",
        "currentmicroversion",
    ]
    assert all(r.method == "GET" for r in fake.calls)
    assert all(f"/m/{M0}/" in r.url.path for r in fake.calls[1:4])
    assert dict(fake.calls[3].url.params) == {"includeGeometricData": "false"}


def test_body_flags_have_no_false_default_or_normalization() -> None:
    for function in (project_write_evidence, SafeEditClient.evidence):
        tree = ast.parse(textwrap.dedent(inspect.getsource(function)))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and node.args[0].value in {"ambiguous", "deleted"}
            ):
                assert len(node.args) == 2
                assert (
                    isinstance(node.args[1], ast.Name) and node.args[1].id == "MISSING"
                )
