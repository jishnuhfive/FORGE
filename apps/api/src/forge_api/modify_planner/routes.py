"""POST /api/modify/plan: a bounded, authenticated, same-origin planning request.

The browser sends only ``{context, request}``. It cannot supply a catalog, handles,
operations, a provider identity or any approval flag. The response is a clarification
or an authoritative A1 preview; approval is a separate human action that this route
neither performs nor exposes.
"""

from typing import cast
from uuid import uuid4

import httpx2 as httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from forge_api.ai.diagnostics import Reason, Stage, emit_diagnostic
from forge_api.ai.models import AiError
from forge_api.auth.routes import Runtime, active_session
from forge_api.cad_edits.domain import Closed, EditError
from forge_api.cad_edits.routes import enabled, error_response, guard
from forge_api.integrations.onshape.client import ReadError
from forge_api.integrations.onshape.contracts import WorkspaceReference
from forge_api.integrations.onshape.service import ReadGate
from forge_api.tutor.limits import HourlyCap

from . import service
from .models import MAX_REQUEST_CHARS
from .providers import create_planner_provider

router = APIRouter()
STATUS = {
    "not_configured": 503,
    "connection_unavailable": 503,
    "authentication_failed": 503,
    "rate_limited": 429,
    "quota_unavailable": 503,
    "capacity_unavailable": 503,
    "timeout": 504,
}


class PlanRequest(Closed):
    context: WorkspaceReference
    request: str


def clean(text: str) -> str:
    text = " ".join(text.split())
    if not text or len(text) > MAX_REQUEST_CHARS:
        raise ValueError
    if any(ord(c) < 32 or ord(c) == 127 for c in text):
        raise ValueError
    return text


def failure(code: str, status: int, wait: int | None = None) -> JSONResponse:
    body: dict[str, object] = {"detail": code}
    headers = {"Cache-Control": "no-store"}
    if wait is not None:
        body["retry_after_seconds"] = wait
        headers["Retry-After"] = str(wait)
    return JSONResponse(body, status_code=status, headers=headers)


@router.post("/api/modify/plan")
async def plan(request: Request, auth: Runtime) -> JSONResponse:
    raw = await guard(request, auth)
    with auth.sessions() as db:
        session = active_session(request, auth, db)
        if session is None:
            raise HTTPException(401, "session_expired")
        user_id = session.user_id
    try:
        enabled(auth)
        value = PlanRequest.model_validate(raw)
        text = clean(value.request)
    except EditError as error:
        return error_response(error)
    except ValidationError, ValueError:
        # Default validation errors would echo the user's private request.
        raise HTTPException(400, "invalid_request") from None
    wait = cast(HourlyCap, request.app.state.planner_cap).acquire(user_id)
    if wait is not None:
        return failure("rate_limited", 429, wait)
    gate = cast(ReadGate, request.app.state.planner_gate)
    transport = cast(httpx.AsyncClient, request.app.state.ai_transport)
    correlation = uuid4().hex

    def diagnostic(error: AiError) -> None:
        emit_diagnostic(
            error,
            environment=auth.settings.environment,
            provider=auth.settings.forge_ai_provider,
            stage=Stage.FINAL_OUTPUT,
            request_id=correlation,
        )

    try:
        with gate.enter(user_id):
            result = await service.plan(
                request,
                auth,
                user_id,
                value.context,
                text,
                create_planner_provider(auth.settings, transport)
                if auth.settings.ai_configured
                else None,
                correlation,
            )
        return JSONResponse(
            result,
            headers={"Cache-Control": "no-store", "X-Forge-Request-Id": correlation},
        )
    except ReadError as error:
        return failure(
            "request_in_progress"
            if error.state.code == "request_in_progress"
            else "rate_limited",
            429,
            error.state.retry_after_seconds,
        )
    except EditError as error:
        return error_response(error)
    except AiError as error:
        diagnostic(error)
        if error.code in ("rate_limited", "capacity_unavailable", "quota_unavailable"):
            gate.defer(user_id, error.retry_after or 60)
        status = STATUS.get(error.code, 502)
        return failure(
            "plan_unavailable" if status == 502 else error.code,
            status,
            error.retry_after,
        )
    except service.Unplannable:
        diagnostic(AiError("invalid_response", reason=Reason.FINAL_CONTENT_INVALID))
        return failure("plan_unavailable", 502)
    except TimeoutError:
        diagnostic(AiError("timeout"))
        return failure("timeout", 504)
    except SQLAlchemyError, RuntimeError:
        return failure("connection_unavailable", 503)
