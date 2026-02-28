import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_async_session
from app.db.models import GeneratedContent, Validation, Video
from app.schemas.video import (
    CreateVideoRequest,
    ErrorInfo,
    ProgressInfo,
    RegenerateResponse,
    ResultInfo,
    VideoResponse,
)
from app.workers.tasks import process_video_task, regenerate_task

router = APIRouter(prefix="/api/videos", tags=["videos"])


@router.post("", status_code=201, response_model=VideoResponse)
async def create_video(
    req: CreateVideoRequest,
    session: AsyncSession = Depends(get_async_session),
):
    video = Video(url=req.url)
    session.add(video)
    await session.commit()
    await session.refresh(video)

    process_video_task.delay(str(video.id))

    return VideoResponse(
        video_id=video.id,
        status=video.status,
        progress=ProgressInfo(stage="queued", percent=0),
    )


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "video_not_found", "message": "Video not found"}},
        )

    response = VideoResponse(video_id=video.id, status=video.status)

    if video.progress_json:
        response.progress = ProgressInfo(**video.progress_json)

    if video.status == "failed":
        response.error = ErrorInfo(
            code=video.error_code or "internal_error",
            message=video.error_message or "Unknown error",
        )

    if video.status == "approved":
        gc_result = await session.execute(
            select(GeneratedContent).where(GeneratedContent.video_id == video.id)
        )
        gc = gc_result.scalar_one_or_none()
        if gc:
            response.result = ResultInfo(
                medium_text=gc.medium_text,
                habr_text=gc.habr_text,
                linkedin_text=gc.linkedin_text,
            )
    elif video.status == "needs_review":
        val_result = await session.execute(
            select(Validation)
            .where(Validation.video_id == video.id)
            .order_by(Validation.created_at.desc())
            .limit(1)
        )
        val = val_result.scalar_one_or_none()
        if val:
            response.result = ResultInfo(validation_report=val.report_json)

    return response


@router.post("/{video_id}/regenerate", response_model=RegenerateResponse)
async def regenerate_video(
    video_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "video_not_found", "message": "Video not found"}},
        )

    if video.status != "needs_review":
        raise HTTPException(
            status_code=409,
            detail={
                "error": {
                    "code": "status_conflict",
                    "message": "Video must be in needs_review status",
                }
            },
        )

    if video.regen_count >= 1:
        raise HTTPException(
            status_code=409,
            detail={
                "error": {
                    "code": "regenerate_limit",
                    "message": "Regeneration limit reached",
                }
            },
        )

    regenerate_task.delay(str(video.id))

    return RegenerateResponse(video_id=video.id, status="reducing")
