"""Explicit, authenticated POST; bounded normalized NDJSON, never provider SSE."""

import asyncio
import hmac
import json
import re
from collections.abc import AsyncIterator
from typing import cast
from uuid import uuid4

import httpx2 as httpx
from fastapi import APIRouter, HTTPException, Request, Response
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool
from starlette.responses import StreamingResponse

from forge_api.auth.routes import Runtime, active_session
from forge_api.auth.security import csrf_token
from forge_api.db.models import OnshapeAuthorization
from forge_api.integrations.onshape.client import ReadError, bounded_json
from forge_api.integrations.onshape.routes import acquire_bound
from forge_api.integrations.onshape.service import ReadGate

from .diagnostics import Reason, Stage, emit_diagnostic
from .grounding import GroundedCad, ground
from .models import AiError, AiRequest
from .providers import create_provider
from .service import TOTAL_SECONDS, run_agent

router = APIRouter()
MAX_REQUEST_BYTES = 65536


@router.post("/api/ai/ask")
async def ask(request: Request, auth: Runtime) -> Response:
    with auth.sessions() as db:
        session = active_session(request, auth, db)
        if session is None:
            raise HTTPException(401, "session_expired")
        user_id = session.user_id
    supplied = request.headers.get("x-csrf-token", "")
    if (
        request.headers.get("origin") != auth.settings.origin
        or len(request.headers.getlist("origin")) != 1
        or len(request.headers.getlist("x-csrf-token")) != 1
        or request.headers.get("sec-fetch-site") == "cross-site"
        or not re.fullmatch(r"[a-f0-9]{64}", supplied)
        or not hmac.compare_digest(
            supplied, csrf_token(request.cookies.get(auth.settings.session_cookie, ""))
        )
    ):
        raise HTTPException(403, "csrf_failed")
    if (
        request.query_params
        or request.headers.get("content-type", "").split(";")[0] != "application/json"
    ):
        raise HTTPException(400, "invalid_request")
    body = bytearray()
    try:
        async with asyncio.timeout(5):
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > MAX_REQUEST_BYTES:
                    raise HTTPException(413, "invalid_request")
        value = AiRequest.model_validate(bounded_json(bytes(body)))
    except ValueError, UnicodeError, TimeoutError:
        # Default FastAPI validation errors echo private prompts; never use them.
        raise HTTPException(400, "invalid_request") from None
    if not auth.settings.ai_configured:
        raise HTTPException(503, "not_configured")
    correlation = uuid4().hex
    gate = cast(ReadGate, request.app.state.ai_gate)
    cad_gate = cast(ReadGate, request.app.state.cad_gate)
    cad_transport = cast(httpx.Client, request.app.state.cad_transport)
    transport = cast(httpx.AsyncClient, request.app.state.ai_transport)

    def active() -> None:
        with auth.sessions() as db:
            current = active_session(request, auth, db)
            grant = db.get(OnshapeAuthorization, user_id)
            if (
                current is None
                or current.user_id != user_id
                or grant is None
                or grant.status != "connected"
            ):
                raise AiError("session_expired")

    async def ensure_active() -> None:
        if await request.is_disconnected():
            raise asyncio.CancelledError
        await run_in_threadpool(active)

    def read_bound() -> GroundedCad:
        with auth.sessions() as db:
            current = active_session(request, auth, db)
            if current is None or current.user_id != user_id:
                raise AiError("session_expired")
            result = acquire_bound(
                request,
                Response(),
                auth,
                db,
                current,
                value.context,
                correlation,
                cad_gate,
                cad_transport,
            )
            return ground(result, value.context, correlation)

    async def read() -> GroundedCad:
        # The existing synchronous CAD transport completes at most four bounded
        # reads if cancelled mid-read. Cancellation prevents subsequent AI calls.
        return await asyncio.to_thread(read_bound)

    async def events() -> AsyncIterator[str]:
        stage = Stage.INSPECTION_REQUEST

        def diagnostic(error: AiError) -> None:
            emit_diagnostic(
                error,
                environment=auth.settings.environment,
                provider=auth.settings.forge_ai_provider,
                stage=stage,
                request_id=correlation,
            )

        try:
            with gate.enter(user_id):
                async with asyncio.timeout(TOTAL_SECONDS):
                    async for event in run_agent(
                        value,
                        create_provider(auth.settings, transport),
                        read,
                        ensure_active,
                        correlation,
                    ):
                        if event.get("type") == "progress":
                            stage = {
                                "understanding": Stage.INSPECTION_REQUEST,
                                "inspecting": Stage.CAD_INSPECTION,
                                "reviewing": Stage.FINAL_OUTPUT,
                                "preparing": Stage.GROUNDING,
                            }.get(str(event.get("stage")), stage)
                        yield (
                            json.dumps(event, ensure_ascii=True, allow_nan=False) + "\n"
                        )
        except ReadError as error:
            yield (
                json.dumps(
                    {
                        "type": "error",
                        "code": "request_in_progress"
                        if error.state.code == "request_in_progress"
                        else "rate_limited",
                        "retry_after_seconds": error.state.retry_after_seconds,
                    }
                )
                + "\n"
            )
        except AiError as error:
            diagnostic(error)
            if error.code in (
                "rate_limited",
                "capacity_unavailable",
                "quota_unavailable",
            ):
                gate.defer(user_id, error.retry_after or 60)
            yield (
                json.dumps(
                    {
                        "type": "error",
                        "code": error.code,
                        "retry_after_seconds": error.retry_after,
                    }
                )
                + "\n"
            )
        except TimeoutError:
            diagnostic(AiError("timeout"))
            yield (
                json.dumps(
                    {"type": "error", "code": "timeout", "retry_after_seconds": None}
                )
                + "\n"
            )
        except SQLAlchemyError, RuntimeError, ValueError:
            diagnostic(
                AiError(
                    "connection_unavailable",
                    reason=Reason.GROUNDING_REWRITE_FAILED
                    if stage == Stage.GROUNDING
                    else Reason.EVIDENCE_UNAVAILABLE
                    if stage == Stage.CAD_INSPECTION
                    else Reason.PROVIDER_UNAVAILABLE,
                )
            )
            yield (
                json.dumps(
                    {
                        "type": "error",
                        "code": "connection_unavailable",
                        "retry_after_seconds": None,
                    }
                )
                + "\n"
            )

    return StreamingResponse(
        events(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-store",
            "X-Accel-Buffering": "no",
            "X-Forge-Request-Id": correlation,
        },
    )
