import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

import httpx2 as httpx
from fastapi import FastAPI, Request
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, RedirectResponse, Response

from forge_api.ai.routes import router as ai_router
from forge_api.auth.routes import router as auth_router
from forge_api.auth.runtime import AuthRuntime
from forge_api.cad_edits.routes import router as edit_router
from forge_api.core.config import Settings
from forge_api.db.database import make_engine, verify_schema
from forge_api.integrations.onshape.routes import router as cad_router
from forge_api.integrations.onshape.service import ReadGate
from forge_api.routes.health import router as health_router
from forge_api.step_checks.routes import router as step_checks_router
from forge_api.tutor.limits import HourlyCap
from forge_api.tutor.routes import router as tutor_router


class SafeBoundary(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        try:
            if len(request.scope.get("query_string", b"")) > 8192:
                response: Response = JSONResponse(
                    {"detail": "invalid_request"}, status_code=400
                )
            else:
                response = await call_next(request)
        except SQLAlchemyError, RuntimeError:
            # No exception/body/URL interpolation: DB errors can contain token material.
            response = JSONResponse({"detail": "service_unavailable"}, status_code=503)
        if (
            request.url.path == "/auth/onshape/callback"
            and not isinstance(response, RedirectResponse)
            and response.status_code >= 400
        ):
            config: Settings = request.app.state.settings
            response = RedirectResponse(
                config.origin + "/#/auth/authorization_error", status_code=303
            )
            response.delete_cookie(
                config.state_cookie,
                path="/",
                httponly=True,
                secure=config.secure_cookies,
                samesite="lax",
            )
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings if settings is not None else Settings()
    # Transport/access logging may include callback queries or response headers.
    for name in ("httpx2", "httpcore2", "uvicorn.access"):
        logging.getLogger(name).setLevel(logging.CRITICAL + 1)
    engine: Engine | None = None

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        nonlocal engine
        try:
            if config.database_url:
                engine = make_engine(config)
                try:
                    verify_schema(engine)
                except SQLAlchemyError, RuntimeError:
                    raise RuntimeError(
                        "Database unavailable or migration required; run make migrate"
                    ) from None
            with (
                httpx.Client(
                    timeout=10, follow_redirects=False, trust_env=False
                ) as client,
                httpx.Client(
                    timeout=httpx.Timeout(connect=3, read=8, write=3, pool=2),
                    limits=httpx.Limits(
                        max_connections=16, max_keepalive_connections=8
                    ),
                    follow_redirects=False,
                    trust_env=False,
                ) as cad_transport,
            ):
                application.state.cad_transport = cad_transport
                if config.auth_configured and engine is not None:
                    application.state.auth = AuthRuntime.create(config, engine, client)
                async with httpx.AsyncClient(
                    timeout=45,
                    follow_redirects=False,
                    trust_env=False,
                    limits=httpx.Limits(max_connections=8, max_keepalive_connections=4),
                ) as ai_transport:
                    application.state.ai_transport = ai_transport

                    async def purge_writes() -> None:
                        from forge_api.cad_edits.storage import cleanup

                        while True:
                            await asyncio.sleep(60)
                            runtime = application.state.auth
                            if runtime is not None:
                                try:

                                    def purge(owner: AuthRuntime = runtime) -> None:
                                        with owner.sessions.begin() as db:
                                            cleanup(db)

                                    await asyncio.to_thread(purge)
                                except SQLAlchemyError:
                                    pass  # Cleanup failure never releases a fence.

                    cleaner = asyncio.create_task(purge_writes())
                    try:
                        yield
                    finally:
                        cleaner.cancel()
                        with suppress(asyncio.CancelledError):
                            await cleaner
        finally:
            if engine is not None:
                engine.dispose()

    development_docs = config.environment != "production"
    application = FastAPI(
        title="Forge API",
        version="0.6.0",
        debug=False,
        lifespan=lifespan,
        docs_url="/docs" if development_docs else None,
        redoc_url=None,
        openapi_url="/openapi.json" if development_docs else None,
    )
    application.state.auth = None
    application.state.cad_gate = ReadGate()
    application.state.ai_gate = ReadGate()
    application.state.tutor_gate = ReadGate()
    application.state.tutor_cap = HourlyCap()
    application.state.settings = config
    application.add_middleware(SafeBoundary)
    application.include_router(health_router)
    application.include_router(auth_router)
    application.include_router(cad_router)
    application.include_router(ai_router)
    application.include_router(edit_router)
    application.include_router(step_checks_router)
    application.include_router(tutor_router)
    return application


app = create_app()
