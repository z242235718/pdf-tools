"""PDF split engine.

Splits a PDF into individual pages (one PDF per page).
Multi-page output is packed into a ZIP archive.
A single-page split returns the PDF directly.
"""

import io
import json
import logging
import zipfile
from datetime import UTC, datetime
from io import BytesIO

from pypdf import PdfReader, PdfWriter

from app.database import SessionLocal
from app.models import Task
from app.pdf_engines.page_ranges import parse_page_range
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
    """Execute PDF split by page.

    Returns:
        List of output file IDs.
    """
    params: dict = json.loads(task.params) if task.params else {}
    page_range_str: str = params.get("page_range", "all")

    input_file_ids: list[int] = json.loads(task.input_file_ids) if task.input_file_ids else []
    if not input_file_ids:
        raise ValueError("No input files specified")

    pdf_data = _load_input_file(input_file_ids[0])

    reader = PdfReader(io.BytesIO(pdf_data))
    total_pages = len(reader.pages)

    if total_pages == 0:
        raise ValueError("PDF has no pages")

    # Parse page range (0-based indices)
    try:
        page_indices = parse_page_range(page_range_str, total_pages)
    except ValueError as exc:
        raise exc

    # Get original filename
    db_local = SessionLocal()
    try:
        src_record = FileService.get(db_local, input_file_ids[0])
        original_name = src_record.original_name if src_record else "document.pdf"
    finally:
        db_local.close()

    now = datetime.now(UTC)
    output_file_ids: list[int] = []

    if len(page_indices) == 1:
        # Single page → output one PDF directly
        idx = page_indices[0]
        writer = PdfWriter()
        writer.add_page(reader.pages[idx])

        pdf_bytes = BytesIO()
        writer.write(pdf_bytes)
        writer.close()
        pdf_data_out = pdf_bytes.getvalue()

        output_name = build_output_filename(
            original_name,
            suffix=f"page_{idx + 1:03d}",
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
        output_file_ids.append(output_file.id)
    else:
        # Multiple pages → pack each into ZIP
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for idx in page_indices:
                writer = PdfWriter()
                writer.add_page(reader.pages[idx])

                page_bytes = BytesIO()
                writer.write(page_bytes)
                writer.close()

                entry_name = build_output_filename(
                    original_name,
                    suffix=f"page_{idx + 1:03d}",
                    extension="pdf",
                    timestamp=now,
                )
                zf.writestr(entry_name, page_bytes.getvalue())

        zip_data = zip_buffer.getvalue()
        zip_name = build_output_filename(
            original_name,
            suffix="split",
            extension="zip",
            timestamp=now,
        )

        key = storage.generate_key()
        storage.store_output(zip_data, key)

        output_file = FileService.mark_output(
            db,
            original_name=zip_name,
            mime_type="application/zip",
            storage_key=key,
        )
        output_file_ids.append(output_file.id)

    return output_file_ids
