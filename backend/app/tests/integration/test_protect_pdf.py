"""Integration tests for PDF copyright protection.

Tests the full flow: file upload → task creation → poll → download,
and verifies that fingerprint records are created and queryable.
"""

import io
import time

import fitz
import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader


# ── fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def pdf_bytes() -> bytes:
    """Create a 3-page text-based test PDF."""
    doc = fitz.open()
    try:
        for i in range(3):
            page = doc.new_page(width=595, height=842)
            page.insert_text(fitz.Point(72, 72), f"这是第 {i + 1} 页测试内容。")
        return doc.tobytes(garbage=4)
    finally:
        doc.close()


def _upload(client: TestClient, data: bytes, filename: str = "document.pdf") -> int:
    resp = client.post("/api/files", files={"file": (filename, data, "application/octet-stream")})
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["file_id"]


def _wait_for_task(client: TestClient, task_id: int, timeout: float = 60) -> dict:
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

class TestProtectPdf:
    """Full flow: PDF copyright protection."""

    def test_protect_pdf_success(self, client: TestClient, pdf_bytes: bytes) -> None:
        """A PDF protected with visible text should produce a valid output PDF."""
        pdf_id = _upload(client, pdf_bytes, "report.pdf")

        task_resp = client.post("/api/tasks", json={
            "tool_type": "protect_pdf",
            "input_file_ids": [pdf_id],
            "params": {
                "visible_text": "授权给：张三",
                "add_qrcode": True,
                "set_permissions": False,
                "page_range": "all",
            },
        })
        assert task_resp.status_code in (200, 201), task_resp.text
        task = task_resp.json()

        done = _wait_for_task(client, task["task_id"])
        assert done["status"] == "succeeded", done.get("error_message", "unknown error")
        assert len(done["output_files"]) > 0

        # Download and verify it's a valid PDF
        out = done["output_files"][0]
        dl = client.get(out["download_url"])
        assert dl.status_code == 200
        assert dl.headers["content-type"] == "application/pdf"

        reader = PdfReader(io.BytesIO(dl.content))
        assert len(reader.pages) == 3

    def test_fingerprint_record_created(self, client: TestClient, pdf_bytes: bytes) -> None:
        """After protection, a fingerprint record should exist and be queryable."""
        pdf_id = _upload(client, pdf_bytes)

        task_resp = client.post("/api/tasks", json={
            "tool_type": "protect_pdf",
            "input_file_ids": [pdf_id],
            "params": {"visible_text": "授权给：李四"},
        })
        done = _wait_for_task(client, task_resp.json()["task_id"])
        assert done["status"] == "succeeded"

        # Download the output to extract fingerprint_id from metadata
        out = done["output_files"][0]
        dl = client.get(out["download_url"])
        reader = PdfReader(io.BytesIO(dl.content))
        meta = reader.metadata
        assert meta is not None
        fp_id = meta.get("/fingerprint_id", None)
        assert fp_id, "fingerprint_id not found in PDF metadata"

        # Query via trace API
        trace_resp = client.post("/api/trace/query", json={"fingerprint_id": fp_id})
        assert trace_resp.status_code == 200, trace_resp.text
        trace_data = trace_resp.json()
        assert trace_data["fingerprint_id"] == fp_id
        assert trace_data["visible_text"] == "授权给：李四"
        assert trace_data["source_file_id"] == pdf_id

    def test_protect_pdf_with_permissions(self, client: TestClient, pdf_bytes: bytes) -> None:
        """With set_permissions=True, the output PDF should be encrypted."""
        pdf_id = _upload(client, pdf_bytes)

        task_resp = client.post("/api/tasks", json={
            "tool_type": "protect_pdf",
            "input_file_ids": [pdf_id],
            "params": {
                "visible_text": "授权给：王五",
                "set_permissions": True,
                "add_qrcode": False,
            },
        })
        done = _wait_for_task(client, task_resp.json()["task_id"])
        assert done["status"] == "succeeded"

        out = done["output_files"][0]
        dl = client.get(out["download_url"])

        # Try opening without password — should need one
        reader = PdfReader(io.BytesIO(dl.content))
        assert reader.is_encrypted, "PDF should be encrypted when set_permissions=True"

    def test_trace_query_not_found(self, client: TestClient) -> None:
        """Querying a non-existent fingerprint should return 404."""
        resp = client.post("/api/trace/query", json={"fingerprint_id": "nonexistent123"})
        assert resp.status_code == 404

    def test_protect_pdf_metadata_contains_fingerprint(
        self, client: TestClient, pdf_bytes: bytes,
    ) -> None:
        """The output PDF should have fingerprint metadata embedded."""
        pdf_id = _upload(client, pdf_bytes, "metadata_test.pdf")

        task_resp = client.post("/api/tasks", json={
            "tool_type": "protect_pdf",
            "input_file_ids": [pdf_id],
            "params": {"visible_text": "授权给：测试"},
        })
        done = _wait_for_task(client, task_resp.json()["task_id"])
        assert done["status"] == "succeeded"

        out = done["output_files"][0]
        dl = client.get(out["download_url"])
        reader = PdfReader(io.BytesIO(dl.content))
        meta = reader.metadata
        assert meta is not None
        assert meta.get("/fingerprint_id") is not None
        assert meta.get("/fingerprint_visible_text") == "授权给：测试"
