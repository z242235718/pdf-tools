"""Images → PDF engine.

Converts one or more images into a single PDF.

JPEG/JPG images that need no resampling are handled via *img2pdf* for
lossless encapsulation.  All other formats go through Pillow for format
normalisation, EXIF orientation correction, and optional resizing.
"""

import json
import logging
from datetime import UTC, datetime
from io import BytesIO

from PIL import Image, ImageOps

from app.database import SessionLocal
from app.models import Task
from app.services.file_service import FileService
from app.services.naming_service import build_output_filename
from app.storage import LocalStorage

logger = logging.getLogger(__name__)

storage = LocalStorage()

# JPEG magic bytes for lossless-path detection
_JPEG_MAGIC = b"\xff\xd8\xff"

# Maximum pixel dimension for in-memory processing
_MAX_IMAGE_PIXELS = 10_000


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


def _get_original_name(file_id: int) -> str:
    db = SessionLocal()
    try:
        record = FileService.get(db, file_id)
        return record.original_name if record else f"image_{file_id}"
    finally:
        db.close()


def _is_jpeg(data: bytes) -> bool:
    """Check if raw bytes represent a JPEG image."""
    return data.startswith(_JPEG_MAGIC)


def _can_lossless_encapsulate(images: list[bytes]) -> bool:
    """Check if all images can be losslessly encapsulated by img2pdf.

    img2pdf can losslessly embed JPEG when the image needs no resampling,
    no EXIF correction, and has no transparency.  We keep it simple: if
    every input starts with JPEG magic, we try the lossless path.
    """
    return all(_is_jpeg(img) for img in images)


def _process_image_with_pillow(
    data: bytes,
    idx: int,
    page_size: str = "original",
    margin: int = 0,
    fit_mode: str = "contain",
) -> Image.Image:
    """Open, fix EXIF, and optionally resize an image using Pillow.

    Returns an RGB image ready for PDF insertion.
    """
    img = Image.open(BytesIO(data))
    img = ImageOps.exif_transpose(img) or img

    # Convert to RGB (remove alpha / palette)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGBA") if img.mode == "P" else img.convert("RGB")
    if img.mode == "RGBA":
        # Composite onto white background
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        img = background
    elif img.mode == "L":
        img = img.convert("RGB")

    if page_size != "original":
        # Resize to a target dimension (simple implementation — keep aspect)
        target_w, target_h = (
            (int(x) for x in page_size.split("x", 1))
            if "x" in page_size
            else (595, 842)
        )
        if fit_mode == "contain":
            img = ImageOps.contain(img, (target_w, target_h))
        else:
            img = ImageOps.fit(img, (target_w, target_h))

    if margin > 0:
        # Add white margin
        new_w = img.width + 2 * margin
        new_h = img.height + 2 * margin
        padded = Image.new("RGB", (new_w, new_h), (255, 255, 255))
        padded.paste(img, (margin, margin))
        img = padded

    return img


def _lossless_encapsulate(
    images_data: list[bytes], original_name: str, now: datetime
) -> tuple[bytes, str]:
    """Use img2pdf for lossless JPEG → PDF encapsulation.

    Returns (pdf_bytes, output_filename).
    """
    import img2pdf

    pdf_bytes = img2pdf.convert(images_data)
    output_name = build_output_filename(
        original_name,
        extension="pdf",
        timestamp=now,
    )
    return pdf_bytes, output_name


def _pillow_render(
    images_data: list[bytes], original_name: str, now: datetime, params: dict
) -> tuple[bytes, str]:
    """Render all images through Pillow and produce a single PDF."""
    page_size = params.get("page_size", "original")
    margin = params.get("margin", 0)
    fit_mode = params.get("fit_mode", "contain")

    images_pil: list[Image.Image] = []
    for idx, data in enumerate(images_data):
        img = _process_image_with_pillow(data, idx, page_size, margin, fit_mode)
        images_pil.append(img)

    # Save as multi-page PDF
    buf = BytesIO()
    if len(images_pil) == 1:
        images_pil[0].save(buf, format="PDF", resolution=72.0)
    else:
        first, *rest = images_pil
        first.save(buf, format="PDF", resolution=72.0, save_all=True, append_images=rest)

    pdf_bytes = buf.getvalue()
    output_name = build_output_filename(
        original_name,
        extension="pdf",
        timestamp=now,
    )
    return pdf_bytes, output_name


def run(task: Task, db) -> list[int]:
    """Execute images → PDF conversion.

    Returns:
        List containing the single output file ID.
    """
    params: dict = json.loads(task.params) if task.params else {}
    input_file_ids: list[int] = json.loads(task.input_file_ids) if task.input_file_ids else []

    if not input_file_ids:
        raise ValueError("No input files specified")

    if len(input_file_ids) > 100:
        raise ValueError("Too many input images (max 100)")

    # Load all images
    images_data: list[bytes] = []
    for fid in input_file_ids:
        data = _load_input_file(fid)
        if not data:
            raise ValueError(f"Image file {fid} is empty")
        images_data.append(data)

    now = datetime.now(UTC)
    original_name = _get_original_name(input_file_ids[0])

    # Determine which path to use
    custom_output = params.get("output_name")
    base_name = custom_output or original_name

    if _can_lossless_encapsulate(images_data) and params.get("page_size", "original") == "original":
        pdf_bytes, output_name = _lossless_encapsulate(images_data, base_name, now)
    else:
        pdf_bytes, output_name = _pillow_render(images_data, base_name, now, params)

    # Store output
    key = storage.generate_key()
    storage.store_output(pdf_bytes, key)

    output_file = FileService.mark_output(
        db,
        original_name=output_name,
        mime_type="application/pdf",
        storage_key=key,
    )
    return [output_file.id]
