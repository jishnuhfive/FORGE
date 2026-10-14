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


def test_only_allowlisted_auth_and_read_routes_exist(harness: Harness) -> None:
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
    }
    assert set(paths["/api/onshape/part-studio/snapshot"]) == {"get"}
    assert set(paths["/api/onshape/part-studio/inspector"]) == {"get"}
