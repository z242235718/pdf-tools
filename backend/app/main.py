"""FastAPI entry point.

Exposes ``create_app`` so the PyInstaller launcher (``run.py``) and tests
can build the same application with different config.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import files, previews, settings, tasks, trace
from app.database import Base, SessionLocal, engine
from app.models import Task, TaskStatus
from app.services.task_service import TaskService

log = logging.getLogger(__name__)

_STATIC_DIR_ENV = "PDF_TOOLS_FRONTEND_DIST"


def _frontend_dist() -> Path | None:
    raw = os.environ.get(_STATIC_DIR_ENV)
    if not raw:
        return None
    path = Path(raw).expanduser().resolve()
    return path if path.is_dir() else None


def _recover_stale_tasks() -> None:
    db = SessionLocal()
    try:
        stale = db.query(Task).filter(Task.status == TaskStatus.running).all()
        for task in stale:
            TaskService.mark_failed(
                db,
                task,
                error_code="PROCESS_INTERRUPTED",
                error_message="Task interrupted by server restart",
            )
        if stale:
            log.info("Recovered %d stale task(s)", len(stale))
    finally:
        db.close()


def create_app() -> FastAPI:
    app = FastAPI(title="PDF Tools API", version="0.1.0")

    # In single-EXE mode the SPA is served from the same origin, so CORS is a no-op.
    # In dev (vite on :5173) we still want CORS enabled.
    frontend_dist = _frontend_dist()
    if frontend_dist is None:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.on_event("startup")
    def _on_startup() -> None:
        Base.metadata.create_all(bind=engine)
        _recover_stale_tasks()
        if frontend_dist is not None:
            log.info("Serving frontend from %s", frontend_dist)

    @app.get("/health")
    def _health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(files.router, prefix="/api/files", tags=["files"])
    app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
    app.include_router(previews.router, prefix="/api/previews", tags=["previews"])
    app.include_router(trace.router, prefix="/api/trace", tags=["trace"])
    app.include_router(settings.router, prefix="/api/settings", tags=["settings"])

    if frontend_dist is not None:
        assets_dir = frontend_dist / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        @app.get("/favicon.svg")
        def _favicon() -> FileResponse:
            target = frontend_dist / "favicon.svg"
            return FileResponse(target) if target.exists() else FileResponse(frontend_dist / "index.html")

        @app.get("/{full_path:path}")
        def _spa_fallback(full_path: str, request: Request):  # noqa: ARG001
            # Never shadow API routes; FastAPI router runs first so this is safe.
            candidate = frontend_dist / full_path
            if full_path and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(frontend_dist / "index.html")

    return app


app = create_app()
