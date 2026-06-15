import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ToolType(enum.StrEnum):
    pdf_to_word = "pdf_to_word"
    pdf_to_png = "pdf_to_png"
    images_to_pdf = "images_to_pdf"
    split_pdf = "split_pdf"
    remove_pdf_pages = "remove_pdf_pages"
    watermark_pdf = "watermark_pdf"
    protect_pdf = "protect_pdf"


class TaskStatus(enum.StrEnum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    expired = "expired"


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tool_type: Mapped[ToolType] = mapped_column(
        Enum(ToolType, name="tool_type"), nullable=False
    )
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status"),
        default=TaskStatus.pending,
        nullable=False,
    )
    input_file_ids: Mapped[str] = mapped_column(
        Text, default="[]", nullable=False
    )  # JSON list
    output_file_ids: Mapped[str] = mapped_column(
        Text, default="[]", nullable=False
    )  # JSON list
    params: Mapped[str] = mapped_column(Text, default="{}", nullable=False)  # JSON dict
    progress: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    warnings: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
