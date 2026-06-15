"""Preview endpoints for watermark.

Generates a low‑resolution preview of a watermarked first page so users
can inspect look‑and‑feel before submitting a task.
"""

import base64
import logging

import fitz
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.pdf_engines.watermark import _img_bytes_to_pixmap, _load_file_bytes
from app.schemas.preview import PreviewResponse
from app.services.file_service import FileService

logger = logging.getLogger(__name__)

router = APIRouter()


class WatermarkPreviewRequest(BaseModel):
    file_id: int
    watermark_type: str = Field(..., pattern=r"^(text|image)$")
    params: dict = Field(default_factory=dict)
    max_width: int = Field(default=200, ge=50, le=800)


@router.post("/watermark", response_model=PreviewResponse)
def watermark_preview(
    payload: WatermarkPreviewRequest,
    db: Session = Depends(get_db),
) -> PreviewResponse:
    """Generate a low‑res PNG preview of a watermarked first page."""
    # Validate input file
    file_record = FileService.get(db, payload.file_id)
    if file_record is None:
        raise HTTPException(status_code=404, detail="File not found")

    pdf_data = _load_file_bytes(payload.file_id)

    # Load watermark image if needed
    image_data: bytes | None = None
    if payload.watermark_type == "image":
        wm_file_id = payload.params.get("watermark_file_id")
        if not wm_file_id:
            raise HTTPException(
                status_code=422,
                detail="watermark_file_id is required for image watermark",
            )
        image_data = _load_file_bytes(wm_file_id)

    # Generate preview
    try:
        from app.pdf_engines.watermark import generate_preview_png

        png_bytes = generate_preview_png(
            pdf_data=pdf_data,
            params=payload.params | {"watermark_type": payload.watermark_type},
            image_data=image_data,
            max_width=payload.max_width,
        )
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    b64 = base64.b64encode(png_bytes).decode("ascii")
    data_url = f"data:image/png;base64,{b64}"

    doc = fitz.open(stream=pdf_data, filetype="pdf")
    page_count = doc.page_count
    doc.close()

    return PreviewResponse(
        file_id=payload.file_id,
        page_count=page_count,
        preview_image_url=data_url,
    )
