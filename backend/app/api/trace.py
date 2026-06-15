"""Trace / fingerprint query API.

Allows looking up copyright fingerprint records by fingerprint ID.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CopyrightFingerprint
from app.schemas.trace import TraceQueryRequest, TraceQueryResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/query", response_model=TraceQueryResponse)
def query_fingerprint(
    payload: TraceQueryRequest,
    db: Session = Depends(get_db),
) -> TraceQueryResponse:
    """Look up a copyright fingerprint by its ID."""
    record = (
        db.query(CopyrightFingerprint)
        .filter(CopyrightFingerprint.fingerprint_id == payload.fingerprint_id)
        .first()
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fingerprint {payload.fingerprint_id!r} not found",
        )

    return TraceQueryResponse(
        fingerprint_id=record.fingerprint_id,
        visible_text=record.visible_text,
        metadata_payload=record.metadata_payload,
        verify_url=record.verify_url,
        source_file_id=record.source_file_id,
        output_file_id=record.output_file_id,
        task_id=record.task_id,
        created_at=record.created_at,
    )
