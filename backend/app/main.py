from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import files, previews, settings, tasks, trace
from app.database import SessionLocal
from app.models import Task, TaskStatus
from app.services.task_service import TaskService

app = FastAPI(title="PDF Tools API", version="0.1.0")

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def recover_stale_tasks() -> None:
    """Mark tasks stuck in 'running' status as 'failed' on server restart.

    Background tasks can be killed by uvicorn --reload or process restarts,
    leaving tasks permanently stuck in 'running' with no recovery path.
    """
    db = SessionLocal()
    try:
        stale = db.query(Task).filter(Task.status == TaskStatus.running).all()
        for task in stale:
            TaskService.mark_failed(
                db, task,
                error_code="PROCESS_INTERRUPTED",
                error_message="Task interrupted by server restart",
            )
        if stale:
            from logging import getLogger
            getLogger(__name__).info("Recovered %d stale task(s)", len(stale))
    finally:
        db.close()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(previews.router, prefix="/api/previews", tags=["previews"])
app.include_router(trace.router, prefix="/api/trace", tags=["trace"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
