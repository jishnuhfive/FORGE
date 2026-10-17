"""Bounded same-origin Modify contracts. Approval never comes from an AI tool."""

import asyncio
import hmac
import json
import re
from collections.abc import AsyncIterator
from typing import cast
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import Field

from forge_api.auth.routes import Runtime, active_session
from forge_api.auth.security import csrf_token
from forge_api.integrations.onshape.client import bounded_json
from forge_api.integrations.onshape.contracts import WorkspaceReference

from . import service
from .domain import Closed, Digest, EditError, Handle, supported_intent

router = APIRouter()


class Discover(Closed):
    context: WorkspaceReference
    intent: str = Field(min_length=1, max_length=256)


class Prepare(Closed):
    context: WorkspaceReference
    candidate: Handle


class Approve(Closed):
    digest: Digest


async def guard(request: Request, auth: Runtime) -> object:
    with auth.sessions() as db:
        if active_session(request, auth, db) is None:
            raise HTTPException(401, "session_expired")
    origin = request.headers.get("origin")
    if origin is None:
        try:
            ref = urlsplit(request.headers.get("referer", ""))
            origin = f"{ref.scheme}://{ref.netloc}"
        except ValueError:
            raise HTTPException(403, "csrf_failed") from None
        if request.method == "GET" and not request.headers.get("referer"):
            origin = auth.settings.origin
    supplied = request.headers.get("x-csrf-token", "")
    if (
        origin != auth.settings.origin
        or len(request.headers.getlist("origin")) > 1
        or len(request.headers.getlist("x-csrf-token")) != 1
        or request.headers.get("sec-fetch-site") == "cross-site"
        or not re.fullmatch(r"[a-f0-9]{64}", supplied)
        or not hmac.compare_digest(
            supplied, csrf_token(request.cookies.get(auth.settings.session_cookie, ""))
        )
    ):
        raise HTTPException(403, "csrf_failed")
    if request.query_params:
        raise HTTPException(400, "invalid_request")
    if request.method == "GET":
        if request.headers.get("content-length", "0") != "0" or request.headers.get(
            "transfer-encoding"
        ):
            raise HTTPException(400, "invalid_request")
        return {}
    if request.headers.get("content-type", "").split(";")[0] != "application/json":
        raise HTTPException(400, "invalid_request")
    data = bytearray()
    try:
        async with asyncio.timeout(5):
            async for part in request.stream():
                data.extend(part)
                if len(data) > 8192:
                    raise HTTPException(413, "invalid_request")
        return bounded_json(bytes(data))
    except ValueError, TimeoutError, UnicodeError, RecursionError:
        raise HTTPException(400, "invalid_request") from None


def enabled(auth: Runtime) -> None:
    if not auth.settings.forge_cad_writes_enabled:
        raise EditError("write_disabled", 403)


def error_response(error: EditError) -> JSONResponse:
    return JSONResponse({"detail": error.code}, status_code=error.status)


@router.get("/api/modify/capabilities")
async def capabilities(request: Request, auth: Runtime) -> JSONResponse:
    await guard(request, auth)
    if not auth.settings.forge_cad_writes_enabled:
        return JSONResponse({"state": "write_disabled"})
    with auth.sessions() as db:
        current = active_session(request, auth, db)
        assert current is not None
        from forge_api.db.models import OnshapeAuthorization

        grant = db.get(OnshapeAuthorization, current.user_id)
        if grant is None or grant.status != "connected":
            state = "reconsent_required"
        elif grant.granted_scope is None or "onshape_bitmask:" in grant.granted_scope:
            state = "authorization_unknown"
        elif not {"OAuth2Read", "OAuth2Write"} <= set(grant.granted_scope.split()):
            state = "write_permission_required"
        else:
            state = "available"
    return JSONResponse({"state": state})


@router.post("/api/modify/targets")
async def targets(request: Request, auth: Runtime) -> JSONResponse:
    raw = await guard(request, auth)
    try:
        enabled(auth)
        value = Discover.model_validate(raw)
        if not supported_intent(value.intent):
            raise EditError("unsupported_edit", 422)
        result = await asyncio.to_thread(service.create, request, auth, value.context)
        return JSONResponse(result)
    except ValueError:
        raise HTTPException(400, "invalid_request") from None
    except EditError as error:
        return error_response(error)


@router.post("/api/modify/proposals")
async def proposals(request: Request, auth: Runtime) -> JSONResponse:
    raw = await guard(request, auth)
    try:
        enabled(auth)
        value = Prepare.model_validate(raw)
        return JSONResponse(
            await asyncio.to_thread(
                service.create, request, auth, value.context, value.candidate
            )
        )
    except ValueError:
        raise HTTPException(400, "invalid_request") from None
    except EditError as error:
        return error_response(error)


@router.api_route(
    "/api/modify/proposals/{handle}/{action}", methods=["POST"], response_model=None
)
async def action(
    request: Request, auth: Runtime, handle: str, action: str
) -> JSONResponse | StreamingResponse:
    raw = await guard(request, auth)
    try:
        if not re.fullmatch(r"[A-Za-z0-9_-]{43}", handle):
            raise EditError("proposal_unavailable", 404)
        if action == "approve":
            enabled(auth)
            value = Approve.model_validate(raw)

            async def events() -> AsyncIterator[str]:
                loop = asyncio.get_running_loop()
                queue: asyncio.Queue[dict[str, object]] = asyncio.Queue()

                def progress(stage: str) -> None:
                    loop.call_soon_threadsafe(
                        queue.put_nowait,
                        cast(dict[str, object], {"type": "progress", "stage": stage}),
                    )

                async def run() -> None:
                    try:
                        result = await asyncio.to_thread(
                            service.approve,
                            request,
                            auth,
                            handle,
                            value.digest,
                            progress,
                        )
                        await queue.put({"type": "result", **result})
                    except EditError as error:
                        await queue.put({"type": "error", "code": error.code})
                    except Exception:
                        await queue.put(
                            {"type": "error", "code": "execution_uncertain"}
                        )

                task = asyncio.create_task(run())
                # Shield dispatch from browser disconnect; never retry. A lost
                # connection uses owner-authenticated status/reconciliation.
                try:
                    while True:
                        event = await queue.get()
                        yield json.dumps(event) + "\n"
                        if event["type"] != "progress":
                            break
                finally:
                    await asyncio.shield(task)

            return StreamingResponse(
                events(),
                media_type="application/x-ndjson",
                headers={"X-Accel-Buffering": "no"},
            )
        Closed.model_validate(raw)
        if action == "cancel":
            return JSONResponse(
                await asyncio.to_thread(service.cancel, request, auth, handle)
            )
        if action == "reconcile":
            return JSONResponse(
                await asyncio.to_thread(service.reconcile, request, auth, handle)
            )
        raise EditError("invalid_request", 400)
    except ValueError:
        raise HTTPException(400, "invalid_request") from None
    except EditError as error:
        return error_response(error)


@router.get("/api/modify/proposals/{handle}")
async def status(request: Request, auth: Runtime, handle: str) -> JSONResponse:
    await guard(request, auth)
    try:
        if not re.fullmatch(r"[A-Za-z0-9_-]{43}", handle):
            raise EditError("proposal_unavailable", 404)
        return JSONResponse(
            await asyncio.to_thread(service.status, request, auth, handle)
        )
    except EditError as error:
        return error_response(error)
