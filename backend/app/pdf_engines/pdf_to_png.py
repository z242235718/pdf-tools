"""PDF → PNG engine.

Renders PDF pages as PNG images using PyMuPDF.
Multi-page output is packed into a ZIP archive.
"""

import json
import logging
import math
import zipfile
from datetime import UTC, datetime
from io import BytesIO

import fitz  # PyMuPDF

from app.database import SessionLocal
from app.models import Task
from app.pdf_engines.page_ranges import parse_page_range
from app.services.file_service import FileService
from app.services.naming_service import build_output_filename
from app.storage import LocalStorage

logger = logging.getLogger(__name__)

# Maximum safe pixel count (w * h) before mupdf C-level int32 overflow.
# w * h * 4 must stay well below INT32_MAX (2_147_483_647).
MAX_SAFE_PIXELS = 500_000_000


def _compute_safe_matrix(page: "fitz.Page", dpi: int) -> tuple["fitz.Matrix", str | None]:
    """Compute a zoom matrix, capping pixel count to avoid C-level int32 overflow.

    For large pages at high DPI, the product ``ceil(w_pts * zoom) * ceil(h_pts * zoom) * 4``
    can overflow a signed 32-bit integer inside mupdf's C layer.  This function
    pre-computes the pixel dimensions and scales down the zoom factor if needed.

    Returns:
        A tuple ``(matrix, warning)`` where ``warning`` is a human-readable string
        (in Chinese) when scaling is applied, or ``None`` when no scaling is needed.
    """
    zoom = dpi / 72.0
    rect = page.rect
    w = math.ceil(rect.width * zoom)
    h = math.ceil(rect.height * zoom)
    if w * h > MAX_SAFE_PIXELS:
        scale = math.sqrt(MAX_SAFE_PIXELS / (w * h))
        zoom *= scale
        effective_dpi = round(zoom * 72)
        warning = (
            f"第 {page.number + 1} 页：请求 {dpi} DPI，"
            f"因页面尺寸过大自动降级至 {effective_dpi} DPI"
        )
        logger.warning(
            "Page %d dimensions too large for %d DPI (%d\xd7%d px), "
            "scaling zoom to %.2f (effective DPI \x3d %d)",
            page.number + 1, dpi, w, h, zoom, effective_dpi,
        )
        return fitz.Matrix(zoom, zoom), warning
    return fitz.Matrix(zoom, zoom), None


storage = LocalStorage()


