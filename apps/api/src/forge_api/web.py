"""Explicit production entrypoints, with no catch-all filesystem or SPA route."""

from pathlib import Path

from fastapi import FastAPI
from starlette.responses import FileResponse
from starlette.staticfiles import StaticFiles

FRAME_ANCESTORS = "frame-ancestors https://cad.onshape.com"


def install_web(application: FastAPI, directory: Path) -> None:
    @application.get("/", include_in_schema=False)
    @application.get("/extension", include_in_schema=False)
    def entrypoint() -> FileResponse:
        # Queries remain in the browser URL for the existing strict launch parser.
        return FileResponse(directory / "index.html", media_type="text/html")

    application.mount(
        "/assets",
        StaticFiles(directory=directory / "assets", follow_symlink=False),
        name="web-assets",
    )
    if (directory / "brand").is_dir():
        application.mount(
            "/brand",
            StaticFiles(directory=directory / "brand", follow_symlink=False),
            name="web-brand",
        )
