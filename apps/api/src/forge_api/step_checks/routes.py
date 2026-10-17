"""Explicit, authenticated Check my step. Read-only; status is never model-chosen.

The browser names a lesson step and the validated workspace context only. The
server owns the requirement set, performs one fresh bounded Onshape read through
the existing gate, and evaluates deterministic requirements over that evidence.
"""

import asyncio
import hmac
import re
from typing import Literal, cast
from uuid import uuid4

import httpx2 as httpx
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, ValidationError
from starlette.concurrency import run_in_threadpool

from forge_api.auth.routes import Runtime, active_session
from forge_api.auth.security import csrf_token
from forge_api.db.models import OnshapeAuthorization
from forge_api.integrations.onshape.client import ReadError, bounded_json
from forge_api.integrations.onshape.contracts import WorkspaceReference
from forge_api.integrations.onshape.inspector import inspect
from forge_api.integrations.onshape.models import SectionState
from forge_api.integrations.onshape.routes import acquire_bound
from forge_api.integrations.onshape.service import ReadGate

from .bracket import STEPS, check_step
from .model import RequirementResult, StepOutcome

router = APIRouter()
MAX_REQUEST_BYTES = 4096
READ_REFUSALS = {
    "connection_required": 401,
    "read_permission_required": 403,
    "permission_or_access_required": 403,
    "document_forbidden": 403,
    "request_in_progress": 409,
    "rate_limited": 429,
}


class CheckStepRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)

    lesson_id: Literal["mounting-bracket"]
    step_id: str
    context: WorkspaceReference


class CheckStepResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    lesson_id: Literal["mounting-bracket"]
    step_id: str
    outcome: StepOutcome
    results: tuple[RequirementResult, ...]
    captured_at: str
    # The snapshot consists of separate reads; Forge never claims it is atomic.
    consistency: Literal["unverified", "mismatch"]


def refuse(code: str, retry_after: int | None = None) -> JSONResponse:
    headers = {"Cache-Control": "no-store"}
    if retry_after:
        headers["Retry-After"] = str(retry_after)
    return JSONResponse(
        {"detail": code, "retry_after_seconds": retry_after},
        status_code=READ_REFUSALS.get(code, 503),
        headers=headers,
    )


@router.post("/api/learning/check-step", response_model=CheckStepResponse)
async def check_my_step(request: Request, auth: Runtime) -> Response:
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
        value = CheckStepRequest.model_validate(bounded_json(bytes(body)))
    except ValueError, UnicodeError, TimeoutError, ValidationError:
        # Default validation errors would echo private document identifiers.
        raise HTTPException(400, "invalid_request") from None
    if value.step_id not in STEPS:
        raise HTTPException(400, "invalid_request")

    correlation = uuid4().hex
    cad_gate = cast(ReadGate, request.app.state.cad_gate)
    cad_transport = cast(httpx.Client, request.app.state.cad_transport)

    def run() -> Response:
        with auth.sessions() as db:
            current = active_session(request, auth, db)
            grant = db.get(OnshapeAuthorization, user_id)
            if (
                current is None
                or current.user_id != user_id
                or grant is None
                or grant.status != "connected"
            ):
                raise HTTPException(401, "session_expired")
            try:
                snapshot = acquire_bound(
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
            except ReadError as error:
                return refuse(error.state.code, error.state.retry_after_seconds)
        if isinstance(snapshot, SectionState):
            return refuse(snapshot.code, snapshot.retry_after_seconds)
        # Authorization and quota stops are shown as such, not as model findings.
        stop = next(
            (
                state
                for state in snapshot.sections.values()
                if state.status in ("unauthorized", "forbidden", "rate_limited")
            ),
            None,
        )
        if stop is not None:
            return refuse(stop.code, stop.retry_after_seconds)
        evidence = inspect(snapshot, correlation)
        result = check_step(value.step_id, evidence)
        return JSONResponse(
            CheckStepResponse(
                lesson_id=value.lesson_id,
                step_id=value.step_id,
                outcome=result.outcome,
                results=result.results,
                captured_at=evidence.source.captured_at,
                consistency=evidence.source.consistency,
            ).model_dump(mode="json"),
            headers={"Cache-Control": "no-store"},
        )

    return await run_in_threadpool(run)
