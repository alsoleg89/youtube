import pytest

from app.db.models import GeneratedContent, Source, Validation


@pytest.mark.asyncio
async def test_approved_source_returns_content(client, db_session):
    source = Source(
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        source_type="youtube",
        status="approved",
        progress_json={"stage": "done", "percent": 100},
    )
    db_session.add(source)
    await db_session.commit()
    await db_session.refresh(source)

    gc = GeneratedContent(
        source_id=source.id,
        content_payload={
            "medium_text": "medium content",
            "habr_text": "habr content",
            "linkedin_text": "linkedin content",
            "research_article": "research content",
            "banana_video_prompt": {
                "style_summary": "cinematic",
                "scenes": [
                    {
                        "scene_number": 1,
                        "visual_prompt": "A dark room",
                        "voiceover_text": "Текст",
                    }
                ],
            },
            "reduce_summary_text": "summary",
        },
    )
    db_session.add(gc)
    await db_session.commit()

    resp = await client.get(f"/api/sources/{source.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "approved"
    assert data["content_payload"] is not None
    assert "medium_text" in data["content_payload"]
    assert "banana_video_prompt" in data["content_payload"]


@pytest.mark.asyncio
async def test_needs_review_no_content_payload(client, db_session):
    """CRITICAL-9: needs_review must NOT leak content_payload."""
    source = Source(
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        source_type="youtube",
        status="needs_review",
        progress_json={"stage": "done", "percent": 100},
    )
    db_session.add(source)
    await db_session.commit()
    await db_session.refresh(source)

    gc = GeneratedContent(
        source_id=source.id,
        content_payload={"medium_text": "should not appear"},
    )
    db_session.add(gc)
    await db_session.commit()

    val = Validation(
        source_id=source.id,
        overall_verdict="needs_revision",
        report_json={"medium": {"checks": [{"name": "hallucination", "passed": False}]}},
    )
    db_session.add(val)
    await db_session.commit()

    resp = await client.get(f"/api/sources/{source.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "needs_review"
    assert data["content_payload"] is None
    assert data["validation_report"] is not None


@pytest.mark.asyncio
async def test_queued_source_no_content(client, db_session):
    source = Source(
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        source_type="youtube",
        status="queued",
    )
    db_session.add(source)
    await db_session.commit()
    await db_session.refresh(source)

    resp = await client.get(f"/api/sources/{source.id}")
    data = resp.json()
    assert data["content_payload"] is None
    assert data["validation_report"] is None
