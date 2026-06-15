"""Unit tests for the watermark engine.

Tests focus on the core rendering logic by calling internal helpers
directly with synthetic PDFs and images.
"""

import io

import fitz
import pytest
from PIL import Image

# The module under test exposes helpers we can test in isolation
from app.pdf_engines.watermark import (
    _calc_single_position,
    _calc_text_dimensions,
    _calc_tile_positions,
    _hex_to_rgb,
    _img_bytes_to_pixmap,
    _pick_font,
    generate_preview_png,
)


# ── helpers ─────────────────────────────────────────────────────────────────

def _make_pdf_bytes(page_count: int = 3, page_size: tuple[float, float] = (595, 842)) -> bytes:
    """Create a minimal PDF with *page_count* A4-ish pages."""
    doc = fitz.open()
    try:
        for _ in range(page_count):
            page = doc.new_page(width=page_size[0], height=page_size[1])
            page.insert_text(fitz.Point(72, 72), "Test content")
        buf = doc.tobytes(garbage=4)
    finally:
        doc.close()
    return buf


def _make_png_bytes(width: int = 50, height: int = 50) -> bytes:
    """Create a small RGBA PNG."""
    img = Image.new("RGBA", (width, height), (255, 0, 0, 128))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_jpg_bytes(width: int = 50, height: int = 50) -> bytes:
    """Create a small JPEG."""
    img = Image.new("RGB", (width, height), (0, 128, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


_PDF_A4_1 = _make_pdf_bytes(1)
_PDF_A4_3 = _make_pdf_bytes(3)


# ── _hex_to_rgb ─────────────────────────────────────────────────────────────

class TestHexToRgb:
    def test_black(self) -> None:
        assert _hex_to_rgb("#000000") == (0.0, 0.0, 0.0)

    def test_white(self) -> None:
        assert _hex_to_rgb("#FFFFFF") == (1.0, 1.0, 1.0)

    def test_grey(self) -> None:
        assert _hex_to_rgb("#888888") == (0x88 / 255,) * 3

    def test_red(self) -> None:
        assert _hex_to_rgb("#FF0000") == (1.0, 0.0, 0.0)

    def test_missing_hash_prefix(self) -> None:
        # "123456" has 6 hex chars → parsed normally
        result = _hex_to_rgb("123456")
        assert result == (0x12 / 255, 0x34 / 255, 0x56 / 255)

    def test_too_short_falls_back(self) -> None:
        result = _hex_to_rgb("#FFF")
        assert result == (0.5, 0.5, 0.5)

    def test_empty_falls_back(self) -> None:
        result = _hex_to_rgb("")
        assert result == (0.5, 0.5, 0.5)


# ── _pick_font ──────────────────────────────────────────────────────────────

class TestPickFont:
    def test_latin_uses_helv(self) -> None:
        assert _pick_font("Hello") == "helv"

    def test_cjk_uses_china_s(self) -> None:
        assert _pick_font("内部资料") == "china-s"

    def test_mixed_uses_china_s(self) -> None:
        assert _pick_font("Hello 世界") == "china-s"

    def test_empty_string(self) -> None:
        assert _pick_font("") == "helv"


# ── _calc_text_dimensions ───────────────────────────────────────────────────

class TestCalcTextDimensions:
    def test_basic_width(self) -> None:
        w, h = _calc_text_dimensions("Hello", 12, "helv")
        assert w > 0
        assert h == 12 * 1.2

    def test_cjk_width(self) -> None:
        w, h = _calc_text_dimensions("测试文本", 16, "china-s")
        assert w > 0
        assert h == 16 * 1.2

    def test_larger_font_returns_larger_width(self) -> None:
        w8, _ = _calc_text_dimensions("Hi", 8, "helv")
        w32, _ = _calc_text_dimensions("Hi", 32, "helv")
        assert w32 > w8


# ── _calc_single_position ───────────────────────────────────────────────────

class TestCalcSinglePosition:
    RECT = fitz.Rect(0, 0, 595, 842)

    def test_center(self) -> None:
        x, y = _calc_single_position(self.RECT, 100, 20, "center")
        assert x == pytest.approx((595 - 100) / 2)
        assert y == pytest.approx((842 - 20) / 2)

    def test_top_left(self) -> None:
        x, y = _calc_single_position(self.RECT, 100, 20, "top-left")
        assert x == 20
        assert y == 20

    def test_bottom_right(self) -> None:
        x, y = _calc_single_position(self.RECT, 100, 20, "bottom-right")
        assert x == pytest.approx(595 - 100 - 20)
        assert y == pytest.approx(842 - 20 - 20)

    def test_default_is_center_for_unknown_position(self) -> None:
        x, y = _calc_single_position(self.RECT, 100, 20, "unknown")
        assert x == pytest.approx((595 - 100) / 2)
        assert y == pytest.approx((842 - 20) / 2)


# ── _calc_tile_positions ────────────────────────────────────────────────────

class TestCalcTilePositions:
    RECT = fitz.Rect(0, 0, 595, 842)
    ITEM_W = 100
    ITEM_H = 20

    def test_full_tile_returns_multiple_positions(self) -> None:
        pos = _calc_tile_positions(self.RECT, self.ITEM_W, self.ITEM_H, "full")
        assert len(pos) > 1

    def test_dense_tile_returns_more_than_full(self) -> None:
        full = _calc_tile_positions(self.RECT, self.ITEM_W, self.ITEM_H, "full")
        dense = _calc_tile_positions(self.RECT, self.ITEM_W, self.ITEM_H, "dense")
        assert len(dense) > len(full)

    def test_positions_cover_page_area(self) -> None:
        pos = _calc_tile_positions(self.RECT, self.ITEM_W, self.ITEM_H, "full")
        xs = [p[0] for p in pos]
        ys = [p[1] for p in pos]
        assert any(self.ITEM_W * -0.5 <= x <= 595 + self.ITEM_W * 0.5 for x in xs)
        assert any(self.ITEM_H * -0.5 <= y <= 842 + self.ITEM_H * 0.5 for y in ys)


# ── _img_bytes_to_pixmap ────────────────────────────────────────────────────

class TestImgBytesToPixmap:
    def test_png_loads(self) -> None:
        pix = _img_bytes_to_pixmap(_make_png_bytes())
        assert pix.width == 50
        assert pix.height == 50

    def test_jpg_loads(self) -> None:
        pix = _img_bytes_to_pixmap(_make_jpg_bytes())
        assert pix.width == 50
        assert pix.height == 50


# ── generate_preview_png ────────────────────────────────────────────────────

class TestGeneratePreviewPng:
    def test_text_preview_returns_png_bytes(self) -> None:
        pdf_data = _PDF_A4_1
        params = {
            "watermark_type": "text",
            "text": "TEST",
            "font_size": 24,
            "color": "#FF0000",
            "opacity": 0.5,
            "rotation": 0,
            "position": "center",
            "tile_mode": "single",
            "page_range": "all",
        }
        png = generate_preview_png(pdf_data, params, max_width=200)
        assert png[:8] == b"\x89PNG\r\n\x1a\n"

    def test_image_preview_returns_png_bytes(self) -> None:
        pdf_data = _PDF_A4_1
        img_data = _make_png_bytes()
        params = {
            "watermark_type": "image",
            "scale": 0.5,
            "opacity": 0.5,
            "rotation": 0,
            "position": "center",
            "tile_mode": "single",
            "page_range": "all",
        }
        png = generate_preview_png(pdf_data, params, img_data, max_width=200)
        assert png[:8] == b"\x89PNG\r\n\x1a\n"

    def test_preview_without_image_data_skips_watermark(self) -> None:
        """When image_data is None for image type, preview renders the raw page."""
        pdf_data = _PDF_A4_1
        params = {
            "watermark_type": "image",
            "scale": 0.5,
            "opacity": 0.5,
            "rotation": 0,
            "position": "center",
            "tile_mode": "single",
            "page_range": "all",
        }
        # Should not raise — missing image data just means no watermark drawn
        png = generate_preview_png(pdf_data, params, image_data=None, max_width=200)
        assert png[:8] == b"\x89PNG\r\n\x1a\n"

    def test_empty_pdf_raises(self) -> None:
        params = {"watermark_type": "text", "text": "x"}
        with pytest.raises(Exception):
            generate_preview_png(b"", params, max_width=200)

    def test_text_preview_respects_max_width(self) -> None:
        pdf_data = _PDF_A4_1
        params = {
            "watermark_type": "text",
            "text": "X",
            "font_size": 12,
            "opacity": 0.5,
            "rotation": 0,
            "position": "center",
            "tile_mode": "single",
            "page_range": "all",
        }
        png200 = generate_preview_png(pdf_data, params, max_width=200)
        png400 = generate_preview_png(pdf_data, params, max_width=400)
        assert len(png400) > len(png200)
