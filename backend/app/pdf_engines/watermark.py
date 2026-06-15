"""PDF Watermark engine.

Supports text and image watermarks with configurable opacity, rotation,
position, tiling, and page range.
"""

import io
import json
import logging
from datetime import UTC, datetime

import fitz
from PIL import Image

from app.database import SessionLocal
from app.models import Task
from app.pdf_engines.page_ranges import parse_page_range
from app.services.file_service import FileService
from app.services.naming_service import build_output_filename
from app.storage import LocalStorage

logger = logging.getLogger(__name__)

storage = LocalStorage()

# 9 predefined position anchors (relative to item centre)
_POSITIONS: dict[str, tuple[float, float]] = {
    "center":         (0.50, 0.50),
    "top-left":       (0.00, 0.00),
    "top-center":     (0.50, 0.00),
    "top-right":      (1.00, 0.00),
    "left-center":    (0.00, 0.50),
    "right-center":   (1.00, 0.50),
    "bottom-left":    (0.00, 1.00),
    "bottom-center":  (0.50, 1.00),
    "bottom-right":   (1.00, 1.00),
}

_TILE_SPACING: dict[str, tuple[float, float]] = {
    "full":  (1.5, 2.0),
    "dense": (1.1, 1.2),
}


# ── public API ──────────────────────────────────────────────────────────────

