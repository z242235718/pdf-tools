from pathlib import Path

from sqlalchemy.orm import Session

from app.models import File, FileKind
from app.security import validate_uploaded_file
from app.storage import LocalStorage

storage = LocalStorage()


class FileUploadError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class FileService:
    """Business logic for file upload, retrieval and download."""

    @staticmethod
    def upload(
        db: Session,
        data: bytes,
        filename: str,
        owner_id: int | None = None,
    ) -> tuple[File, Path]:
        """Validate, store and persist an uploaded file.

        Returns:
            (File record, filesystem path).
        """
        result = validate_uploaded_file(data, filename)
        if not result.valid:
            raise FileUploadError(result.error_code, result.error_message)

        key = storage.generate_key()
        path = storage.store_upload(data, key)

        file = File(
            owner_id=owner_id,
            original_name=filename,
            mime_type=result.mime_type,
            size_bytes=len(data),
            sha256=result.sha256,
            storage_key=key,
            kind=FileKind.upload,
        )
        db.add(file)
        db.commit()
        db.refresh(file)
        return file, path

    @staticmethod
    def get(db: Session, file_id: int) -> File | None:
        return db.query(File).filter(File.id == file_id).first()

    @staticmethod
    def resolve_path(file: File) -> Path | None:
        """Return the filesystem path for a file record, or *None*."""
        if file.kind == FileKind.upload:
            p = storage.upload_path(file.storage_key)
        elif file.kind == FileKind.output:
            p = storage.output_path(file.storage_key)
        else:
            return None
        return p if p.exists() else None

    @staticmethod
    def mark_output(
        db: Session,
        original_name: str,
        mime_type: str,
        storage_key: str,
        owner_id: int | None = None,
    ) -> File:
        """Register an output file in the database."""
        file = File(
            owner_id=owner_id,
            original_name=original_name,
            mime_type=mime_type,
            size_bytes=0,
            storage_key=storage_key,
            kind=FileKind.output,
        )
        db.add(file)
        db.commit()
        db.refresh(file)
        return file

    @staticmethod
    def delete(db: Session, file: File) -> None:
        """Soft-delete / mark as expired."""
        db.delete(file)
        db.commit()
