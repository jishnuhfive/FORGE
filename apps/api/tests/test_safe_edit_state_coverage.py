"""Synthetic state-map coverage; no private provider data or inferred states."""

import json
import logging

import httpx2 as httpx
import pytest
from test_cad_read import REF
from test_safe_edit import M0, M1, Provider, bodies, config, features

from forge_api.cad_edits.domain import EditError
from forge_api.core.config import Settings
from forge_api.integrations.onshape.client import MAX_BYTES
from forge_api.integrations.onshape.dev.safe_edit import CoverageClient, coverage
from forge_api.integrations.onshape.eligibility import EligibilityRejected, Reason
from forge_api.integrations.onshape.write_evidence import project_write_evidence


@pytest.mark.parametrize("position", [0, 1, 2])
@pytest.mark.parametrize("unmatched", [False, True])
def test_missing_state_exact_position_still_rejects(
    position: int, unmatched: bool
) -> None:
    data = features()
    del data["featureStates"][f"synthetic-feature-{position}"]
    if unmatched:
        data["featureStates"]["synthetic-unmatched"] = {
            "featureStatus": "OK",
            "inactive": False,
        }
    report = coverage(data, M0, 100)
    assert report.states == 2 + int(unmatched)
    assert report.unmatched_state_count == int(unmatched)
    assert [p.state_present for p in report.positions] == [
        i != position for i in range(3)
    ]
    with pytest.raises(EligibilityRejected) as caught:
        project_write_evidence(REF, M0, data, config(), bodies())
    assert caught.value.diagnostic.reason == Reason.STATE_COVERAGE
    assert caught.value.diagnostic.position is None


@pytest.mark.parametrize("extra", [False, True])
def test_complete_state_coverage_and_extra_state_count(extra: bool) -> None:
    data = features()
    if extra:
        data["featureStates"]["synthetic-unmatched"] = {
            "featureStatus": "OK",
            "inactive": False,
        }
    report = coverage(data, M0, 100)
    assert report.features == 3 and report.states == 3 + int(extra)
    assert report.unmatched_state_count == int(extra)
    assert [p.category for p in report.positions] == ["sketch", "extrude", "fillet"]
    assert all(p.state_present for p in report.positions)
    assert report.source_matches and report.is_complete is True
    if extra:
        with pytest.raises(EligibilityRejected) as caught:
            project_write_evidence(REF, M0, data, config(), bodies())
        assert caught.value.diagnostic.reason == Reason.STATE_COVERAGE
    else:
        project_write_evidence(REF, M0, data, config(), bodies())


@pytest.mark.parametrize("position", [0, 1, 2])
@pytest.mark.parametrize(
    "change", ["invalid", "missing_status", "missing_inactive", "error", "inactive"]
)
def test_no_state_policy_reduction(position: int, change: str) -> None:
    data = features()
    identity = f"synthetic-feature-{position}"
    state = data["featureStates"][identity]
    expected = Reason.STATE
    if change == "invalid":
        data["featureStates"][identity] = None
    elif change == "missing_status":
        del state["featureStatus"]
        expected = Reason.STATUS
    elif change == "missing_inactive":
        del state["inactive"]
        expected = Reason.INACTIVE
    elif change == "error":
        state["featureStatus"] = "ERROR"
        expected = Reason.STATUS
    else:
        state["inactive"] = True
        expected = Reason.INACTIVE
    # Exact-key presence does not claim validity or eligibility.
    assert coverage(data, M0, 100).positions[position].state_present
    with pytest.raises(EligibilityRejected) as caught:
        project_write_evidence(REF, M0, data, config(), bodies())
    assert caught.value.diagnostic.reason == expected
    assert caught.value.diagnostic.position == position + 1


def test_comparison_fixed_pinned_gets_byte_counts_and_private_log_boundary(
    caplog: pytest.LogCaptureFixture,
) -> None:
    provider = Provider()
    sizes: list[int] = []

    def read(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.host == "cad.onshape.com"
        assert request.url.path.startswith("/api/v17/")
        if request.url.path.endswith("/features"):
            assert f"/m/{M0}/" in request.url.path
            assert dict(request.url.params) == {
                "includeGeometryIds": "false",
                "noSketchGeometry": "true" if not sizes else "false",
                "rollbackBarIndex": "-1",
            }
            data = features()
            data["features"][0]["name"] = "private-synthetic-name"
            data["features"][0]["featureType"] = "private-synthetic-type"
            if not sizes:
                del data["featureStates"]["synthetic-feature-0"]
            payload = json.dumps(data).encode()
            sizes.append(len(payload))
            return httpx.Response(
                200, content=payload, headers={"content-type": "application/json"}
            )
        return provider.handle(request)

    settings = Settings(_env_file=None)
    assert not settings.forge_cad_writes_enabled
    with (
        httpx.Client(transport=httpx.MockTransport(read)) as transport,
        caplog.at_level(logging.WARNING),
    ):
        CoverageClient(settings, transport, "private-synthetic-token").compare(REF)
    reports = [json.loads(r.message.split("metadata=")[1]) for r in caplog.records]
    assert len(reports) == 2
    assert [r["response_bytes"] for r in reports] == sizes
    assert reports[0]["positions"][0]["state_present"] is False
    assert reports[1]["positions"][0]["state_present"] is True
    assert reports[0]["positions"][0]["category"] == "unsupported"
    for private in (
        "private-synthetic",
        "synthetic-feature",
        M0,
        REF.documentId,
        "https://",
    ):
        assert private not in caplog.text


@pytest.mark.parametrize("mode", ["declared", "streamed", "redirect", "revision"])
def test_comparison_caps_redirect_and_changing_head_fail_without_reports(
    mode: str, caplog: pytest.LogCaptureFixture
) -> None:
    provider = Provider()
    heads = 0

    def read(request: httpx.Request) -> httpx.Response:
        nonlocal heads
        assert request.method == "GET"
        if request.url.path.endswith("/currentmicroversion"):
            heads += 1
            return httpx.Response(200, json={"microversion": M1 if heads == 2 else M0})
        if mode == "declared":
            return httpx.Response(
                200,
                content=b"{}",
                headers={
                    "content-type": "application/json",
                    "content-length": str(MAX_BYTES + 1),
                },
            )
        if mode == "streamed":
            return httpx.Response(
                200,
                content=b" " * (MAX_BYTES + 1),
                headers={"content-type": "application/json"},
            )
        if mode == "redirect":
            return httpx.Response(
                302, headers={"location": "https://example.com/private"}
            )
        return provider.handle(request)

    with (
        httpx.Client(transport=httpx.MockTransport(read)) as transport,
        caplog.at_level(logging.WARNING),
        pytest.raises(EditError),
    ):
        CoverageClient(Settings(_env_file=None), transport, "synthetic-token").compare(
            REF
        )
    assert not caplog.records