def run(task: Task, db) -> list[int]:
    """Execute watermark on a PDF.

    Returns:
        List containing the single output file ID.
    """
    params: dict = json.loads(task.params) if task.params else {}
    watermark_type: str = params.get("watermark_type", "")
    if watermark_type not in ("text", "image"):
        raise ValueError("watermark_type must be 'text' or 'image'")

    input_file_ids: list[int] = json.loads(task.input_file_ids) if task.input_file_ids else []
    if not input_file_ids:
        raise ValueError("No input files specified")

    pdf_data = _load_file_bytes(input_file_ids[0])

    doc = fitz.open(stream=pdf_data, filetype="pdf")
    try:
        total_pages = doc.page_count
        if total_pages == 0:
            raise ValueError("PDF has no pages")

        page_range_str = params.get("page_range", "all")
        try:
            page_indices = parse_page_range(page_range_str, total_pages)
        except ValueError as exc:
            raise exc

        if watermark_type == "text":
            for idx in page_indices:
                _apply_text_watermark(doc.load_page(idx), params)
        else:
            # Image watermark — load via Pillow for format-agnostic handling
            wm_file_id = params.get("watermark_file_id")
            if not wm_file_id:
                raise ValueError("watermark_file_id is required for image watermark")
            image_data = _load_file_bytes(wm_file_id)
            pix = _img_bytes_to_pixmap(image_data)
            try:
                for idx in page_indices:
                    _apply_image_watermark(doc.load_page(idx), pix, params)
            finally:
                pix = None

        pdf_bytes_buf = io.BytesIO()
        doc.save(pdf_bytes_buf, garbage=4, deflate=True)
        pdf_data_out = pdf_bytes_buf.getvalue()
    finally:
        doc.close()

    original_name = _get_original_name(input_file_ids[0])
    now = datetime.now(UTC)
    output_name = build_output_filename(
        original_name,
        suffix="watermarked",
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


def generate_preview_png(
    pdf_data: bytes,
    params: dict,
    image_data: bytes | None = None,
    max_width: int = 200,
) -> bytes:
    """Generate a low‑resolution PNG preview of the first watermarked page.

    Returns PNG bytes.
    """
    doc = fitz.open(stream=pdf_data, filetype="pdf")
    try:
        if doc.page_count == 0:
            raise ValueError("PDF has no pages")

        watermark_type = params.get("watermark_type", "text")
        if watermark_type == "text":
            _apply_text_watermark(doc.load_page(0), params)
        elif watermark_type == "image" and image_data:
            pix = _img_bytes_to_pixmap(image_data)
            try:
                _apply_image_watermark(doc.load_page(0), pix, params)
            finally:
                pix = None

        page = doc.load_page(0)
        zoom = max_width / page.rect.width
        mat = fitz.Matrix(zoom, zoom)
        rendered = page.get_pixmap(matrix=mat)
        return rendered.tobytes("png")
    finally:
        doc.close()


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


def _img_bytes_to_pixmap(image_data: bytes) -> fitz.Pixmap:
    """Convert arbitrary image bytes (JPEG/PNG/WebP/…) to a PyMuPDF Pixmap.

    Relies on PyMuPDF's built-in image decoder (available since 1.19).
    """
    # Normalise via Pillow to handle all formats, then re-encode as PNG
    # which PyMuPDF can read natively.
    pil_img = Image.open(io.BytesIO(image_data))
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    return fitz.Pixmap(buf.getvalue())


def _hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    """Convert ``#RRGGBB`` to ``(r, g, b)`` floats in 0‑1 range."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return (0.5, 0.5, 0.5)
    return tuple(int(h[i: i + 2], 16) / 255.0 for i in (0, 2, 4))


def _pick_font(text: str) -> str:
    """Return a CJK font name if text contains CJK characters."""
    for ch in text:
        if '一' <= ch <= '鿿' or '　' <= ch <= '〿':
            return "china-s"
    return "helv"


def _calc_text_dimensions(text: str, fontsize: float, fontname: str) -> tuple[float, float]:
    """Return ``(width_pts, height_pts)`` of rendered text."""
    w = fitz.get_text_length(text, fontname=fontname, fontsize=fontsize)
    return w, fontsize * 1.2


def _calc_single_position(
    page_rect: fitz.Rect,
    item_w: float,
    item_h: float,
    position: str,
    margin: float = 20,
) -> tuple[float, float]:
    """Return top‑left ``(x, y)`` for a single watermark at *position*."""
    anchor = _POSITIONS.get(position, (0.5, 0.5))
    pw, ph = page_rect.width, page_rect.height

    if position == "center":
        return (pw - item_w) / 2, (ph - item_h) / 2

    ax, ay = anchor
    x = ax * (pw - item_w - 2 * margin) + margin
    y = ay * (ph - item_h - 2 * margin) + margin
    return x, y


def _calc_tile_positions(
    page_rect: fitz.Rect,
    item_w: float,
    item_h: float,
    tile_mode: str,
) -> list[tuple[float, float]]:
    """Return list of top‑left positions for tiled watermarks."""
    sx, sy = _TILE_SPACING.get(tile_mode, (1.5, 2.0))
    pw, ph = page_rect.width, page_rect.height

    positions: list[tuple[float, float]] = []
    start_x = item_w * -0.5
    start_y = item_h * -0.5

    stagger = False
    y = start_y
    while y < ph + item_h:
        offset_x = (sx * item_w * 0.5) if (tile_mode == "dense" and stagger) else 0
        x = start_x + offset_x
        while x < pw + item_w:
            positions.append((x, y))
            x += item_w * sx
        y += item_h * sy
        if tile_mode == "dense":
            stagger = not stagger

    return positions


def _apply_text_watermark(page: fitz.Page, params: dict) -> None:
    """Apply a text watermark to *page*.

    Uses the ``morph`` parameter for arbitrary rotation angles (PyMuPDF
    ``insert_text`` only supports rotation in 90° increments natively).
    """
    text = params.get("text", "Watermark")
    fontsize = params.get("font_size", 32)
    color_hex = params.get("color", "#888888")
    opacity = params.get("opacity", 0.25)
    rotation = params.get("rotation", 0)
    position = params.get("position", "center")
    tile_mode = params.get("tile_mode", "full")

    rgb = _hex_to_rgb(color_hex)
    fontname = _pick_font(text)
    rect = page.rect

    text_w, text_h = _calc_text_dimensions(text, fontsize, fontname)

    if tile_mode == "single":
        positions = [_calc_single_position(rect, text_w, text_h, position)]
    else:
        positions = _calc_tile_positions(rect, text_w, text_h, tile_mode)

    # Build a rotation matrix if angle is non‑zero
    rot_mat = fitz.Matrix(rotation) if rotation else fitz.Matrix()

    for x, y in positions:
        # Centre of rotation = centre of the text block
        cx = x + text_w / 2
        cy = y + text_h / 2
        morph = (fitz.Point(cx, cy), rot_mat) if rotation else None
        page.insert_text(
            fitz.Point(x, y),
            text,
            fontname=fontname,
            fontsize=fontsize,
            color=rgb,
            fill_opacity=opacity,
            morph=morph,
            overlay=True,
        )


def _pil_rotate_pixmap(pix: fitz.Pixmap, angle: float) -> fitz.Pixmap:
    """Rotate a PyMuPDF Pixmap by an arbitrary angle via Pillow.

    ``fitz.Pixmap.rotate()`` is not available on all platforms / versions,
    and ``page.insert_image(rotate=…)`` only supports 90° increments.
    """
    # Determine colour mode from the pixmap
    mode = "RGBA" if pix.alpha else "RGB"
    img = Image.frombuffer(mode, (pix.width, pix.height), pix.samples, "raw", mode, 0, 1)
    img = img.rotate(angle, expand=True, resample=Image.BICUBIC)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return fitz.Pixmap(buf.getvalue())


def _apply_image_watermark(page: fitz.Page, pix: fitz.Pixmap, params: dict) -> None:
    """Apply an image watermark to *page*.

    PyMuPDF's ``insert_image(rotate=…)`` only supports 0/90/180/270, so for
    arbitrary rotation angles we pre‑rotate via Pillow.  The ``alpha``
    parameter of ``insert_image`` is a dead arg in PyMuPDF 1.27.x, so
    opacity is also baked into the pixmap alpha channel via PIL.
    """
    scale = params.get("scale", 0.5)
    opacity = params.get("opacity", 0.25)
    rotation = params.get("rotation", -30)
    position = params.get("position", "center")
    tile_mode = params.get("tile_mode", "single")

    # PIL processing is needed when any of scale / rotation / opacity
    # differs from the identity (we cannot rely on PyMuPDF's alpha param).
    needs_pil = scale != 1.0 or rotation != 0 or opacity < 1.0

    if needs_pil:
        mode = "RGBA" if pix.alpha else "RGB"
        img = Image.frombuffer(mode, (pix.width, pix.height), pix.samples, "raw", mode, 0, 1)

        if scale != 1.0:
            w = max(1, int(pix.width * scale))
            h = max(1, int(pix.height * scale))
            img = img.resize((w, h), Image.BICUBIC)

        if rotation != 0:
            img = img.rotate(rotation, expand=True, resample=Image.BICUBIC)

        if opacity < 1.0:
            # Apply opacity through the alpha channel (PyMuPDF's alpha=
            # parameter is ignored in practice).
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            alpha = img.getchannel("A")
            alpha = alpha.point(lambda x: int(x * opacity))
            img.putalpha(alpha)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        pix = fitz.Pixmap(buf.getvalue())

    rect = page.rect
    img_w, img_h = pix.width, pix.height

    if tile_mode == "single":
        positions = [_calc_single_position(rect, img_w, img_h, position)]
    else:
        positions = _calc_tile_positions(rect, img_w, img_h, tile_mode)

    for x, y in positions:
        page.insert_image(
            rect=fitz.Rect(x, y, x + img_w, y + img_h),
            pixmap=pix,
            overlay=True,
            keep_proportion=True,
        )
