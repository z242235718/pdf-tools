from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CopyrightFingerprint(Base):
    __tablename__ = "copyright_fingerprints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fingerprint_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_file_id: Mapped[int] = mapped_column(Integer, nullable=False)
    output_file_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    task_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    visible_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    verify_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )
