import logging
from urllib.parse import parse_qs

import pytest
from conftest import Harness
from cryptography.fernet import Fernet, InvalidToken
from pydantic import SecretStr
from sqlalchemy import func, select, update

from forge_api.auth.provider import ProviderError
from forge_api.auth.security import TokenCipher, digest, random_token
from forge_api.db.models import (
    AuditEvent,
    OAuthState,
    OnshapeAuthorization,
    Session,
    User,
    UserPreferences,
    now,
)


def test_start_url_browser_binding_and_safe_headers(harness: Harness) -> None:
    state = harness.start()
    assert len(state) == 43
    response = harness.client.get("/auth/onshape/start", follow_redirects=False)
    location = response.headers["location"]
    assert location.startswith("https://oauth.onshape.com/oauth/authorize?")
    params = parse_qs(location.split("?", 1)[1])
    assert params["response_type"] == ["code"]
    assert params["client_id"] == ["synthetic-client"]
    assert params["redirect_uri"] == [
        harness.runtime.settings.origin + "/auth/onshape/callback"
    ]
    assert params["state"] != [state]
    assert "client_secret" not in params
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=lax" in response.headers["set-cookie"]
    with harness.runtime.sessions() as db:
        record = db.get(OAuthState, digest(state))
        assert record is not None and record.consumed_at is not None
        assert record.browser_hash != harness.client.cookies.get("forge_oauth")


@pytest.mark.parametrize(
    "case", ["missing", "unknown", "expired", "mismatch", "no_browser", "duplicate"]
)
def test_invalid_state_never_exchanges(harness: Harness, case: str) -> None:
    state = harness.start()
    if case == "expired":
        with harness.runtime.sessions.begin() as db:
            db.execute(update(OAuthState).values(expires_at=now() - 1))
    elif case == "unknown":
        state = random_token()
    elif case == "mismatch":
        harness.client.cookies.clear()
        harness.client.cookies.set("forge_oauth", random_token())
    elif case == "no_browser":
        harness.client.cookies.clear()
    elif case == "missing":
        state = ""
    if case == "duplicate":
        response = harness.client.get(
            f"/auth/onshape/callback?state={state}&state={state}&code=synthetic-code",
            follow_redirects=False,
        )
    else:
        response = harness.callback(state, code="synthetic-code")
    assert response.headers["location"].endswith("/#/auth/invalid_state")
    assert not harness.provider.calls


def test_success_identity_minimization_session_and_replay(harness: Harness) -> None:
    state = harness.start()
    browser = harness.client.cookies.get("forge_oauth")
    response = harness.callback(state, code="synthetic-code")
    assert response.status_code == 303
    raw = harness.client.cookies.get("forge_session")
    assert raw and len(raw) == 43
    assert "HttpOnly" in response.headers["set-cookie"]
    profile = harness.client.get("/api/me").json()
    assert profile["display_name"] == "Test Engineer"
    assert profile["connection"] == "connected"
    assert (
        not {"id", "onshape_user_id", "access_token", "refresh_token"} & profile.keys()
    )
    with harness.runtime.sessions() as db:
        assert db.scalar(select(func.count()).select_from(User)) == 1
        assert db.scalar(select(func.count()).select_from(UserPreferences)) == 1
        assert db.get(Session, digest(raw)) is not None
        grant = db.scalar(select(OnshapeAuthorization))
        assert grant and grant.encrypted_refresh_token
        assert "synthetic-refresh" not in grant.encrypted_refresh_token
        assert (
            harness.runtime.cipher.decrypt(grant.encrypted_refresh_token)
            == "synthetic-refresh"
        )
        assert grant.granted_scope is None  # No invented claim about granted scopes.
    assert (
        harness.provider.calls[1].headers["authorization"] == "Bearer synthetic-access"
    )
    harness.client.cookies.set("forge_oauth", browser or "")
    assert (
        harness.callback(state, code="synthetic-code")
        .headers["location"]
        .endswith("invalid_state")
    )
    assert len(harness.provider.calls) == 2


