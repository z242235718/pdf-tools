"""Integration tests for PDF splitting."""

import io
import time
import zipfile

import fitz
import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader


@pytest.fixture(scope="module")
def pdf_bytes() -> bytes:
    """Create a 3-page test PDF."""
    doc = fitz.open()
    try:
        for i in range(3):
            page = doc.new_page(width=595, height=842)
            page.insert_text(fitz.Point(72, 72), f"Page {i + 1}")
        return doc.tobytes(garbage=4)
    finally:
        doc.close()


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


class TestSplitPdf:
    """Full flow: PDF split."""

    def test_single_page_split_filename_contains_source_page(
        self, client: TestClient, pdf_bytes: bytes,
    ) -> None:
        pdf_id = _upload(client, pdf_bytes, "contract.pdf")

        task_resp = client.post("/api/tasks", json={
            "tool_type": "split_pdf",
            "input_file_ids": [pdf_id],
            "params": {"page_range": "2"},
        })
        assert task_resp.status_code in (200, 201), task_resp.text

        done = _wait_for_task(client, task_resp.json()["task_id"])
        assert done["status"] == "succeeded", done.get("error_message", "unknown error")
        assert len(done["output_files"]) == 1

        out = done["output_files"][0]
        assert out["filename"].startswith("output_contract_page_002_")
        assert out["filename"].endswith(".pdf")

        dl = client.get(out["download_url"])
        assert dl.status_code == 200
        assert dl.headers["content-type"] == "application/pdf"

        reader = PdfReader(io.BytesIO(dl.content))
        assert len(reader.pages) == 1

    def test_multi_page_split_zip_entries_contain_source_pages(
        self, client: TestClient, pdf_bytes: bytes,
    ) -> None:
        pdf_id = _upload(client, pdf_bytes, "contract.pdf")

        task_resp = client.post("/api/tasks", json={
            "tool_type": "split_pdf",
            "input_file_ids": [pdf_id],
            "params": {"page_range": "1,3"},
        })
        assert task_resp.status_code in (200, 201), task_resp.text

        done = _wait_for_task(client, task_resp.json()["task_id"])
        assert done["status"] == "succeeded", done.get("error_message", "unknown error")
        assert len(done["output_files"]) == 1

        out = done["output_files"][0]
        assert out["filename"].startswith("output_contract_split_")
        assert out["filename"].endswith(".zip")

        dl = client.get(out["download_url"])
        assert dl.status_code == 200
        assert dl.headers["content-type"] in ("application/zip", "application/x-zip-compressed")

        with zipfile.ZipFile(io.BytesIO(dl.content)) as zf:
            names = zf.namelist()
            assert len(names) == 2
            assert len(names) == len(set(names))
            assert any("page_001" in name for name in names)
            assert any("page_003" in name for name in names)

            for name in names:
                assert name.startswith("output_contract_page_")
                assert name.endswith(".pdf")
                reader = PdfReader(io.BytesIO(zf.read(name)))
                assert len(reader.pages) == 1

    def test_split_filename_keeps_page_suffix_with_unsafe_source_name(
        self, client: TestClient, pdf_bytes: bytes,
    ) -> None:
        pdf_id = _upload(client, pdf_bytes, "合同:版本?测试.pdf")

        task_resp = client.post("/api/tasks", json={
            "tool_type": "split_pdf",
            "input_file_ids": [pdf_id],
            "params": {"page_range": "1"},
        })
        assert task_resp.status_code in (200, 201), task_resp.text

        done = _wait_for_task(client, task_resp.json()["task_id"])
        assert done["status"] == "succeeded", done.get("error_message", "unknown error")

        filename = done["output_files"][0]["filename"]
        assert "page_001" in filename
        assert filename.endswith(".pdf")
        assert not any(char in filename for char in '<>:"/\\|?*')
