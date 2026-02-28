import os
import shutil
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_async_session
from app.core.rate_limit import limiter
from app.db.models import GeneratedContent, Source, Validation
from app.schemas.source import (
    CreateSourceRequest,
    ErrorInfo,
    ProgressInfo,
    RegenerateResponse,
    SourceListItem,
    SourceListResponse,
    SourceResponse,
)
from app.workers.tasks import process_source_task, regenerate_task

router = APIRouter(prefix="/api/sources", tags=["sources"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
READ_CHUNK_SIZE = 64 * 1024  # 64 KB

MAGIC_BYTES = {
    "pdf": b"%PDF",
    "epub": b"PK",
}


async def _read_limited(file: UploadFile, limit: int) -> bytes:
    """Read upload in chunks; raise 413 before exceeding RAM budget."""
    chunks: list[bytes] = []
    received = 0
    while True:
        chunk = await file.read(READ_CHUNK_SIZE)
        if not chunk:
            break
        received += len(chunk)
        if received > limit:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Max {limit} bytes ({limit // 1024 // 1024} MB).",
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _verify_magic(contents: bytes, source_type: str) -> bool:
    magic = MAGIC_BYTES.get(source_type, b"")
    return contents[: len(magic)] == magic


@router.get("", response_model=SourceListResponse)
async def list_sources(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_async_session),
):
    total_result = await session.execute(select(func.count(Source.id)))
    total = total_result.scalar_one()

    result = await session.execute(
        select(Source)
        .order_by(Source.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    sources = result.scalars().all()

    items = [
        SourceListItem(
            source_id=s.id,
            title=s.title,
            source_type=s.source_type,
            status=s.status,
            created_at=s.created_at,
        )
        for s in sources
    ]
    return SourceListResponse(items=items, total=total)


@router.post("", status_code=201, response_model=SourceResponse)
@limiter.limit("30/minute")
async def create_source(
    request: Request,
    req: CreateSourceRequest,
    session: AsyncSession = Depends(get_async_session),
):
    source = Source(url=str(req.url), source_type=req.source_type)
    session.add(source)
    await session.commit()
    await session.refresh(source)

    process_source_task.delay(str(source.id))

    return SourceResponse(
        source_id=source.id,
        source_type=source.source_type,
        status=source.status,
        progress=ProgressInfo(stage="queued", percent=0),
    )


@router.post("/upload", status_code=201, response_model=SourceResponse)
@limiter.limit("10/minute")
async def upload_source(
    request: Request,
    file: UploadFile,
    session: AsyncSession = Depends(get_async_session),
):
    if not file.filename:
        raise HTTPException(status_code=422, detail="Filename is required")

    safe_name = os.path.basename(file.filename).replace("\x00", "")
    ext = os.path.splitext(safe_name)[1].lower()
    type_map = {".pdf": "pdf", ".epub": "epub"}
    source_type = type_map.get(ext)
    if source_type is None:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type: {ext}. Allowed: .pdf, .epub",
        )

    contents = await _read_limited(file, MAX_UPLOAD_BYTES)

    if not _verify_magic(contents, source_type):
        raise HTTPException(
            status_code=422,
            detail="File content does not match declared type",
        )

    source_id = uuid.uuid4()
    work_dir = os.path.join(settings.tmp_dir, str(source_id))
    os.makedirs(work_dir, exist_ok=True)
    file_path = os.path.join(work_dir, safe_name)

    with open(file_path, "wb") as f:
        f.write(contents)

    try:
        source = Source(id=source_id, source_type=source_type, file_path=file_path)
        session.add(source)
        await session.commit()
        await session.refresh(source)
        process_source_task.delay(str(source.id))
    except Exception:
        shutil.rmtree(work_dir, ignore_errors=True)
        raise

    return SourceResponse(
        source_id=source.id,
        source_type=source.source_type,
        status=source.status,
        progress=ProgressInfo(stage="queued", percent=0),
    )


@router.get("/{source_id}", response_model=SourceResponse)
async def get_source(
    source_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "source_not_found", "message": "Source not found"}},
        )

    response = SourceResponse(
        source_id=source.id,
        source_type=source.source_type,
        status=source.status,
    )

    if source.progress_json:
        response.progress = ProgressInfo(**source.progress_json)

    if source.status == "failed":
        response.error = ErrorInfo(
            code=source.error_code or "internal_error",
            message=source.error_message or "Unknown error",
        )

    if source.status in ("approved", "needs_review"):
        gc_result = await session.execute(
            select(GeneratedContent).where(GeneratedContent.source_id == source.id)
        )
        gc = gc_result.scalar_one_or_none()
        if gc:
            response.content_payload = gc.content_payload

    if source.status == "needs_review":
        val_result = await session.execute(
            select(Validation)
            .where(Validation.source_id == source.id)
            .order_by(Validation.created_at.desc())
            .limit(1)
        )
        val = val_result.scalar_one_or_none()
        if val:
            response.validation_report = val.report_json

    return response


@router.post("/{source_id}/regenerate", response_model=RegenerateResponse)
@limiter.limit("5/minute")
async def regenerate_source(
    request: Request,
    source_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        update(Source)
        .where(
            Source.id == source_id,
            Source.status == "needs_review",
            Source.regen_count < 3,
        )
        .values(status="reducing", regen_count=Source.regen_count + 1)
        .returning(Source.id)
    )
    updated_id = result.scalar_one_or_none()
    await session.commit()

    if updated_id is None:
        existing = await session.execute(select(Source).where(Source.id == source_id))
        source = existing.scalar_one_or_none()
        if not source:
            raise HTTPException(
                status_code=404,
                detail={"error": {"code": "source_not_found", "message": "Source not found"}},
            )
        if source.status != "needs_review":
            raise HTTPException(
                status_code=409,
                detail={"error": {"code": "status_conflict", "message": "Source must be in needs_review status"}},
            )
        raise HTTPException(
            status_code=409,
            detail={"error": {"code": "regenerate_limit", "message": "Regeneration limit reached"}},
        )

    regenerate_task.delay(str(source_id))

    return RegenerateResponse(source_id=source_id, status="reducing")