def test_existing_user_and_session_fixation(harness: Harness) -> None:
    first_user = harness.login()
    first_cookie = harness.client.cookies.get("forge_session") or ""
    harness.provider.identity_payload = {
        "id": "synthetic-user",
        "name": "Updated Engineer",
        "email": "unused@example.invalid",
    }
    assert harness.login() == first_user
    assert harness.client.cookies.get("forge_session") != first_cookie
    with harness.runtime.sessions() as db:
        assert db.scalar(select(func.count()).select_from(User)) == 1
        session = db.get(Session, digest(first_cookie))
        assert session and session.revoked_at
    assert harness.client.get("/api/me").json()["display_name"] == "Updated Engineer"


@pytest.mark.parametrize(
    "case",
    [
        "denied",
        "provider_error",
        "missing_code",
        "extra",
        "exchange",
        "identity",
        "malformed",
        "network",
    ],
)
def test_callback_failures_clean_query_and_issue_no_session(
    harness: Harness, case: str
) -> None:
    state = harness.start()
    params = {"code": "synthetic-code"}
    suffix = "authorization_error"
    if case == "denied":
        params = {
            "error": "access_denied",
            "error_description": "untrusted-provider-text",
        }
        suffix = "authorization_denied"
    if case == "provider_error":
        params = {"error": "unknown"}
    if case == "missing_code":
        params = {}
    if case == "extra":
        params["return_to"] = "https://attacker.invalid"
    if case == "exchange":
        harness.provider.exchange_status = 400
    if case == "identity":
        harness.provider.identity_payload = {"name": "Missing stable ID"}
    if case == "malformed":
        harness.provider.malformed_token = True
    if case == "network":
        harness.provider.network_error = True
    response = harness.callback(state, **params)
    assert (
        response.headers["location"]
        == harness.runtime.settings.origin + "/#/auth/" + suffix
    )
    assert not harness.client.cookies.get("forge_session")
    assert not harness.client.cookies.get("forge_oauth")
    assert harness.client.get("/api/me").json()["status"] == "signed_out"


def test_optional_profile_name(harness: Harness) -> None:
    harness.provider.identity_payload = {"id": "synthetic-user"}
    harness.login()
    assert harness.client.get("/api/me").json()["display_name"] == "Onshape member"


@pytest.mark.parametrize("field", ["expires_at", "last_seen_at", "revoked_at"])
def test_expired_or_revoked_sessions(harness: Harness, field: str) -> None:
    harness.login()
    with harness.runtime.sessions.begin() as db:
        db.execute(update(Session).values(**{field: 1}))
    assert harness.client.get("/api/me").json()["status"] == "session_expired"
    assert harness.client.post("/auth/logout").status_code == 401


@pytest.mark.parametrize(
    "path", ["/auth/logout", "/api/onshape/disconnect", "/api/onshape/check"]
)
@pytest.mark.parametrize(
    "case",
    [
        "anonymous",
        "missing_csrf",
        "wrong_csrf",
        "wrong_origin",
        "null_origin",
        "missing_origin",
    ],
)
def test_mutations_require_owned_session_csrf_and_origin(
    harness: Harness, path: str, case: str
) -> None:
    if case == "anonymous":
        assert harness.client.post(path).status_code == 401
        return
    harness.login()
    headers = harness.headers()
    if case == "missing_csrf":
        headers.pop("X-CSRF-Token")
    if case == "wrong_csrf":
        headers["X-CSRF-Token"] = "wrong"
    if case == "wrong_origin":
        headers["Origin"] = "https://attacker.invalid"
    if case == "null_origin":
        headers["Origin"] = "null"
    if case == "missing_origin":
        headers.pop("Origin")
    assert harness.client.post(path, headers=headers).status_code == 403
    assert harness.client.get("/api/me").json()["connection"] == "connected"


