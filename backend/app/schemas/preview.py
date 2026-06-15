from pydantic import BaseModel


class PreviewResponse(BaseModel):
    file_id: int
    page_count: int
    preview_image_url: str | None = None
