import re
from uuid import UUID

from pydantic import BaseModel, field_validator

YOUTUBE_RE = re.compile(
    r"^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[\w\-]{11}"
)


class CreateVideoRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_youtube_url(cls, v: str) -> str:
        if not YOUTUBE_RE.match(v):
            raise ValueError("Invalid YouTube URL")
        return v


class ProgressInfo(BaseModel):
    stage: str
    percent: int


class ErrorInfo(BaseModel):
    code: str
    message: str


class ResultInfo(BaseModel):
    medium_text: str | None = None
    habr_text: str | None = None
    linkedin_text: str | None = None
    validation_report: dict | None = None


class VideoResponse(BaseModel):
    video_id: UUID
    status: str
    progress: ProgressInfo | None = None
    error: ErrorInfo | None = None
    result: ResultInfo | None = None


class RegenerateResponse(BaseModel):
    video_id: UUID
    status: str
