import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import Task, TaskStatus, ToolType


class TaskService:
    """Business logic for creating, querying and updating tasks."""

    # Mapping from tool_type to the engine function that runs it
    ENGINE_MAP: dict[str, str] = {
        "pdf_to_png": "app.pdf_engines.pdf_to_png.run",
        "images_to_pdf": "app.pdf_engines.images_to_pdf.run",
        "split_pdf": "app.pdf_engines.split_pdf.run",
        "remove_pdf_pages": "app.pdf_engines.remove_pages.run",
        "watermark_pdf": "app.pdf_engines.watermark.run",
        "pdf_to_word": "app.pdf_engines.pdf_to_word.run",
        "protect_pdf": "app.pdf_engines.protect_pdf.run",
    }

    @staticmethod
    def create(
        db: Session,
        tool_type: str,
        input_file_ids: list[int],
        params: dict[str, Any],
        user_id: int | None = None,
    ) -> Task:
        if tool_type not in ToolType.__members__:
            raise ValueError(f"Unknown tool_type: {tool_type}")

        task = Task(
            user_id=user_id,
            tool_type=ToolType[tool_type],
            status=TaskStatus.pending,
            input_file_ids=json.dumps(input_file_ids),
            params=json.dumps(params),
            progress=0.0,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def get(db: Session, task_id: int) -> Task | None:
        return db.query(Task).filter(Task.id == task_id).first()

    @staticmethod
    def list_by_user(
        db: Session,
        user_id: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Task]:
        q = db.query(Task)
        if user_id is not None:
            q = q.filter(Task.user_id == user_id)
        return (
            q.order_by(Task.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    @staticmethod
    def mark_running(db: Session, task: Task) -> None:
        task.status = TaskStatus.running
        task.started_at = datetime.now(UTC)
        db.commit()

    @staticmethod
    def mark_succeeded(
        db: Session,
        task: Task,
        output_file_ids: list[int],
        progress: float = 100.0,
    ) -> None:
        task.status = TaskStatus.succeeded
        task.progress = progress
        task.output_file_ids = json.dumps(output_file_ids)
        task.finished_at = datetime.now(UTC)
        db.commit()

    @staticmethod
    def mark_failed(
        db: Session,
        task: Task,
        error_code: str,
        error_message: str,
    ) -> None:
        task.status = TaskStatus.failed
        task.error_code = error_code
        task.error_message = error_message
        task.finished_at = datetime.now(UTC)
        db.commit()

    @staticmethod
    def update_progress(db: Session, task: Task, progress: float) -> None:
        task.progress = progress
        db.commit()

    @staticmethod
    def delete(db: Session, task: Task) -> None:
        db.delete(task)
        db.commit()
