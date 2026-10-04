import hmac
import re
from collections.abc import Iterator
from typing import Annotated, Literal, cast
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session as DatabaseSession
from starlette.responses import RedirectResponse

from forge_api.auth.provider import ProviderError
from forge_api.auth.runtime import AuthRuntime
from forge_api.auth.security import audit, csrf_token, digest, random_token
from forge_api.db.models import (
    OAuthState,
    OnshapeAuthorization,
    Session,
    User,
    UserPreferences,
    identifier,
    now,
)

router = APIRouter()


class Me(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    status: Literal["signed_out", "session_expired", "authenticated"]
    configured: bool
    display_name: str | None = None
    connection: Literal["connected", "disconnected", "revoked", "error"] | None = None
    csrf_token: str | None = None
    verified_at: int | None = None


def runtime(request: Request) -> AuthRuntime:
    value = cast(AuthRuntime | None, request.app.state.auth)
    if value is None:
        raise HTTPException(503, "auth_unavailable")
    return value


Runtime = Annotated[AuthRuntime, Depends(runtime)]


def database(auth: Runtime) -> Iterator[DatabaseSession]:
    with auth.sessions() as db:
        yield db


Database = Annotated[DatabaseSession, Depends(database)]


def redirect(auth: AuthRuntime, status: str = "") -> RedirectResponse:
    response = RedirectResponse(
        auth.settings.origin + ("/#/auth/" + status if status else "/"), status_code=303
    )
    response.delete_cookie(
        auth.settings.state_cookie,
        path="/",
        secure=auth.settings.secure_cookies,
        httponly=True,
        samesite="lax",
    )
    return response


def active_session(
    request: Request, auth: AuthRuntime, db: DatabaseSession
) -> Session | None:
    raw = request.cookies.get(auth.settings.session_cookie, "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", raw):
        return None
    session = db.get(Session, digest(raw))
    if (
        session is None
        or session.revoked_at is not None
        or session.expires_at <= now()
        or session.last_seen_at + auth.settings.session_idle_seconds <= now()
    ):
        return None
    grant = db.get(OnshapeAuthorization, session.user_id)
    if (
        grant is None
        or grant.stack != str(auth.settings.onshape_api_base_url)
        or grant.company_id != auth.settings.onshape_company_id
    ):
        return None
    return session


def require_mutation(
    request: Request, auth: AuthRuntime, db: DatabaseSession
) -> Session:
    session = active_session(request, auth, db)
    if session is None:
        raise HTTPException(401, "session_expired")
    origin = request.headers.get("origin")
    if origin is None:
        try:
            referer = urlsplit(request.headers.get("referer", ""))
            origin = f"{referer.scheme}://{referer.netloc}"
        except ValueError:
            raise HTTPException(403, "csrf_failed") from None
    supplied = request.headers.get("x-csrf-token", "")
    expected = csrf_token(request.cookies.get(auth.settings.session_cookie, ""))
    if (
        origin != auth.settings.origin
        or len(request.headers.getlist("origin")) > 1
        or not re.fullmatch(r"[a-f0-9]{64}", supplied)
        or not hmac.compare_digest(supplied, expected)
    ):
        raise HTTPException(403, "csrf_failed")
    # Empty POSTs only; no user IDs, return URLs or provider parameters are accepted.
    if (
        request.query_params
        or request.headers.get("content-length", "0") != "0"
        or request.headers.get("transfer-encoding")
    ):
        raise HTTPException(400, "invalid_request")
    session.last_seen_at = now()
    return session


@router.get("/auth/onshape/start")
def start(request: Request, auth: Runtime, db: Database) -> Response:
    if request.query_params:
        return redirect(auth, "authorization_error")
    state, browser = random_token(), random_token()
    previous = request.cookies.get(auth.settings.state_cookie)
    if previous:
        db.execute(
            update(OAuthState)
            .where(OAuthState.browser_hash == digest(previous))
            .values(consumed_at=now())
        )
    db.add(
        OAuthState(
            state_hash=digest(state),
            browser_hash=digest(browser),
            expires_at=now() + 600,
        )
    )
    audit(db, "login_started")
    db.commit()
    response = RedirectResponse(auth.provider.authorization_url(state), status_code=303)
    response.set_cookie(
        auth.settings.state_cookie,
        browser,
        max_age=600,
        httponly=True,
        secure=auth.settings.secure_cookies,
        samesite="lax",
        path="/",
    )
    return response


@router.get("/auth/onshape/callback")
def callback(request: Request, auth: Runtime, db: Database) -> Response:
    params = request.query_params
    state = params.get("state", "")
    browser = request.cookies.get(auth.settings.state_cookie, "")
    valid_shape = (
        re.fullmatch(r"[A-Za-z0-9_-]{43}", state)
        and re.fullmatch(r"[A-Za-z0-9_-]{43}", browser)
        and all(len(params.getlist(key)) == 1 for key in params)
    )
    consumed = None
    if valid_shape:
        consumed = db.scalar(
            update(OAuthState)
            .where(
                OAuthState.state_hash == digest(state),
                OAuthState.browser_hash == digest(browser),
                OAuthState.expires_at > now(),
                OAuthState.consumed_at.is_(None),
            )
            .values(consumed_at=now())
            .returning(OAuthState.state_hash)
        )
    if consumed is None:
        audit(db, "login_failed", "invalid_state")
        db.commit()
        return redirect(auth, "invalid_state")
    # Commit first: concurrent/replayed callbacks cannot exchange twice.
    db.commit()
    if "error" in params:
        denied = params.get("error") == "access_denied"
        audit(
            db,
            "login_denied" if denied else "login_failed",
            "denied" if denied else "provider_error",
        )
        db.commit()
        return redirect(
            auth, "authorization_denied" if denied else "authorization_error"
        )
    code = params.get("code", "")
    if not code or len(code) > 4096 or set(params) - {"code", "state"}:
        audit(db, "login_failed", "malformed")
        db.commit()
        return redirect(auth, "authorization_error")
    try:
        token = auth.provider.exchange(code)
        identity = auth.provider.identity(token.access_token.get_secret_value())
    except ProviderError:
        audit(db, "login_failed", "provider_error")
        db.commit()
        return redirect(auth, "authorization_error")
    stack = str(auth.settings.onshape_api_base_url)
    new_id = identifier()
    insert = sqlite_insert if db.get_bind().dialect.name == "sqlite" else pg_insert
    db.execute(
        insert(User)
        .values(
            id=new_id,
            onshape_user_id=identity.id,
            stack=stack,
            display_name=identity.name or "Onshape member",
        )
        .on_conflict_do_nothing(index_elements=["onshape_user_id", "stack"])
    )
    user = db.scalar(
        select(User)
        .where(User.onshape_user_id == identity.id, User.stack == stack)
        .with_for_update()
    )
    assert user is not None
    user.display_name = identity.name or "Onshape member"
    user.updated_at = user.last_login_at = now()
    grant = db.scalar(
        select(OnshapeAuthorization)
        .where(OnshapeAuthorization.user_id == user.id)
        .with_for_update()
    )
    if grant is None:
        grant = OnshapeAuthorization(user_id=user.id, stack=stack)
        db.add(grant)
    assert token.refresh_token is not None
    grant.encrypted_refresh_token = auth.cipher.encrypt(
        token.refresh_token.get_secret_value()
    )
    grant.access_expires_at = now() + token.expires_in
    grant.granted_scope = token.scope
    if grant.granted_scope is None and identity.oauth2_scopes is not None:
        # Retain the provider-reported mask without inventing a bit-to-scope map.
        grant.granted_scope = f"onshape_bitmask:{identity.oauth2_scopes}"
    grant.company_id = auth.settings.onshape_company_id
    grant.status = "connected"
    grant.generation = identifier()
    grant.updated_at = grant.verified_at = now()
    grant.disconnected_at = grant.retry_after = None
    if db.get(UserPreferences, user.id) is None:
        db.add(UserPreferences(user_id=user.id))
    old = active_session(request, auth, db)
    if old:
        old.revoked_at = now()
        audit(db, "session_revoked", user_id=old.user_id)
    raw = random_token()
    db.add(
        Session(
            token_hash=digest(raw),
            user_id=user.id,
            expires_at=now() + auth.settings.session_lifetime_seconds,
        )
    )
    audit(db, "login_succeeded", user_id=user.id)
    db.commit()
    auth.tokens.remember(user.id, grant.generation, token)
    response = redirect(auth)
    response.set_cookie(
        auth.settings.session_cookie,
        raw,
        max_age=auth.settings.session_lifetime_seconds,
        httponly=True,
        secure=auth.settings.secure_cookies,
        samesite=auth.settings.session_samesite,
        path="/",
    )
    return response


@router.get("/api/me", response_model=Me)
def me(request: Request) -> Me:
    auth = cast(AuthRuntime | None, request.app.state.auth)
    if auth is None:
        return Me(status="signed_out", configured=False)
    with auth.sessions() as db:
        session = active_session(request, auth, db)
        if session is None:
            status: Literal["signed_out", "session_expired"] = (
                "session_expired"
                if request.cookies.get(auth.settings.session_cookie)
                else "signed_out"
            )
            return Me(status=status, configured=True)
        user = db.get(User, session.user_id)
        grant = db.get(OnshapeAuthorization, session.user_id)
        assert user is not None
        return Me(
            status="authenticated",
            configured=True,
            display_name=user.display_name,
            connection=cast(
                Literal["connected", "disconnected", "revoked", "error"],
                grant.status if grant else "disconnected",
            ),
            csrf_token=csrf_token(request.cookies[auth.settings.session_cookie]),
            verified_at=grant.verified_at if grant else None,
        )


@router.post("/auth/logout", status_code=204)
def logout(request: Request, auth: Runtime, db: Database) -> Response:
    session = require_mutation(request, auth, db)
    session.revoked_at = now()
    audit(db, "logout", user_id=session.user_id)
    audit(db, "session_revoked", user_id=session.user_id)
    db.commit()
    response = Response(status_code=204)
    response.delete_cookie(
        auth.settings.session_cookie,
        path="/",
        httponly=True,
        secure=auth.settings.secure_cookies,
        samesite=auth.settings.session_samesite,
    )
    return response


@router.post("/api/onshape/disconnect", status_code=204)
def disconnect(request: Request, auth: Runtime, db: Database) -> Response:
    session = require_mutation(request, auth, db)
    grant = db.scalar(
        select(OnshapeAuthorization)
        .where(OnshapeAuthorization.user_id == session.user_id)
        .with_for_update()
    )
    if grant:
        grant.encrypted_refresh_token = None
        grant.access_expires_at = None
        grant.status = "disconnected"
        grant.disconnected_at = grant.updated_at = now()
        grant.generation = identifier()
        grant.retry_after = None
    audit(db, "authorization_disconnected", "local_only", session.user_id)
    db.commit()
    auth.tokens.forget(session.user_id)
    return Response(status_code=204)


@router.post("/api/onshape/check", status_code=204)
def check(request: Request, auth: Runtime, db: Database) -> Response:
    session = require_mutation(request, auth, db)
    user_id = session.user_id
    db.commit()
    try:
        auth.tokens.check_identity(user_id)
    except ProviderError as error:
        raise HTTPException(
            409 if error.revoked else 503,
            "reconnect_required" if error.revoked else "authorization_error",
        ) from None
    return Response(status_code=204)
