"""Integration tests for PDF to Word conversion.

Tests the full flow: file upload → task creation → poll → download.
"""

import io
import time

import fitz
import pytest
from fastapi.testclient import TestClient


# ── fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def pdf_text_bytes() -> bytes:
    """Create a 3-page text-based test PDF."""
    doc = fitz.open()
    try:
        for i in range(3):
            page = doc.new_page(width=595, height=842)
            page.insert_text(fitz.Point(72, 72), f"这是第 {i + 1} 页的测试内容。Hello World!")
        return doc.tobytes(garbage=4)
    finally:
        doc.close()


@pytest.fixture(scope="module")
def pdf_scanned_bytes() -> bytes:
    """Create a 1-page PDF with no extractable text (simulating scanned)."""
    doc = fitz.open()
    try:
        page = doc.new_page(width=595, height=842)
        # Insert an image instead of text to simulate a scanned page
        # Actually we can just not insert any text — the page is empty
        return doc.tobytes(garbage=4)
    finally:
        doc.close()


def _upload(client: TestClient, data: bytes, filename: str = "test.pdf") -> int:
    """Upload a file and return its file_id."""
    resp = client.post("/api/files", files={"file": (filename, data, "application/octet-stream")})
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["file_id"]


def _wait_for_task(client: TestClient, task_id: int, timeout: float = 60) -> dict:
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

class TestPdfToWord:
    """Full flow: PDF to Word conversion."""

    def test_text_pdf_conversion(self, client: TestClient, pdf_text_bytes: bytes) -> None:
        """A text-based PDF should convert to a valid .docx."""
        pdf_id = _upload(client, pdf_text_bytes, "contract.pdf")

        task_resp = client.post("/api/tasks", json={
            "tool_type": "pdf_to_word",
            "input_file_ids": [pdf_id],
            "params": {},
        })
        assert task_resp.status_code in (200, 201), task_resp.text
        task = task_resp.json()

        done = _wait_for_task(client, task["task_id"])
        assert done["status"] == "succeeded", done.get("error_message", "unknown error")
        assert len(done["output_files"]) > 0

        # Download output and verify it's a valid .docx (ZIP with word/document.xml)
        out = done["output_files"][0]
        dl = client.get(out["download_url"])
        assert dl.status_code == 200
        assert dl.headers["content-type"] == (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

        # Verify it's a valid ZIP
        import zipfile
        with zipfile.ZipFile(io.BytesIO(dl.content)) as zf:
            assert "word/document.xml" in zf.namelist()

    def test_text_pdf_warning_not_present(self, client: TestClient, pdf_text_bytes: bytes) -> None:
        """A text PDF should NOT trigger the scanned-document warning."""
        pdf_id = _upload(client, pdf_text_bytes, "report.pdf")

        task_resp = client.post("/api/tasks", json={
            "tool_type": "pdf_to_word",
            "input_file_ids": [pdf_id],
            "params": {},
        })
        assert task_resp.status_code in (200, 201)
        done = _wait_for_task(client, task_resp.json()["task_id"])
        assert done["status"] == "succeeded"
        # No warnings for text PDFs
        warnings = done.get("warnings", [])
        assert len(warnings) == 0

    def test_empty_pdf_conversion(self, client: TestClient, pdf_scanned_bytes: bytes) -> None:
        """An empty/near-empty PDF should still produce a valid .docx."""
        pdf_id = _upload(client, pdf_scanned_bytes, "blank.pdf")

        task_resp = client.post("/api/tasks", json={
            "tool_type": "pdf_to_word",
            "input_file_ids": [pdf_id],
            "params": {},
        })
        assert task_resp.status_code in (200, 201)
        done = _wait_for_task(client, task_resp.json()["task_id"])
        assert done["status"] == "succeeded"

        out = done["output_files"][0]
        dl = client.get(out["download_url"])
        assert dl.status_code == 200

        import zipfile
        with zipfile.ZipFile(io.BytesIO(dl.content)) as zf:
            assert "word/document.xml" in zf.namelist()
