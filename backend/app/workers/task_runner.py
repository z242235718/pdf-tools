"""Background task runner using FastAPI BackgroundTasks.

In MVP this runs synchronously inside the API process.  In production this
should be replaced by a Celery worker (see Phase M13).
"""

import logging

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Task
from app.pdf_engines import (
    images_to_pdf,
    pdf_to_png,
    pdf_to_word,
    protect_pdf,
    remove_pages,
    split_pdf,
    watermark,
)
from app.services.task_service import TaskService

logger = logging.getLogger(__name__)


_ENGINE_DISPATCH: dict[str, object] = {
    "pdf_to_png": pdf_to_png.run,
    "images_to_pdf": images_to_pdf.run,
    "split_pdf": split_pdf.run,
    "remove_pdf_pages": remove_pages.run,
    "watermark_pdf": watermark.run,
    "pdf_to_word": pdf_to_word.run,
    "protect_pdf": protect_pdf.run,
}


def run_task_background(task_id: int) -> None:
    """Execute a task in the background.

    This is designed to be called via FastAPI ``BackgroundTasks.add_task()``.
    It opens its own DB session so the caller's session is not shared.
    """
    db: Session = SessionLocal()
    try:
        task = TaskService.get(db, task_id)
        if task is None:
            logger.error("Task %s not found", task_id)
            return

        TaskService.mark_running(db, task)

        engine = _ENGINE_DISPATCH.get(task.tool_type.value)
        if engine is None:
            TaskService.mark_failed(
                db, task,
                error_code="INVALID_TOOL_TYPE",
                error_message=f"Unknown tool type: {task.tool_type.value}",
            )
            return

        output_file_ids = engine(task, db)
        TaskService.mark_succeeded(db, task, output_file_ids)

    except NotImplementedError:
        # Stub engines raise this — mark as succeeded with empty output
        # so the UI can test the flow
        task = TaskService.get(db, task_id)
        if task:
            TaskService.mark_succeeded(db, task, [])
    except Exception as exc:
        logger.exception("Task %s failed", task_id)
        task = TaskService.get(db, task_id)
        if task:
            TaskService.mark_failed(
                db, task,
                error_code="CONVERSION_FAILED",
                error_message=str(exc),
            )
    finally:
        db.close()
