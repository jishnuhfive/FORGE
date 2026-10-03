from fastapi import FastAPI

from forge_api.core.config import Settings
from forge_api.routes.health import router as health_router


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings if settings is not None else Settings()
    development_docs = config.environment != "production"
    application = FastAPI(
        title="Forge API",
        version="0.0.0",
        debug=False,
        docs_url="/docs" if development_docs else None,
        redoc_url=None,
        openapi_url="/openapi.json" if development_docs else None,
    )
    application.include_router(health_router)
    return application


app = create_app()
