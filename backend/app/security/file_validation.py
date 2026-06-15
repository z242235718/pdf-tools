import hashlib
import io
from dataclasses import dataclass

from PIL import Image

from app.config import get_settings

settings = get_settings()

# PDF magic bytes: "%PDF"
PDF_HEADER = b"%PDF"

# Common image signatures (magic bytes)  — first bytes of the file
IMAGE_SIGNATURES: dict[str, bytes] = {
    "image/jpeg": b"\xff\xd8\xff",
    "image/png": b"\x89PNG\r\n\x1a\n",
    "image/webp": b"WEBP",
    "image/gif": b"GIF8",
    "image/bmp": b"BM",
    "image/tiff": b"II*\x00",
    "image/tiff-le": b"MM\x00*",
}

# Supported MIME types per tool kind
PDF_MIMES = {"application/pdf"}
IMAGE_MIMES = set(IMAGE_SIGNATURES.keys())

ALLOWED_UPLOAD_MIMES = PDF_MIMES | IMAGE_MIMES

# Max upload size in bytes
MAX_UPLOAD_BYTES = settings.max_upload_mb * 1024 * 1024


@dataclass
class FileValidationResult:
    valid: bool
    mime_type: str = ""
    sha256: str = ""
    error_code: str = ""
    error_message: str = ""
    page_count: int = 0


def _detect_mime_by_header(data: bytes) -> str:
    """Detect MIME type using magic bytes (not extension-dependent)."""
    if data.startswith(PDF_HEADER):
        return "application/pdf"
    for mime, sig in IMAGE_SIGNATURES.items():
        if data.startswith(sig):
            return mime
    # Fallback: try Pillow
    try:
        with Image.open(io.BytesIO(data)) as img:
            return f"image/{img.format.lower()}" if img.format else ""
    except Exception:
        return ""


def _compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_uploaded_file(
    data: bytes,
    filename: str,
    expected_kind: str = "pdf_or_image",
) -> FileValidationResult:
    """Validate an uploaded file's type, size, and integrity.

    Args:
        data: Raw file bytes.
        filename: Original filename (for error messages only).
        expected_kind: ``"pdf"``, ``"image"``, or ``"pdf_or_image"``.

    Returns:
        A :class:`FileValidationResult` with validation outcome.
    """
    # Empty file
    if not data:
        return FileValidationResult(
            valid=False,
            error_code="INVALID_FILE_TYPE",
            error_message="Empty file",
        )

    # Size limit
    if len(data) > MAX_UPLOAD_BYTES:
        return FileValidationResult(
            valid=False,
            error_code="FILE_TOO_LARGE",
            error_message=(
                f"File exceeds maximum upload size of {settings.max_upload_mb} MB"
            ),
        )

    # MIME detection
    mime = _detect_mime_by_header(data)
    if not mime:
        return FileValidationResult(
            valid=False,
            error_code="INVALID_FILE_TYPE",
            error_message=f"Unrecognised file type for {filename}",
        )

    sha256 = _compute_sha256(data)

    # Validate expected kind
    if expected_kind == "pdf" and mime not in PDF_MIMES:
        return FileValidationResult(
            valid=False,
            error_code="INVALID_FILE_TYPE",
            error_message=f"Expected a PDF file, got {mime}",
        )
    if expected_kind == "image" and mime not in IMAGE_MIMES:
        return FileValidationResult(
            valid=False,
            error_code="INVALID_FILE_TYPE",
            error_message=f"Expected an image file, got {mime}",
        )

    # Additional PDF validation: try reading with PyMuPDF
    page_count = 0
    if mime in PDF_MIMES:
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(stream=data, filetype="pdf")
            page_count = doc.page_count
            doc.close()
        except Exception:
            return FileValidationResult(
                valid=False,
                error_code="INVALID_FILE_TYPE",
                error_message="File is not a valid PDF",
            )

    # Additional image validation: try opening with Pillow
    if mime in IMAGE_MIMES:
        try:
            with Image.open(io.BytesIO(data)) as img:
                img.verify()
        except Exception:
            return FileValidationResult(
                valid=False,
                error_code="INVALID_FILE_TYPE",
                error_message="File is not a valid image",
            )

    return FileValidationResult(
        valid=True,
        mime_type=mime,
        sha256=sha256,
        page_count=page_count,
    )
