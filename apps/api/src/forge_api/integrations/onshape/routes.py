"""Two explicit projections of one authenticated read pipeline; no raw proxy."""

import hmac
import re
from typing import cast
from uuid import uuid4

import httpx2 as httpx
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import ValidationError
from sqlalchemy.orm import Session as DatabaseSession

from forge_api.auth.routes import Database, Runtime, active_session
from forge_api.auth.runtime import AuthRuntime
from forge_api.auth.security import csrf_token
from forge_api.db.models import OnshapeAuthorization
from forge_api.db.models import Session as ForgeSession

from .client import OnshapeReadClient, ReadError
from .contracts import WorkspaceReference
from .inspector import CadInspector, inspect
from .models import SectionState, Snapshot, SnapshotProof
from .service import ReadGate, capture, failed_proof, proof

router = APIRouter()


@router.get(
    "/api/onshape/part-studio/snapshot",
    response_model=SnapshotProof,
    summary="Read a workspace Part Studio count/status proof",
    description=(
        "Requires a Forge session and its X-CSRF-Token. Performs four bounded "
        "Onshape GETs with the session owner's grant. No raw CAD or provider "
        "credentials are returned. Separate reads have unverified consistency."
    ),
    openapi_extra={
        "parameters": [
            {"name": name, "in": "query", "required": True, "schema": schema}
            for name, schema in WorkspaceReference.model_json_schema()[
                "properties"
            ].items()
        ]
        + [
            {
                "name": "X-CSRF-Token",
                "in": "header",
                "required": True,
                "schema": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
            }
        ]
    },
    responses={
        400: {
            "description": "Invalid or extra context reference; values are not echoed"
        },
        401: {"description": "Forge session required"},
        403: {"description": "Forge CSRF/origin check failed"},
        422: {"description": "Version or microversion context unsupported"},
        503: {"description": "Forge authentication/database unavailable"},
    },
)
def snapshot(
    request: Request, response: Response, auth: Runtime, db: Database
) -> SnapshotProof:
    result, correlation = acquire(request, response, auth, db)
    return (
        failed_proof(result, correlation)
        if isinstance(result, SectionState)
        else proof(result, correlation)
    )


@router.get(
    "/api/onshape/part-studio/inspector",
    response_model=CadInspector,
    summary="Inspect bounded read-only workspace Part Studio evidence",
)
def inspector(
    request: Request, response: Response, auth: Runtime, db: Database
) -> CadInspector:
    result, correlation = acquire(request, response, auth, db, diagnostic=True)
    return inspect(result, correlation)


def acquire(
    request: Request,
    response: Response,
    auth: Runtime,
    db: Database,
    *,
    diagnostic: bool = False,
) -> tuple[Snapshot | SectionState, str]:
    """Both projections share authentication, quota gate and exactly one capture."""
    session = active_session(request, auth, db)
    if session is None:
        raise HTTPException(401, "connection_required")
    # GET is read-only, but spends provider quota. Require the existing session's
    # CSRF secret header; cross-origin JS cannot supply it (no credentialed CORS).
    # Same-origin GET may omit Origin/Referer under the app's no-referrer policy.
    supplied = request.headers.get("x-csrf-token", "")
    if (
        not re.fullmatch(r"[a-f0-9]{64}", supplied)
        or not hmac.compare_digest(
            supplied, csrf_token(request.cookies.get(auth.settings.session_cookie, ""))
        )
        or len(request.headers.getlist("x-csrf-token")) != 1
        or len(request.headers.getlist("origin")) > 1
        or request.headers.get("origin", auth.settings.origin) != auth.settings.origin
        or request.headers.get("sec-fetch-site") == "cross-site"
    ):
        raise HTTPException(403, "csrf_failed")
    if request.headers.get("content-length", "0") != "0" or request.headers.get(
        "transfer-encoding"
    ):
        raise HTTPException(400, "invalid_context")
    params = request.query_params
    if any(len(params.getlist(key)) != 1 for key in params):
        raise HTTPException(400, "invalid_context")
    if (
        params.get("revisionKind") in ("version", "microversion")
        or "versionId" in params
        or "microversionId" in params
    ):
        raise HTTPException(422, "unsupported_context")
    try:
        reference = WorkspaceReference.model_validate(dict(params))
    except ValidationError:
        # FastAPI's default validation response would echo private context values.
        raise HTTPException(400, "invalid_context") from None
    correlation = uuid4().hex
    response.headers["X-Forge-Request-Id"] = correlation
    gate = cast(ReadGate, request.app.state.cad_gate)
    transport = cast(httpx.Client, request.app.state.cad_transport)
    return acquire_bound(
        request,
        response,
        auth,
        db,
        session,
        reference,
        correlation,
        gate,
        transport,
        diagnostic=diagnostic,
    ), correlation


def acquire_bound(
    request: Request,
    response: Response,
    auth: AuthRuntime,
    db: DatabaseSession,
    session: ForgeSession,
    reference: WorkspaceReference,
    correlation: str,
    gate: ReadGate,
    transport: httpx.Client,
    *,
    diagnostic: bool = False,
) -> Snapshot | SectionState:
    """Server-bound reuse for the inspector and AI; never exposed as a model tool."""
    try:
        with gate.enter(session.user_id):
            mass_diagnostic = None
            body_diagnostic = None
            if auth.settings.environment == "development":
                from .dev.body_structure import describe_body
                from .dev.mass_structure import describe_mass

                mass_diagnostic = describe_mass
                body_diagnostic = describe_body
            client = OnshapeReadClient(
                str(auth.settings.onshape_api_base_url),
                transport,
                mass_diagnostic=mass_diagnostic,
                body_diagnostic=body_diagnostic,
            )
            result = capture(
                auth, client, reference, session.user_id, correlation, gate
            )
            if diagnostic and auth.settings.forge_safe_edit_diagnostics_enabled:
                from .dev.safe_edit import probe

                probe(auth, transport, reference, session.user_id)
            # Discard an in-flight result if the owning session/grant ended.
            db.expire_all()
            current = active_session(request, auth, db)
            grant = db.get(OnshapeAuthorization, session.user_id)
            if (
                current is None
                or grant is None
                or grant.status in ("disconnected", "revoked")
            ):
                raise ReadError("unauthorized", "connection_required")
            if auth.settings.environment == "development" and client.mass_structure:
                response.headers["X-Forge-Mass-Structure"] = client.mass_structure
            if auth.settings.environment == "development" and client.body_structure:
                response.headers["X-Forge-Body-Structure"] = client.body_structure
            return result
    except ReadError as error:
        return error.state
