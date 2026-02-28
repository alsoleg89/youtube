import uuid
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.db.models import Source


@pytest.mark.asyncio
async def test_create_source_youtube(client: AsyncClient, db_session):
    with patch("app.api.sources.process_source_task") as mock_task:
        mock_task.delay.return_value = None
        resp = await client.post(
            "/api/sources",
            json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "source_type": "youtube"},
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["source_type"] == "youtube"
    assert data["status"] == "queued"
    assert "source_id" in data
    mock_task.delay.assert_called_once()


@pytest.mark.asyncio
async def test_create_source_web(client: AsyncClient, db_session):
    with patch("app.api.sources.process_source_task") as mock_task:
        mock_task.delay.return_value = None
        resp = await client.post(
            "/api/sources",
            json={"url": "https://example.com/article", "source_type": "web"},
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["source_type"] == "web"


@pytest.mark.asyncio
async def test_create_source_invalid_youtube_url(client: AsyncClient, db_session):
    resp = await client.post(
        "/api/sources",
        json={"url": "not-a-valid-url", "source_type": "youtube"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_source_ssrf_file_scheme(client: AsyncClient, db_session):
    """CRITICAL-11: file:// scheme must be blocked."""
    resp = await client.post(
        "/api/sources",
        json={"url": "file:///etc/passwd", "source_type": "web"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_source_ssrf_ftp_scheme(client: AsyncClient, db_session):
    """CRITICAL-11: ftp:// scheme must be blocked."""
    resp = await client.post(
        "/api/sources",
        json={"url": "ftp://internal-server/data", "source_type": "web"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_source_not_found(client: AsyncClient, db_session):
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/api/sources/{fake_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_source_queued(client: AsyncClient, db_session):
    source = Source(url="https://www.youtube.com/watch?v=dQw4w9WgXcQ", source_type="youtube")
    db_session.add(source)
    await db_session.commit()
    await db_session.refresh(source)

    resp = await client.get(f"/api/sources/{source.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "queued"
    assert data["source_type"] == "youtube"


@pytest.mark.asyncio
async def test_regenerate_wrong_status(client: AsyncClient, db_session):
    source = Source(url="https://www.youtube.com/watch?v=dQw4w9WgXcQ", source_type="youtube", status="queued")
    db_session.add(source)
    await db_session.commit()
    await db_session.refresh(source)

    resp = await client.post(f"/api/sources/{source.id}/regenerate")
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