def test_logout_only_revokes_current_session(harness: Harness) -> None:
    harness.login()
    cookie = harness.client.cookies.get("forge_session") or ""
    assert (
        harness.client.post("/auth/logout", headers=harness.headers()).status_code
        == 204
    )
    assert not harness.client.cookies.get("forge_session")
    harness.client.cookies.set("forge_session", cookie)
    assert harness.client.get("/api/me").json()["status"] == "session_expired"
    with harness.runtime.sessions() as db:
        grant = db.scalar(select(OnshapeAuthorization))
        assert grant and grant.encrypted_refresh_token


def test_disconnect_is_local_and_preserves_session(harness: Harness) -> None:
    user_id = harness.login()
    headers = harness.headers()
    assert (
        harness.client.post("/api/onshape/disconnect", headers=headers).status_code
        == 204
    )
    profile = harness.client.get("/api/me").json()
    assert profile["status"] == "authenticated"
    assert profile["connection"] == "disconnected"
    with harness.runtime.sessions() as db:
        grant = db.get(OnshapeAuthorization, user_id)
        assert grant and grant.encrypted_refresh_token is None
        assert grant.access_expires_at is None
    with pytest.raises(ProviderError):
        harness.runtime.tokens.get_valid_onshape_access_token(user_id)
    assert len(harness.provider.calls) == 2


def test_referer_fallback_and_body_rejection(harness: Harness) -> None:
    harness.login()
    headers = harness.headers()
    headers["Referer"] = headers.pop("Origin") + "/#/settings"
    assert (
        harness.client.post(
            "/auth/logout", headers=headers, json={"user_id": "other"}
        ).status_code
        == 400
    )
    assert harness.client.post("/auth/logout", headers=headers).status_code == 204


def test_open_redirect_parameters_rejected(harness: Harness) -> None:
    response = harness.client.get(
        "/auth/onshape/start?next=https://attacker.invalid", follow_redirects=False
    )
    assert response.headers["location"].startswith(harness.runtime.settings.origin)
    assert not harness.client.cookies.get("forge_oauth")


def test_token_cipher_authentication_and_rotation(harness: Harness) -> None:
    cipher = harness.runtime.cipher
    encrypted = cipher.encrypt("synthetic-sensitive-token")
    assert encrypted != cipher.encrypt("synthetic-sensitive-token")
    assert cipher.decrypt(encrypted) == "synthetic-sensitive-token"
    for corrupt in ["plaintext", encrypted[:-4] + "AAAA"]:
        with pytest.raises(InvalidToken):
            cipher.decrypt(corrupt)
    settings = harness.runtime.settings.model_copy(
        update={
            "token_encryption_key": SecretStr(Fernet.generate_key().decode()),
            "token_encryption_previous_keys": (
                harness.runtime.settings.token_encryption_key
            ),
        }
    )
    rotated = TokenCipher(settings)
    assert rotated.decrypt(encrypted) == "synthetic-sensitive-token"
    with pytest.raises(InvalidToken):
        cipher.decrypt(rotated.encrypt("new-token"))


@pytest.mark.parametrize("rotate", [True, False])
def test_refresh_rotation_and_ephemeral_access_cache(
    harness: Harness, rotate: bool
) -> None:
    user_id = harness.login()
    assert (
        harness.runtime.tokens.get_valid_onshape_access_token(user_id)
        == "synthetic-access"
    )
    assert len(harness.provider.calls) == 2
    harness.runtime.tokens.forget(user_id)
    harness.provider.rotated = rotate
    assert (
        harness.runtime.tokens.get_valid_onshape_access_token(user_id)
        == "synthetic-refreshed-access"
    )
    with harness.runtime.sessions() as db:
        grant = db.get(OnshapeAuthorization, user_id)
        assert grant and grant.encrypted_refresh_token
        expected = "synthetic-rotated-refresh" if rotate else "synthetic-refresh"
        assert harness.runtime.cipher.decrypt(grant.encrypted_refresh_token) == expected
    assert (
        harness.runtime.tokens.get_valid_onshape_access_token(user_id)
        == "synthetic-refreshed-access"
    )
    assert len(harness.provider.calls) == 3


