from datetime import datetime

from pydantic import BaseModel


class TraceQueryRequest(BaseModel):
    fingerprint_id: str


class TraceQueryResponse(BaseModel):
    fingerprint_id: str
    visible_text: str | None
    metadata_payload: str | None
    verify_url: str | None
    source_file_id: int
    output_file_id: int | None
    task_id: int | None
    created_at: datetime | None

    model_config = {"from_attributes": True}
