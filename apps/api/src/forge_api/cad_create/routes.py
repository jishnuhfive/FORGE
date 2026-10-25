"""Small same-origin creation API. Only explicit approval reaches mutation."""

import json
from typing import cast
from uuid import uuid4

import httpx2 as httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import Field, ValidationError
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from forge_api.ai.diagnostics import Stage, emit_diagnostic
from forge_api.ai.models import AiError
from forge_api.auth.routes import Runtime, active_session
from forge_api.cad_edits import storage
from forge_api.cad_edits.domain import Closed, Digest, EditError, Handle
from forge_api.cad_edits.routes import error_response, guard
from forge_api.integrations.onshape.client import ReadError
from forge_api.integrations.onshape.contracts import WorkspaceReference
from forge_api.integrations.onshape.service import ReadGate
from forge_api.modify_planner.routes import STATUS, failure

from . import service
from .compile import BriefError
from .models import PlateWithHolesBrief
from .natural_language import interpret

router = APIRouter()


class Interpret(Closed):
    request: str = Field(min_length=1, max_length=1024)


class Prepare(Closed):
    context: WorkspaceReference
    brief: PlateWithHolesBrief


class Approve(Closed):
    digest: Digest
    brief_confirmed: bool


@router.post("/api/create/interpret")
async def natural(request: Request, auth: Runtime) -> JSONResponse:
    raw = await guard(request, auth)
    correlation = uuid4().hex
    try:
        value = Interpret.model_validate(raw)
        with auth.sessions() as db:
            current = active_session(request, auth, db)
            if current is None:
                raise EditError("session_expired", 401)
            user = current.user_id
        gate = cast(ReadGate, request.app.state.planner_gate)
        with gate.enter(user):
            result = await interpret(
                auth.settings,
                cast(httpx.AsyncClient, request.app.state.ai_transport),
                value.request,
                correlation,
            )
        return JSONResponse(
            result.model_dump(mode="json"), headers={"Cache-Control": "no-store"}
        )
    except ValidationError, OverflowError:
        return JSONResponse({"detail": "invalid_request"}, 400)
    except AiError as error:
        # Same closed mapping as Modify: only an unusable model answer asks the user
        # to rewrite; provider capacity, auth, quota and timeouts say what they are.
        emit_diagnostic(
            error,
            environment=auth.settings.environment,
            provider=auth.settings.forge_ai_provider,
            stage=Stage.FINAL_OUTPUT,
            request_id=correlation,
        )
        if error.code in ("rate_limited", "capacity_unavailable", "quota_unavailable"):
            gate.defer(user, error.retry_after or 60)
        status = STATUS.get(error.code, 502)
        return failure(
            "plan_unavailable" if status == 502 else error.code,
            status,
            error.retry_after,
        )
    except TimeoutError:
        return failure("timeout", 504)
    except ReadError:
        return JSONResponse({"detail": "request_in_progress"}, 429)
    except EditError as error:
        return error_response(error)
    except SQLAlchemyError, RuntimeError:
        return JSONResponse({"detail": "connection_unavailable"}, 503)


@router.post("/api/create/plan")
async def prepare(request: Request, auth: Runtime) -> JSONResponse:
    raw = await guard(request, auth)
    try:
        value = Prepare.model_validate_json(json.dumps(raw, allow_nan=False))
        return JSONResponse(
            await run_in_threadpool(
                service.prepare, request, auth, value.context, value.brief
            ),
            headers={"Cache-Control": "no-store"},
        )
    except ValidationError, OverflowError:
        return JSONResponse({"detail": "invalid_request"}, 400)
    except BriefError:
        return JSONResponse({"detail": "unsupported_geometry"}, 422)
    except EditError as error:
        return error_response(error)
    except SQLAlchemyError, RuntimeError:
        return JSONResponse({"detail": "connection_unavailable"}, 503)


@router.post("/api/create/plans/{handle}/approve")
async def approve(handle: Handle, request: Request, auth: Runtime) -> JSONResponse:
    raw = await guard(request, auth)
    try:
        value = Approve.model_validate(raw)
        if not value.brief_confirmed:
            raise EditError("invalid_request", 400)
        return JSONResponse(
            await run_in_threadpool(
                service.approve, request, auth, handle, value.digest
            ),
            headers={"Cache-Control": "no-store"},
        )
    except ValidationError, OverflowError:
        return JSONResponse({"detail": "invalid_request"}, 400)
    except EditError as error:
        return error_response(error)
    except SQLAlchemyError, RuntimeError:
        return JSONResponse({"detail": "connection_unavailable"}, 503)


@router.get("/api/create/plans/{handle}")
async def status(handle: Handle, request: Request, auth: Runtime) -> JSONResponse:
    await guard(request, auth)
    try:
        return JSONResponse(
            await run_in_threadpool(service.status, request, auth, handle),
            headers={"Cache-Control": "no-store"},
        )
    except EditError as error:
        return error_response(error)
    except SQLAlchemyError, RuntimeError:
        return JSONResponse({"detail": "connection_unavailable"}, 503)


@router.post("/api/create/plans/{handle}/cancel")
async def cancel(handle: Handle, request: Request, auth: Runtime) -> JSONResponse:
    await guard(request, auth)
    try:
        with auth.sessions.begin() as db:
            current = active_session(request, auth, db)
            if current is None:
                raise EditError("session_expired", 401)
            row = storage.owned(db, handle, current.user_id, current.token_hash)
            saved = service.load(row)
            from forge_api.cad_edits.service import authority

            if (
                authority(request, auth, db, saved.binding.context, lock=True)
                != saved.binding
            ):
                raise EditError("context_changed")
            db.refresh(row)
            if row.state != "pending":
                raise EditError("proposal_used")
            row.state = "cancelled"
        return JSONResponse({"state": "cancelled"})
    except EditError as error:
        return error_response(error)
    except SQLAlchemyError, RuntimeError:
        return JSONResponse({"detail": "connection_unavailable"}, 503)