@pytest.mark.parametrize(
    "case", ["revoked", "service", "network", "corrupt", "invalid_client"]
)
def test_refresh_failure_transitions_and_no_retry_loop(
    harness: Harness, case: str
) -> None:
    user_id = harness.login()
    harness.runtime.tokens.forget(user_id)
    if case == "revoked":
        harness.provider.refresh_status = 400
    if case == "service":
        harness.provider.refresh_status = 503
    if case == "network":
        harness.provider.network_error = True
    if case == "invalid_client":
        harness.provider.refresh_status = 401
        harness.provider.refresh_error = "invalid_client"
    if case == "corrupt":
        with harness.runtime.sessions.begin() as db:
            db.execute(
                update(OnshapeAuthorization).values(encrypted_refresh_token="broken")
            )
    for _ in range(2):
        with pytest.raises(ProviderError):
            harness.runtime.tokens.get_valid_onshape_access_token(user_id)
    assert harness.client.get("/api/me").json()["connection"] == (
        "revoked" if case == "revoked" else "error"
    )
    assert len(harness.provider.calls) == (2 if case == "corrupt" else 3)


def test_remote_revocation_check_and_reconnect(harness: Harness) -> None:
    harness.login()
    harness.provider.identity_status = 401
    assert (
        harness.client.post("/api/onshape/check", headers=harness.headers()).status_code
        == 409
    )
    assert harness.client.get("/api/me").json()["connection"] == "revoked"
    harness.provider.identity_status = 200
    harness.login()
    assert harness.client.get("/api/me").json()["connection"] == "connected"


def test_identity_check_rejects_other_account(harness: Harness) -> None:
    harness.login()
    harness.provider.identity_payload = {"id": "another-user"}
    assert (
        harness.client.post("/api/onshape/check", headers=harness.headers()).status_code
        == 409
    )


