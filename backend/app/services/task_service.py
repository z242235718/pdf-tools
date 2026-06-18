import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import File, Task, TaskStatus, ToolType


_TOOL_TYPE_LABEL: dict[str, str] = {
    "pdf_to_png": "转PNG",
    "images_to_pdf": "图转PDF",
    "split_pdf": "拆分PDF",
    "remove_pdf_pages": "删页",
    "watermark_pdf": "水印",
    "pdf_to_word": "转Word",
    "protect_pdf": "保护",
}


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
    def _build_task_name(tool_type: str, input_file_ids: list[int], db: Session) -> str:
        """Generate a human-readable task name.

        Format: ``{label}-{original_base}_{YYYYMMDD_HHMMSS}``
        """
        label = _TOOL_TYPE_LABEL.get(tool_type, tool_type)
        # Build original filenames string from input files
        names: list[str] = []
        for fid in input_file_ids:
            file_rec = db.query(File).filter(File.id == fid).first()
            if file_rec:
                base = file_rec.original_name.rsplit(".", 1)[0]
                names.append(base)
        name_part = "+".join(names) if names else "file"
        ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        return f"{label}-{name_part}_{ts}"

    @staticmethod
    def _get_input_file_names(input_file_ids: list[int], db: Session) -> list[str]:
        """Get original filenames for the given file IDs."""
        names: list[str] = []
        for fid in input_file_ids:
            file_rec = db.query(File).filter(File.id == fid).first()
            if file_rec:
                names.append(file_rec.original_name)
        return names

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

        task_name = TaskService._build_task_name(tool_type, input_file_ids, db)
        input_file_names = TaskService._get_input_file_names(input_file_ids, db)

        task = Task(
            user_id=user_id,
            task_name=task_name,
            input_file_names=json.dumps(input_file_names),
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
    def search_tasks(
        db: Session,
        task_name: str | None = None,
        file_name: str | None = None,
        status: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 30,
        offset: int = 0,
    ) -> tuple[list[Task], int]:
        """Search tasks with optional filters and pagination.

        Returns:
            (tasks, total_count).
        """
        q = db.query(Task)

        if task_name:
            q = q.filter(Task.task_name.ilike(f"%{task_name}%"))
        if file_name:
            q = q.filter(Task.input_file_names.ilike(f"%{file_name}%"))
        if status:
            # Support comma-separated multi-status: "succeeded,failed"
            status_list = [s.strip() for s in status.split(",") if s.strip()]
            if status_list:
                valid_statuses = [s for s in status_list if s in TaskStatus.__members__]
                if valid_statuses:
                    q = q.filter(Task.status.in_([TaskStatus[s] for s in valid_statuses]))
        if date_from:
            q = q.filter(Task.created_at >= date_from)
        if date_to:
            # Make date_to inclusive: if only a date is given, include the full day
            if "T" not in date_to and " " not in date_to:
                date_to = date_to + "T23:59:59"
            q = q.filter(Task.created_at <= date_to)

        total = q.count()
        tasks = (
            q.order_by(Task.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return tasks, total

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

    @staticmethod
    def delete_all(db: Session) -> None:
        """Delete all task records from the database."""
        db.query(Task).delete()
        db.commit()
