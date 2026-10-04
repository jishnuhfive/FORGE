import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx2 as httpx
from fastapi import FastAPI, Request
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, RedirectResponse, Response

from forge_api.auth.routes import router as auth_router
from forge_api.auth.runtime import AuthRuntime
from forge_api.core.config import Settings
from forge_api.db.database import make_engine, verify_schema
from forge_api.routes.health import router as health_router


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
            with httpx.Client(
                timeout=10, follow_redirects=False, trust_env=False
            ) as client:
                if config.auth_configured and engine is not None:
                    application.state.auth = AuthRuntime.create(config, engine, client)
                yield
        finally:
            if engine is not None:
                engine.dispose()

    development_docs = config.environment != "production"
    application = FastAPI(
        title="Forge API",
        version="0.2.0",
        debug=False,
        lifespan=lifespan,
        docs_url="/docs" if development_docs else None,
        redoc_url=None,
        openapi_url="/openapi.json" if development_docs else None,
    )
    application.state.auth = None
    application.state.settings = config
    application.add_middleware(SafeBoundary)
    application.include_router(health_router)
    application.include_router(auth_router)
    return application


app = create_app()
