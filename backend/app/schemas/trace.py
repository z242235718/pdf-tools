from datetime import datetime

from pydantic import BaseModel


class TraceQueryResponse(BaseModel):
    fingerprint_id: str
    visible_text: str | None
    created_at: datetime
    verify_url: str | None