def test_secrets_never_enter_logs_audit_or_public_errors(
    harness: Harness, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    user_id = harness.login()
    cookie = harness.client.cookies.get("forge_session") or ""
    harness.runtime.tokens.forget(user_id)
    harness.provider.refresh_status = 400
    with pytest.raises(ProviderError):
        harness.runtime.tokens.get_valid_onshape_access_token(user_id)
    response = harness.client.get("/api/me")
    with harness.runtime.sessions() as db:
        events = db.scalars(select(AuditEvent)).all()
        safe_audit = repr([(e.kind, e.outcome) for e in events])
        assert any(e.kind == "login_succeeded" for e in events)
    assert harness.runtime.settings.token_encryption_key
    for sensitive in [
        "synthetic-client-secret",
        "synthetic-code",
        "synthetic-access",
        "synthetic-refresh",
        cookie,
        harness.runtime.settings.token_encryption_key.get_secret_value(),
    ]:
        assert sensitive not in caplog.text
        assert sensitive not in safe_audit
        assert sensitive not in response.text


def test_second_user_cannot_target_first_users_grant(harness: Harness) -> None:
    first = harness.login()
    harness.provider.identity_payload = {
        "id": "second-synthetic-user",
        "name": "Second user",
    }
    harness.callback(harness.start(), code="synthetic-code")
    response = harness.client.post(
        "/api/onshape/disconnect?user_id=" + first, headers=harness.headers()
    )
    assert response.status_code == 400
    assert (
        harness.client.post(
            "/api/onshape/disconnect", headers=harness.headers()
        ).status_code
        == 204
    )
    with harness.runtime.sessions() as db:
        grant = db.get(OnshapeAuthorization, first)
        assert grant and grant.status == "connected" and grant.encrypted_refresh_token
        second = db.scalar(
            select(User).where(User.onshape_user_id == "second-synthetic-user")
        )
        assert second
        other = db.get(OnshapeAuthorization, second.id)
        assert other and other.status == "disconnected"


def test_provider_token_request_is_server_side_form_encoded(harness: Harness) -> None:
    harness.callback(harness.start(), code="synthetic-code&special=+value")
    request = harness.provider.calls[0]
    assert request.method == "POST"
    assert request.url.query == b""
    assert request.headers["content-type"] == "application/x-www-form-urlencoded"
    values = parse_qs(request.content.decode())
    assert values["code"] == ["synthetic-code&special=+value"]
    assert values["client_secret"] == ["synthetic-client-secret"]
    assert values["redirect_uri"] == [
        harness.runtime.settings.origin + "/auth/onshape/callback"
    ]


def test_provider_redirect_never_receives_credentials(harness: Harness) -> None:
    harness.provider.exchange_status = 302
    assert (
        harness.callback(harness.start(), code="synthetic-code")
        .headers["location"]
        .endswith("authorization_error")
    )
    assert len(harness.provider.calls) == 1


def test_https_cookies_are_host_only_secure_and_httponly(harness: Harness) -> None:
    from pydantic import AnyHttpUrl

    config = harness.runtime.settings.model_copy(
        update={
            "app_base_url": AnyHttpUrl("https://localhost:5173"),
            "onshape_redirect_uri": AnyHttpUrl(
                "https://localhost:5173/auth/onshape/callback"
            ),
            "session_samesite": "none",
        }
    )
    harness.runtime.settings = config
    harness.runtime.provider.settings = config
    harness.client.base_url = "https://localhost:5173"
    response = harness.callback(harness.start(), code="synthetic-code")
    cookie = response.headers["set-cookie"]
    assert "__Host-forge_session=" in cookie
    assert "Secure" in cookie and "HttpOnly" in cookie
    assert "SameSite=none" in cookie and "Path=/" in cookie
    assert "Domain=" not in cookie
    assert harness.client.get("/api/me").json()["status"] == "authenticated"


def test_invalid_referer_fails_closed(harness: Harness) -> None:
    harness.login()
    headers = harness.headers()
    headers.pop("Origin")
    headers["Referer"] = "https://[malformed"
    assert harness.client.post("/auth/logout", headers=headers).status_code == 403


def test_csrf_token_from_another_session_fails(harness: Harness) -> None:
    harness.login()
    headers = harness.headers()
    harness.login()
    assert harness.client.post("/auth/logout", headers=headers).status_code == 403


def test_expired_access_token_is_refreshed(harness: Harness) -> None:
    user_id = harness.login()
    # Advance provider-token time without invalidating the Forge session.
    from unittest.mock import patch

    with patch("forge_api.auth.tokens.now", return_value=now() + 3601):
        assert (
            harness.runtime.tokens.get_valid_onshape_access_token(user_id)
            == "synthetic-refreshed-access"
        )
    assert len(harness.provider.calls) == 3


def test_company_context_url_is_operator_configured(harness: Harness) -> None:
    harness.runtime.provider.settings = harness.runtime.settings.model_copy(
        update={
            "onshape_company_id": "a" * 24,
        }
    )
    url = harness.runtime.provider.authorization_url("state&encoded")
    values = parse_qs(url.split("?", 1)[1])
    assert values["company_id"] == ["a" * 24]
    assert values["state"] == ["state&encoded"]


def test_reported_onshape_permissions_mask_is_retained_without_inference(
    harness: Harness,
) -> None:
    harness.provider.identity_payload = {"id": "synthetic-user", "oauth2Scopes": 16}
    user_id = harness.login()
    with harness.runtime.sessions() as db:
        grant = db.get(OnshapeAuthorization, user_id)
        assert grant and grant.granted_scope == "onshape_bitmask:16"


@pytest.mark.parametrize("context", ["stack", "company"])
def test_operator_context_change_requires_new_authentication(
    harness: Harness, context: str
) -> None:
    from pydantic import AnyHttpUrl

    user_id = harness.login()
    update_values = (
        {"onshape_api_base_url": AnyHttpUrl("https://enterprise.onshape.com/api")}
        if context == "stack"
        else {"onshape_company_id": "a" * 24}
    )
    settings = harness.runtime.settings.model_copy(update=update_values)
    harness.runtime.settings = settings
    harness.runtime.provider.settings = settings
    assert harness.client.get("/api/me").json()["status"] == "session_expired"
    with pytest.raises(ProviderError):
        harness.runtime.tokens.get_valid_onshape_access_token(user_id)
    assert len(harness.provider.calls) == 2