def _load_input_file(file_id: int) -> bytes:
    """Load the raw bytes of an input file by its database ID."""
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
    """Execute PDF \xbb PNG conversion.

    Returns:
        List of output file IDs (1 per page, or 1 ZIP for multi-page).
    """
    params: dict = json.loads(task.params) if task.params else {}
    page_range_str: str = params.get("page_range", "all")
    dpi: int = params.get("dpi", 150)
    transparent: bool = params.get("transparent_background", False)

    input_file_ids: list[int] = json.loads(task.input_file_ids) if task.input_file_ids else []
    if not input_file_ids:
        raise ValueError("No input files specified")

    # Load PDF data
    pdf_data = _load_input_file(input_file_ids[0])

    # Open with PyMuPDF
    doc = fitz.open(stream=pdf_data, filetype="pdf")
    total_pages = doc.page_count

    if total_pages == 0:
        doc.close()
        raise ValueError("PDF has no pages")

    # Parse page range (0-based indices)
    try:
        page_indices = parse_page_range(page_range_str, total_pages)
    except ValueError as exc:
        doc.close()
        raise exc

    # Get original filename from the file record
    db_local = SessionLocal()
    try:
        src_record = FileService.get(db_local, input_file_ids[0])
        original_name = src_record.original_name if src_record else "document.pdf"
    finally:
        db_local.close()

    now = datetime.now(UTC)

    output_file_ids: list[int] = []
    warnings: list[str] = []

    if len(page_indices) == 1:
        # Single page \xbb output one PNG directly
        idx = page_indices[0]
        page = doc.load_page(idx)
        try:
            safe_mat, warning = _compute_safe_matrix(page, dpi)
            if warning:
                warnings.append(warning)
            pix = page.get_pixmap(matrix=safe_mat, alpha=transparent)
        except Exception as exc:
            doc.close()
            raise RuntimeError(
                f"\xe6\xb8\xb2\xe6\x9f\x93\xe9\xa1\xb5\xe9\x9d\xa2 {idx + 1} \xe5\xa4\xb1\xe8\xb4\xa5\xef\xbc\x9a\xe5\x86\x85\xe5\xad\x98\xe4\xb8\x8d\xe8\xb6\xb3\xe6\x88\x96\xe5\x9b\xbe\xe5\x83\x8f\xe5\xb0\xba\xe5\xaf\xb8\xe8\xbf\x87\xe5\xa4\xa7\xe3\x80\x82"
                f"\xe8\xaf\xb7\xe5\xb0\x9d\xe8\xaf\x95\xe9\x99\x8d\xe4\xbd\x8e DPI\xef\xbc\x88\xe5\xbb\xba\xe8\xae\xae \xe2\x89\xa4600\xef\xbc\x89\xe6\x88\x96\xe6\xa3\x80\xe6\x9f\xa5 PDF \xe9\xa1\xb5\xe9\x9d\xa2\xe5\xb0\xba\xe5\xaf\xb8\xe3\x80\x82"
            ) from exc
        png_bytes = pix.tobytes("png")
        output_name = build_output_filename(
            original_name,
            suffix=f"page_{idx + 1:03d}",
            extension="png",
            timestamp=now,
        )

        key = storage.generate_key()
        storage.store_output(png_bytes, key)

        output_file = FileService.mark_output(
            db,
            original_name=output_name,
            mime_type="image/png",
            storage_key=key,
        )
        output_file_ids.append(output_file.id)
    else:
        # Multiple pages \xbb render each, pack into ZIP
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for idx in page_indices:
                page = doc.load_page(idx)
                try:
                    safe_mat, warning = _compute_safe_matrix(page, dpi)
                    if warning:
                        warnings.append(warning)
                    pix = page.get_pixmap(matrix=safe_mat, alpha=transparent)
                except Exception as exc:
                    doc.close()
                    raise RuntimeError(
                        f"\xe6\xb8\xb2\xe6\x9f\x93\xe9\xa1\xb5\xe9\x9d\xa2 {idx + 1} \xe5\xa4\xb1\xe8\xb4\xa5\xef\xbc\x9a\xe5\x86\x85\xe5\xad\x98\xe4\xb8\x8d\xe8\xb6\xb3\xe6\x88\x96\xe5\x9b\xbe\xe5\x83\x8f\xe5\xb0\xba\xe5\xaf\xb8\xe8\xbf\x87\xe5\xa4\xa7\xe3\x80\x82"
                        f"\xe8\xaf\xb7\xe5\xb0\x9d\xe8\xaf\x95\xe9\x99\x8d\xe4\xbd\x8e DPI\xef\xbc\x88\xe5\xbb\xba\xe8\xae\xae \xe2\x89\xa4600\xef\xbc\x89\xe6\x88\x96\xe6\xa3\x80\xe6\x9f\xa5 PDF \xe9\xa1\xb5\xe9\x9d\xa2\xe5\xb0\xba\xe5\xaf\xb8\xe3\x80\x82"
                    ) from exc
                png_bytes = pix.tobytes("png")

                entry_name = build_output_filename(
                    original_name,
                    suffix=f"page_{idx + 1:03d}",
                    extension="png",
                    timestamp=now,
                )
                zf.writestr(entry_name, png_bytes)

        zip_data = zip_buffer.getvalue()

        zip_name = build_output_filename(
            original_name,
            suffix="png",
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

    if warnings:
        logger.info("Storing warnings: %s", json.dumps(warnings))
        task.warnings = json.dumps(warnings)
        db.commit()
        logger.warning("Warnings committed: %s", task.warnings)
    else:
        logger.warning("No warnings to store (warnings list empty)")

    doc.close()
    return output_file_ids
