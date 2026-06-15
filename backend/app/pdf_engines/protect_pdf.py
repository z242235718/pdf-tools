"""PDF copyright protection and traceability engine.

Generates traceable fingerprints for PDF distribution by:
- Adding visible authorisation text watermark on each page
- Embedding a QR code linking to a verification URL (optional)
- Writing a signed payload into PDF metadata
- Setting PDF permission encryption (optional)
- Recording the fingerprint in the ``copyright_fingerprints`` table
"""

import hashlib
import hmac
import io
import json
import logging
from datetime import UTC, datetime

import fitz
import qrcode
from pypdf import PdfReader, PdfWriter
from pypdf.constants import UserAccessPermissions

from app.config import get_settings
from app.database import SessionLocal
from app.models import CopyrightFingerprint, Task
from app.pdf_engines.page_ranges import parse_page_range
from app.services.file_service import FileService
from app.services.naming_service import build_output_filename
from app.storage import LocalStorage

logger = logging.getLogger(__name__)

storage = LocalStorage()

_QR_SIZE_PTS = 50       # width/height of the QR code image on the page
_FOOTER_FONTSIZE = 8    # font size for the footer watermark text
_FOOTER_MARGIN = 10     # margin from page edge for footer text


# ── public API ──────────────────────────────────────────────────────────────

def run(task: Task, db) -> list[int]:
    """Execute copyright protection on a PDF.

    Returns:
        List containing the single output file ID.
    """
    params: dict = json.loads(task.params) if task.params else {}
    visible_text: str = params.get("visible_text", "")
    add_qrcode: bool = params.get("add_qrcode", True)
    set_permissions: bool = params.get("set_permissions", False)
    page_range_str: str = params.get("page_range", "all")

    if not visible_text:
        raise ValueError("visible_text is required for copyright protection")

    input_file_ids: list[int] = json.loads(task.input_file_ids) if task.input_file_ids else []
    if not input_file_ids:
        raise ValueError("No input files specified")

    pdf_data = _load_file_bytes(input_file_ids[0])
    fingerprint_id, signed_payload = _generate_fingerprint(
        visible_text=visible_text,
        source_file_id=input_file_ids[0],
    )

    # ── Phase 1: Add visible watermarks via PyMuPDF ───────────────────────
    doc = fitz.open(stream=pdf_data, filetype="pdf")
    try:
        total_pages = doc.page_count
        if total_pages == 0:
            raise ValueError("PDF has no pages")

        page_indices = parse_page_range(page_range_str, total_pages)

        # Generate QR code pixmap once if needed
        qr_pix = _generate_qr_pixmap(fingerprint_id) if add_qrcode else None

        for idx in page_indices:
            page = doc.load_page(idx)
            _add_footer_watermark(page, visible_text, fingerprint_id)
            if qr_pix is not None:
                _add_qr_code(page, qr_pix)

        buf = io.BytesIO()
        doc.save(buf, garbage=4, deflate=True)
        pdf_watermarked = buf.getvalue()
    finally:
        doc.close()

    # ── Phase 2: Add metadata & encryption via pypdf ──────────────────────
    reader = PdfReader(io.BytesIO(pdf_watermarked))
    writer = PdfWriter()
    writer.append(reader)

    writer.add_metadata({
        "/fingerprint_id": fingerprint_id,
        "/fingerprint_payload": signed_payload,
        "/fingerprint_visible_text": visible_text,
        "/fingerprint_created": datetime.now(UTC).isoformat(),
    })

    if set_permissions:
        # Owner password = fingerprint_secret, user password = fingerprint_id
        settings = get_settings()
        writer.encrypt(
            user_password=fingerprint_id,
            owner_password=settings.fingerprint_secret,
            permissions_flag=UserAccessPermissions.PRINT | UserAccessPermissions.EXTRACT,
        )

    pdf_final_buf = io.BytesIO()
    writer.write(pdf_final_buf)
    pdf_final = pdf_final_buf.getvalue()

    # ── Phase 3: Store output ─────────────────────────────────────────────
    original_name = _get_original_name(input_file_ids[0])
    now = datetime.now(UTC)
    output_name = build_output_filename(
        original_name,
        suffix="protected",
        extension="pdf",
        timestamp=now,
        extra=fingerprint_id,
    )

    key = storage.generate_key()
    storage.store_output(pdf_final, key)

    output_file = FileService.mark_output(
        db,
        original_name=output_name,
        mime_type="application/pdf",
        storage_key=key,
    )

    # ── Phase 4: Record fingerprint ───────────────────────────────────────
    settings = get_settings()
    verify_url = f"http://localhost:5173/trace-query?fp={fingerprint_id}"

    fp_record = CopyrightFingerprint(
        fingerprint_id=fingerprint_id,
        user_id=None,  # MVP single-user mode
        source_file_id=input_file_ids[0],
        output_file_id=output_file.id,
        task_id=task.id,
        visible_text=visible_text,
        metadata_payload=signed_payload,
        verify_url=verify_url,
    )
    db.add(fp_record)
    db.commit()

    logger.info(
        "Protected PDF %s → %s (fingerprint=%s)",
        input_file_ids[0], output_file.id, fingerprint_id,
    )
    return [output_file.id]


