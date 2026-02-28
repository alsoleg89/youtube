import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, model_validator

YOUTUBE_RE = re.compile(
    r"^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[\w\-]{11}"
)
HTTPS_RE = re.compile(r"^https?://.+")
BLOCKED_SCHEMES_RE = re.compile(r"^(file|ftp|gopher|data|javascript):", re.IGNORECASE)

SourceType = Literal["youtube", "pdf", "epub", "web"]


class CreateSourceRequest(BaseModel):
    url: str
    source_type: SourceType = "youtube"

    @model_validator(mode="after")
    def validate_url_for_type(self) -> "CreateSourceRequest":
        if BLOCKED_SCHEMES_RE.match(self.url):
            raise ValueError("Blocked URL scheme — only http(s) allowed")

        if self.source_type == "youtube":
            if not YOUTUBE_RE.match(self.url):
                raise ValueError("Invalid YouTube URL")
        elif self.source_type == "web":
            if not HTTPS_RE.match(self.url):
                raise ValueError("Invalid web URL — must start with http(s)://")
        return self


class ProgressInfo(BaseModel):
    stage: str
    percent: int


class ErrorInfo(BaseModel):
    code: str
    message: str


class SourceResponse(BaseModel):
    source_id: UUID
    source_type: str
    status: str
    progress: ProgressInfo | None = None
    error: ErrorInfo | None = None
    content_payload: dict | None = None
    validation_report: dict | None = None


class RegenerateResponse(BaseModel):
    source_id: UUID
    status: str


class SourceListItem(BaseModel):
    source_id: UUID
    title: str | None = None
    source_type: str
    status: str
    created_at: datetime


class SourceListResponse(BaseModel):
    items: list[SourceListItem]
    total: int
