"""Client context is never identity, authorization, or a backend proxy target."""

import pytest
from conftest import Harness


@pytest.mark.parametrize(
    "endpoint", ["/api/onshape/check", "/api/onshape/disconnect", "/auth/logout"]
)
def test_context_ids_cannot_authenticate(harness: Harness, endpoint: str) -> None:
    result = harness.client.post(
        endpoint,
        json={
            "documentId": "a" * 24,
            "workspaceId": "b" * 24,
            "elementId": "c" * 24,
            "server": "https://cad.onshape.com",
        },
        headers={"Origin": "https://cad.onshape.com"},
    )
    assert result.status_code == 401
    assert not harness.provider.calls


@pytest.mark.parametrize(
    "endpoint", ["/api/onshape/check", "/api/onshape/disconnect", "/auth/logout"]
)
def test_context_ids_cannot_redirect_an_authenticated_account_action(
    harness: Harness, endpoint: str
) -> None:
    harness.login()
    calls_before = len(harness.provider.calls)
    result = harness.client.post(
        endpoint,
        headers=harness.headers(),
        json={
            "user_id": "another-user",
            "documentId": "a" * 24,
            "elementId": "c" * 24,
            "server": "https://evil.example",
        },
    )
    assert result.status_code == 400
    assert len(harness.provider.calls) == calls_before
    assert harness.client.get("/api/me").json()["status"] == "authenticated"


def test_only_allowlisted_auth_read_and_approved_edit_routes_exist(
    harness: Harness,
) -> None:
    paths = harness.client.get("/openapi.json").json()["paths"]
    assert set(paths) == {
        "/health",
        "/api/me",
        "/auth/onshape/start",
        "/auth/onshape/callback",
        "/auth/logout",
        "/api/onshape/check",
        "/api/onshape/disconnect",
        "/api/onshape/part-studio/snapshot",
        "/api/onshape/part-studio/inspector",
        "/api/ai/ask",
        "/api/learning/check-step",
        "/api/learning/tutor",
        "/api/modify/capabilities",
        "/api/modify/targets",
        "/api/modify/plan",
        "/api/modify/recovery",
        "/api/modify/plans/{handle}/reconcile",
        "/api/modify/proposals",
        "/api/modify/proposals/{handle}",
        "/api/modify/proposals/{handle}/{action}",
        "/api/modify/plans/{handle}/approve",
        "/api/modify/plans/{handle}/cancel",
        "/api/modify/plans/{handle}",
    }
    assert set(paths["/api/onshape/part-studio/snapshot"]) == {"get"}
    assert set(paths["/api/onshape/part-studio/inspector"]) == {"get"}
    assert set(paths["/api/ai/ask"]) == {"post"}
    assert set(paths["/api/learning/check-step"]) == {"post"}
    assert set(paths["/api/learning/tutor"]) == {"post"}
    assert set(paths["/api/modify/plan"]) == {"post"}

    assert set(paths["/api/modify/proposals/{handle}/{action}"]) == {"post"}
    assert set(paths["/api/modify/proposals/{handle}"]) == {"get"}
    assert set(paths["/api/modify/plans/{handle}/approve"]) == {"post"}
    assert set(paths["/api/modify/plans/{handle}/cancel"]) == {"post"}
    assert set(paths["/api/modify/plans/{handle}"]) == {"get"}
