"""PDF to Word conversion engine.

Uses pdf2docx to convert text-based PDF files to .docx format.
"""

import io
import json
import logging
from datetime import UTC, datetime

from pdf2docx import Converter

from app.database import SessionLocal
from app.models import Task
from app.services.file_service import FileService
from app.services.naming_service import build_output_filename
from app.storage import LocalStorage

logger = logging.getLogger(__name__)

storage = LocalStorage()

# If extracted text is below this threshold, the PDF is likely scanned.
_SCAN_THRESHOLD = 50


def run(task: Task, db) -> list[int]:
    """Convert a PDF to a .docx file.

    Returns:
        List containing the single output file ID.
    """
    params: dict = json.loads(task.params) if task.params else {}
    password: str | None = params.get("password", None)

    input_file_ids: list[int] = json.loads(task.input_file_ids) if task.input_file_ids else []
    if not input_file_ids:
        raise ValueError("No input files specified")

    pdf_data = _load_file_bytes(input_file_ids[0])

    # Convert via pdf2docx
    docx_buf = io.BytesIO()
    cv = Converter(stream=pdf_data)
    try:
        cv.convert(docx_buf, start=0, end=None)
        cv.close()
    except Exception as exc:
        logger.exception("pdf2docx conversion failed")
        raise RuntimeError(f"PDF to Word conversion failed: {exc}") from exc

    docx_bytes = docx_buf.getvalue()

    # Detect scanned PDF: convert() still produces a docx even for scanned
    # pages (each page becomes an embedded image), so we check whether
    # meaningful text was extracted by re-reading the docx metadata.
    warnings: list[str] = []
    try:
        text_len = _count_docx_text(docx_bytes)
        if text_len < _SCAN_THRESHOLD:
            warnings.append(
                "此 PDF 可能为扫描件或图片型 PDF，转换后内容可能为嵌入图片而非可编辑文本。"
                "如需要文字识别（OCR），请使用专业 OCR 工具。"
            )
    except Exception:
        pass  # Best-effort check; don't fail the task

    # Store output
    pdf_basename = _get_original_name(input_file_ids[0])
    now = datetime.now(UTC)
    output_name = build_output_filename(
        pdf_basename,
        extension="docx",
        timestamp=now,
    )
    key = storage.generate_key()
    storage.store_output(docx_bytes, key)

    output_file = FileService.mark_output(
        db,
        original_name=output_name,
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        storage_key=key,
    )

    # Attach warnings to the task
    if warnings:
        try:
            existing = json.loads(task.warnings) if task.warnings else []
        except (json.JSONDecodeError, TypeError):
            existing = []
        task.warnings = json.dumps(existing + warnings, ensure_ascii=False)
        db.commit()

    return [output_file.id]


# ── internal helpers ────────────────────────────────────────────────────────

def _load_file_bytes(file_id: int) -> bytes:
    db = SessionLocal()
    try:
        record = FileService.get(db, file_id)
        if record is None:
            raise FileNotFoundError(f"File {file_id} not found")
        path = FileService.resolve_path(record)
        if path is None:
            raise FileNotFoundError(f"File {file_id} not on storage")
        return path.read_bytes()
    finally:
        db.close()


def _get_original_name(file_id: int) -> str:
    db = SessionLocal()
    try:
        record = FileService.get(db, file_id)
        return record.original_name if record else "document.pdf"
    finally:
        db.close()


def _count_docx_text(docx_bytes: bytes) -> int:
    """Count non-whitespace characters in a .docx file.

    Opens the docx (which is a ZIP) and reads ``word/document.xml`` for a
    rough text-length estimate.  Used to detect scanned / image-only PDFs.
    """
    import zipfile
    from xml.etree import ElementTree

    with zipfile.ZipFile(io.BytesIO(docx_bytes)) as zf:
        if "word/document.xml" not in zf.namelist():
            return 0
        tree = ElementTree.parse(zf.open("word/document.xml"))
        root = tree.getroot()
        # Register the default namespace used by Word
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        texts = [t.text or "" for t in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")]
        return len("".join(texts).strip())
