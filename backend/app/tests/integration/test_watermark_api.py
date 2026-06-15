"""Integration tests for the watermark API.

Tests the full flow: file upload → preview → task creation → poll → download.
"""

import io
import time

import fitz
import pytest
from fastapi.testclient import TestClient
from PIL import Image


# ── fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def pdf_bytes() -> bytes:
    """Create a 3‑page test PDF."""
    doc = fitz.open()
    try:
        for i in range(3):
            page = doc.new_page(width=595, height=842)
            page.insert_text(fitz.Point(72, 72), f"Page {i + 1}")
        return doc.tobytes(garbage=4)
    finally:
        doc.close()


@pytest.fixture(scope="module")
def png_bytes() -> bytes:
    """Create a small test PNG."""
    img = Image.new("RGBA", (30, 30), (255, 0, 0, 200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _upload(client: TestClient, data: bytes, filename: str = "test.pdf") -> int:
    """Upload a file and return its file_id."""
    resp = client.post("/api/files", files={"file": (filename, data, "application/octet-stream")})
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["file_id"]


def _wait_for_task(client: TestClient, task_id: int, timeout: float = 30) -> dict:
    """Poll until task is done."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        resp = client.get(f"/api/tasks/{task_id}")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        if body["status"] in ("succeeded", "failed", "expired"):
            return body
        time.sleep(0.5)
    raise TimeoutError(f"Task {task_id} did not finish within {timeout}s")


# ── tests ───────────────────────────────────────────────────────────────────

class TestWatermarkText:
    """Full flow: text watermark."""

    def test_text_watermark_full_flow(self, client: TestClient, pdf_bytes: bytes) -> None:
        pdf_id = _upload(client, pdf_bytes, "contract.pdf")

        task_resp = client.post("/api/tasks", json={
            "tool_type": "watermark_pdf",
            "input_file_ids": [pdf_id],
            "params": {
                "watermark_type": "text",
                "text": "内部资料",
                "font_size": 32,
                "color": "#888888",
                "opacity": 0.25,
                "rotation": -30,
                "position": "center",
                "tile_mode": "full",
                "page_range": "all",
            },
        })
        assert task_resp.status_code in (200, 201), task_resp.text
        task = task_resp.json()

        # Poll for completion
        done = _wait_for_task(client, task["task_id"])
        assert done["status"] == "succeeded", done.get("error_message", "unknown error")
        assert len(done["output_files"]) > 0

        # Download output and verify it's a valid PDF
        out = done["output_files"][0]
        dl = client.get(out["download_url"])
        assert dl.status_code == 200
        assert dl.headers["content-type"] == "application/pdf"

        doc = fitz.open(stream=dl.content, filetype="pdf")
        assert doc.page_count == 3
        doc.close()

    def test_text_watermark_page_range(self, client: TestClient, pdf_bytes: bytes) -> None:
        pdf_id = _upload(client, pdf_bytes)

        task_resp = client.post("/api/tasks", json={
            "tool_type": "watermark_pdf",
            "input_file_ids": [pdf_id],
            "params": {
                "watermark_type": "text",
                "text": "C",
                "page_range": "1",
                "opacity": 0.5,
                "rotation": 0,
                "position": "center",
                "tile_mode": "single",
            },
        })
        assert task_resp.status_code in (200, 201)
        done = _wait_for_task(client, task_resp.json()["task_id"])
        assert done["status"] == "succeeded"
        assert len(done["output_files"]) == 1


class TestWatermarkImage:
    """Full flow: image watermark."""

    def test_image_watermark_full_flow(self, client: TestClient, pdf_bytes: bytes, png_bytes: bytes) -> None:
        pdf_id = _upload(client, pdf_bytes, "doc.pdf")
        img_id = _upload(client, png_bytes, "logo.png")

        task_resp = client.post("/api/tasks", json={
            "tool_type": "watermark_pdf",
            "input_file_ids": [pdf_id],
            "params": {
                "watermark_type": "image",
                "watermark_file_id": img_id,
                "scale": 0.3,
                "opacity": 0.5,
                "rotation": 0,
                "position": "center",
                "tile_mode": "single",
                "page_range": "all",
            },
        })
        assert task_resp.status_code in (200, 201), task_resp.text
        done = _wait_for_task(client, task_resp.json()["task_id"])
        assert done["status"] == "succeeded", done.get("error_message", "")
        assert len(done["output_files"]) > 0

        dl = client.get(done["output_files"][0]["download_url"])
        assert dl.status_code == 200

        doc = fitz.open(stream=dl.content, filetype="pdf")
        assert doc.page_count == 3
        doc.close()


class TestWatermarkErrors:
    """Error scenarios."""

    def test_missing_watermark_type(self, client: TestClient, pdf_bytes: bytes) -> None:
        pdf_id = _upload(client, pdf_bytes)
        resp = client.post("/api/tasks", json={
            "tool_type": "watermark_pdf",
            "input_file_ids": [pdf_id],
            "params": {},
        })
        assert resp.status_code in (200, 201)
        done = _wait_for_task(client, resp.json()["task_id"])
        assert done["status"] == "failed"
        assert done["error_code"] == "CONVERSION_FAILED"

    def test_image_watermark_missing_file_id(self, client: TestClient, pdf_bytes: bytes) -> None:
        pdf_id = _upload(client, pdf_bytes)
        resp = client.post("/api/tasks", json={
            "tool_type": "watermark_pdf",
            "input_file_ids": [pdf_id],
            "params": {
                "watermark_type": "image",
            },
        })
        assert resp.status_code in (200, 201)
        done = _wait_for_task(client, resp.json()["task_id"])
        assert done["status"] == "failed"
        assert done["error_code"] == "CONVERSION_FAILED"


class TestWatermarkPreview:
    """Preview endpoint."""

    def test_text_preview(self, client: TestClient, pdf_bytes: bytes) -> None:
        pdf_id = _upload(client, pdf_bytes)
        resp = client.post("/api/previews/watermark", json={
            "file_id": pdf_id,
            "watermark_type": "text",
            "params": {
                "text": "X",
                "font_size": 24,
                "color": "#FF0000",
                "opacity": 0.5,
                "rotation": 0,
                "position": "center",
                "tile_mode": "single",
                "page_range": "all",
            },
            "max_width": 200,
        })
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["page_count"] == 3
        assert body["preview_image_url"].startswith("data:image/png;base64,")

    def test_image_preview(self, client: TestClient, pdf_bytes: bytes, png_bytes: bytes) -> None:
        pdf_id = _upload(client, pdf_bytes)
        img_id = _upload(client, png_bytes, "logo.png")
        resp = client.post("/api/previews/watermark", json={
            "file_id": pdf_id,
            "watermark_type": "image",
            "params": {
                "watermark_file_id": img_id,
                "scale": 0.5,
                "opacity": 0.5,
                "rotation": 0,
                "position": "center",
                "tile_mode": "single",
            },
            "max_width": 200,
        })
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["preview_image_url"].startswith("data:image/png;base64,")

    def test_preview_404(self, client: TestClient) -> None:
        resp = client.post("/api/previews/watermark", json={
            "file_id": 99999,
            "watermark_type": "text",
            "params": {"text": "x"},
        })
        assert resp.status_code == 404

    def test_preview_missing_image_file_id(self, client: TestClient, pdf_bytes: bytes) -> None:
        pdf_id = _upload(client, pdf_bytes)
        resp = client.post("/api/previews/watermark", json={
            "file_id": pdf_id,
            "watermark_type": "image",
            "params": {},
        })
        assert resp.status_code == 422
