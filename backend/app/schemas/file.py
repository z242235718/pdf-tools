from datetime import datetime

from pydantic import BaseModel


class FileUploadResponse(BaseModel):
    file_id: int
    original_name: str
    size_bytes: int
    mime_type: str


class FileResponse(BaseModel):
    id: int
    original_name: str
    mime_type: str
    size_bytes: int
    sha256: str | None
    storage_key: str
    created_at: datetime
    expires_at: datetime | None

    model_config = {"from_attributes": True}
