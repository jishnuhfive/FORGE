"""Check my step endpoint over invented provider data; no live Onshape."""

from copy import deepcopy
from typing import Any

import httpx2 as httpx
import pytest
from conftest import Harness
from test_cad_read import (
    BODIES,
    FEATURES,
    REF,
    VERSION,
    CadProvider,
    set_scope,
    transport,
)

PATH = "/api/learning/check-step"


def body(**overrides: object) -> dict[str, Any]:
    return {
        "lesson_id": "mounting-bracket",
        "step_id": "base-solid",
        "context": REF.model_dump(),
        **overrides,
    }


def post(
    harness: Harness,
    payload: object | None = None,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    return harness.client.post(
        PATH,
        json=body() if payload is None else payload,
        headers=headers or harness.headers(),
    )


def statuses(data: dict[str, Any]) -> dict[str, str]:
    return {r["requirement_id"]: r["outcome"]["status"] for r in data["results"]}


def test_signed_out_is_refused(harness: Harness) -> None:
    assert harness.client.post(PATH, json=body()).status_code == 401
    assert not harness.provider.calls


@pytest.mark.parametrize("case", ["csrf", "origin", "cross_site", "no_csrf"])
def test_csrf_and_origin_are_required(harness: Harness, case: str) -> None:
    harness.login()
    headers = harness.headers()
    if case == "csrf":
        headers["X-CSRF-Token"] = "0" * 64
    if case == "no_csrf":
        del headers["X-CSRF-Token"]
    if case == "origin":
        headers["Origin"] = "https://cad.onshape.com"
    if case == "cross_site":
        headers["Sec-Fetch-Site"] = "cross-site"
    provider = CadProvider()
    with transport(harness, provider):
        assert post(harness, headers=headers).status_code == 403
    assert not provider.calls


@pytest.mark.parametrize(
    "payload",
    [
        body(lesson_id="other"),
        body(step_id="no-such-step"),
        body(step_id="x" * 5000),
        body(extra="field"),
        {**body(), "context": {**REF.model_dump(), "documentId": "short"}},
        {**body(), "context": {**REF.model_dump(), "revisionKind": "version"}},
        {"lesson_id": "mounting-bracket", "step_id": "base-solid"},
        [],
    ],
)
def test_invalid_requests_make_no_cad_read_and_echo_nothing(
    harness: Harness, payload: object
) -> None:
    harness.login()
    provider = CadProvider()
    with transport(harness, provider):
        result = post(harness, payload)
    assert result.status_code in (400, 413)
    assert not provider.calls
    assert REF.documentId not in result.text


def test_pass_uses_fresh_read_only_evidence_and_leaks_nothing(
    harness: Harness,
) -> None:
    harness.login()
    provider = CadProvider()
    with transport(harness, provider):
        result = post(harness)
    assert result.status_code == 200
    data = result.json()
    assert data["outcome"] == "verified"
    assert statuses(data) == {
        "extrude.exists": "PASS",
        "body.solid": "PASS",
        "extrude.depth": "UNVERIFIED",
    }
    assert result.headers["cache-control"] == "no-store"
    # Exactly the four existing bounded reads; nothing can write to Onshape.
    assert len(provider.calls) == 4
    assert {call.method for call in provider.calls} == {"GET"}
    for private in (REF.documentId, VERSION, "synthetic-", "Sketch 1", "server-only"):
        assert private not in result.text


def test_each_check_reads_fresh_and_is_rate_limited_not_cached(
    harness: Harness,
) -> None:
    harness.login()
    provider = CadProvider()
    with transport(harness, provider):
        first = post(harness)
        second = post(harness)
    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["detail"] == "rate_limited"
    assert second.headers["retry-after"]
    assert len(provider.calls) == 4  # the refused check never reaches Onshape


def test_fail_for_empty_part_studio(harness: Harness) -> None:
    harness.login()
    provider = CadProvider(
        responses={
            "features": {"features": [], "isComplete": True},
            "parts": [],
            "bodies": {"bodies": [], "errorEnum": "NO_ERROR"},
            "mass": {"bodies": {}},
        }
    )
    with transport(harness, provider):
        data = post(harness).json()
    assert data["outcome"] == "not_met"
    assert statuses(data)["extrude.exists"] == "FAIL"
    assert statuses(data)["body.solid"] == "FAIL"


def test_renamed_features_still_pass(harness: Harness) -> None:
    harness.login()
    features = deepcopy(FEATURES)
    for item, name in zip(features["features"], ("Zzz", "Qqq"), strict=True):  # type: ignore[call-overload]
        item["name"] = name
    provider = CadProvider(responses={**CadProvider().responses, "features": features})
    with transport(harness, provider):
        assert post(harness).json()["outcome"] == "verified"


def test_unreadable_bodies_are_unverified_not_fail(harness: Harness) -> None:
    harness.login()
    provider = CadProvider(statuses={"bodies": 500})
    with transport(harness, provider):
        data = post(harness).json()
    assert statuses(data)["body.solid"] == "UNVERIFIED"
    assert data["outcome"] == "unverified"


def test_unknown_body_type_is_unverified(harness: Harness) -> None:
    harness.login()
    bodies: Any = deepcopy(BODIES)
    del bodies["bodies"][0]["type"]
    provider = CadProvider(responses={**CadProvider().responses, "bodies": bodies})
    with transport(harness, provider):
        data = post(harness).json()
    assert statuses(data)["body.solid"] == "UNVERIFIED"


def test_changed_microversion_makes_everything_unverified(harness: Harness) -> None:
    harness.login()
    original: Any = CadProvider().responses["parts"]
    parts = [{**p, "microversionId": "e" * 24} for p in original]
    provider = CadProvider(responses={**CadProvider().responses, "parts": parts})
    with transport(harness, provider):
        data = post(harness).json()
    assert data["consistency"] == "mismatch"
    assert all(
        r["outcome"]["status"] == "UNVERIFIED" for r in data["results"] if r["blocking"]
    )


def test_missing_read_permission_is_a_clear_refusal(harness: Harness) -> None:
    user = harness.login()
    set_scope(harness, user, "OAuth2ReadPII")
    provider = CadProvider()
    with transport(harness, provider):
        result = post(harness)
    assert result.status_code == 403
    assert result.json()["detail"] == "read_permission_required"
    assert not provider.calls


def test_disconnected_account_cannot_check(harness: Harness) -> None:
    harness.login()
    harness.client.post("/api/onshape/disconnect", headers=harness.headers())
    provider = CadProvider()
    with transport(harness, provider):
        assert post(harness).status_code in (401, 403)
    assert not provider.calls


def test_status_is_never_taken_from_the_request(harness: Harness) -> None:
    harness.login()
    provider = CadProvider()
    with transport(harness, provider):
        result = post(harness, {**body(), "status": "PASS", "outcome": "verified"})
    assert result.status_code == 400
    assert not provider.calls
