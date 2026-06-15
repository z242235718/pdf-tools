"""Remove PDF pages engine.

Deletes specified pages from a PDF and outputs the remaining pages
as a single PDF file.
"""

import io
import json
import logging
from datetime import UTC, datetime

from pypdf import PdfReader, PdfWriter

from app.database import SessionLocal
from app.models import Task
from app.pdf_engines.page_ranges import compute_remaining_pages, parse_page_range
from app.services.file_service import FileService
from app.services.naming_service import build_output_filename
from app.storage import LocalStorage

logger = logging.getLogger(__name__)

storage = LocalStorage()


def _load_input_file(file_id: int) -> bytes:
    db = SessionLocal()
    try:
        record = FileService.get(db, file_id)
        if record is None:
            raise FileNotFoundError(f"Input file {file_id} not found")
        path = FileService.resolve_path(record)
        if path is None:
            raise FileNotFoundError(f"Input file {file_id} not on storage")
        return path.read_bytes()
    finally:
        db.close()


def run(task: Task, db) -> list[int]:
    """Execute remove-pages on a PDF.

    Returns:
        List containing the single output file ID.
    """
    params: dict = json.loads(task.params) if task.params else {}
    delete_pages_str: str = params.get("delete_pages", "")

    if not delete_pages_str:
        raise ValueError("delete_pages is required")

    input_file_ids: list[int] = json.loads(task.input_file_ids) if task.input_file_ids else []
    if not input_file_ids:
        raise ValueError("No input files specified")

    pdf_data = _load_input_file(input_file_ids[0])

    reader = PdfReader(io.BytesIO(pdf_data))
    total_pages = len(reader.pages)

    if total_pages == 0:
        raise ValueError("PDF has no pages")

    # Parse delete pages (1-based user input → 0-based indices)
    try:
        delete_indices = parse_page_range(delete_pages_str, total_pages)
    except ValueError as exc:
        raise exc

    # Compute remaining page indices (0-based)
    try:
        keep_indices = compute_remaining_pages(delete_indices, total_pages)
    except ValueError as exc:
        # This raises when all pages would be deleted
        raise exc

    # Build output PDF
    writer = PdfWriter()
    for idx in keep_indices:
        writer.add_page(reader.pages[idx])

    pdf_bytes_buf = io.BytesIO()
    writer.write(pdf_bytes_buf)
    writer.close()
    pdf_data_out = pdf_bytes_buf.getvalue()

    # Get original filename
    db_local = SessionLocal()
    try:
        src_record = FileService.get(db_local, input_file_ids[0])
        original_name = src_record.original_name if src_record else "document.pdf"
    finally:
        db_local.close()

    now = datetime.now(UTC)
    output_name = build_output_filename(
        original_name,
        suffix="removed_pages",
        extension="pdf",
        timestamp=now,
    )

    key = storage.generate_key()
    storage.store_output(pdf_data_out, key)

    output_file = FileService.mark_output(
        db,
        original_name=output_name,
        mime_type="application/pdf",
        storage_key=key,
    )
    return [output_file.id]
