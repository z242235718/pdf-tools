from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.file import FileUploadResponse
from app.services.file_service import FileService, FileUploadError

router = APIRouter()


@router.post("", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile,
    db: Session = Depends(get_db),  # noqa: B008
) -> FileUploadResponse:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing filename",
        )

    data = await file.read()
    try:
        record, _ = FileService.upload(
            db,
            data=data,
            filename=file.filename,
        )
    except FileUploadError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST
            if exc.code in ("INVALID_FILE_TYPE", "FILE_TOO_LARGE")
            else status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_code": exc.code, "error_message": exc.message},
        ) from exc

    return FileUploadResponse(
        file_id=record.id,
        original_name=record.original_name,
        size_bytes=record.size_bytes,
        mime_type=record.mime_type,
    )


@router.get("/{file_id}/download")
def download_file(
    file_id: int,
    db: Session = Depends(get_db),  # noqa: B008
) -> FileResponse:
    record = FileService.get(db, file_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    path = FileService.resolve_path(record)
    if path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File content not found on storage",
        )

    return FileResponse(
        path=path,
        filename=record.original_name,
        media_type=record.mime_type,
    )