# ── internal helpers ────────────────────────────────────────────────────────

def _load_file_bytes(file_id: int) -> bytes:
    """Load file bytes from storage by ID."""
    _db = SessionLocal()
    try:
        record = FileService.get(_db, file_id)
        if record is None:
            raise FileNotFoundError(f"File {file_id} not found")
        path = FileService.resolve_path(record)
        if path is None:
            raise FileNotFoundError(f"File {file_id} not on storage")
        return path.read_bytes()
    finally:
        _db.close()


def _get_original_name(file_id: int) -> str:
    """Get the original filename for a file ID."""
    _db = SessionLocal()
    try:
        record = FileService.get(_db, file_id)
        return record.original_name if record else "document.pdf"
    finally:
        _db.close()


def _generate_fingerprint(
    visible_text: str,
    source_file_id: int,
) -> tuple[str, str]:
    """Generate a unique fingerprint ID and a signed payload.

    Returns:
        (fingerprint_id, signed_payload_string).
    """
    import uuid
    settings = get_settings()
    fingerprint_id = uuid.uuid4().hex[:16]  # Short readable hex ID

    payload = {
        "fingerprint_id": fingerprint_id,
        "visible_text": visible_text,
        "source_file_id": source_file_id,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    payload_str = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)

    signature = hmac.new(
        settings.fingerprint_secret.encode("utf-8"),
        payload_str.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:16]

    signed_payload = json.dumps(
        {**payload, "signature": signature},
        ensure_ascii=False,
    )
    return fingerprint_id, signed_payload


def _generate_qr_pixmap(fingerprint_id: str) -> fitz.Pixmap:
    """Generate a QR code Pixmap encoding the verification URL."""
    verify_url = f"http://localhost:5173/trace-query?fp={fingerprint_id}"
    qr_img = qrcode.make(verify_url, box_size=4, border=1)
    buf = io.BytesIO()
    qr_img.save(buf, format="PNG")
    return fitz.Pixmap(buf.getvalue())


def _add_footer_watermark(
    page: fitz.Page,
    visible_text: str,
    fingerprint_id: str,
) -> None:
    """Add a small footer watermark at the bottom of the page."""
    rect = page.rect
    text = f"{visible_text} | ID: {fingerprint_id}"
    fontname = "china-s" if _has_cjk(visible_text) else "helv"

    # Position at bottom-centre, slightly above the edge
    text_w = fitz.get_text_length(text, fontname=fontname, fontsize=_FOOTER_FONTSIZE)
    x = (rect.width - text_w) / 2
    y = rect.height - _FOOTER_MARGIN

    page.insert_text(
        fitz.Point(x, y),
        text,
        fontname=fontname,
        fontsize=_FOOTER_FONTSIZE,
        color=(0.5, 0.5, 0.5),
        fill_opacity=0.6,
        overlay=True,
    )


def _add_qr_code(page: fitz.Page, qr_pix: fitz.Pixmap) -> None:
    """Insert a QR code image at the bottom-right corner of the page."""
    rect = page.rect
    x = rect.width - _QR_SIZE_PTS - _FOOTER_MARGIN
    y = rect.height - _QR_SIZE_PTS - _FOOTER_MARGIN - _FOOTER_FONTSIZE - 2

    page.insert_image(
        rect=fitz.Rect(x, y, x + _QR_SIZE_PTS, y + _QR_SIZE_PTS),
        pixmap=qr_pix,
        overlay=True,
        keep_proportion=True,
    )


def _has_cjk(text: str) -> bool:
    """Check if text contains CJK characters."""
    for ch in text:
        if '一' <= ch <= '鿿' or '　' <= ch <= '〿':
            return True
    return False
