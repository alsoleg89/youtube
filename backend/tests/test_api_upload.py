import io
from unittest.mock import patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_upload_pdf_happy_path(client: AsyncClient, db_session):
    pdf_content = b"%PDF-1.4 fake pdf content for testing"
    with patch("app.api.sources.process_source_task") as mock_task:
        mock_task.delay.return_value = None
        resp = await client.post(
            "/api/sources/upload",
            files={"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")},
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["source_type"] == "pdf"
    assert data["status"] == "queued"
    mock_task.delay.assert_called_once()


@pytest.mark.asyncio
async def test_upload_epub_happy_path(client: AsyncClient, db_session):
    epub_content = b"PK\x03\x04 fake epub content"
    with patch("app.api.sources.process_source_task") as mock_task:
        mock_task.delay.return_value = None
        resp = await client.post(
            "/api/sources/upload",
            files={"file": ("test.epub", io.BytesIO(epub_content), "application/epub+zip")},
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["source_type"] == "epub"


@pytest.mark.asyncio
async def test_upload_too_large(client: AsyncClient, db_session):
    big_content = b"%PDF" + b"x" * (10 * 1024 * 1024)
    resp = await client.post(
        "/api/sources/upload",
        files={"file": ("big.pdf", io.BytesIO(big_content), "application/pdf")},
    )
    assert resp.status_code == 413


@pytest.mark.asyncio
async def test_upload_unsupported_type(client: AsyncClient, db_session):
    resp = await client.post(
        "/api/sources/upload",
        files={"file": ("test.docx", io.BytesIO(b"fake"), "application/vnd.openxmlformats")},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_upload_magic_bytes_mismatch(client: AsyncClient, db_session):
    """CRITICAL-10: exe renamed to .pdf should be rejected by magic bytes check."""
    resp = await client.post(
        "/api/sources/upload",
        files={"file": ("exploit.pdf", io.BytesIO(b"MZ\x90\x00evil"), "application/pdf")},
    )
    assert resp.status_code == 422
    assert "does not match" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_upload_path_traversal(client: AsyncClient, db_session):
    """CRITICAL-2: path traversal in filename must be neutralized."""
    pdf_content = b"%PDF-1.4 safe content"
    with patch("app.api.sources.process_source_task") as mock_task:
        mock_task.delay.return_value = None
        resp = await client.post(
            "/api/sources/upload",
            files={"file": ("../../etc/cron.d/evil.pdf", io.BytesIO(pdf_content), "application/pdf")},
        )

    assert resp.status_code == 201
