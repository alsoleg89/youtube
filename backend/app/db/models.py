import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    progress_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    regen_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    transcript: Mapped["Transcript | None"] = relationship(
        back_populates="video", uselist=False
    )
    generated_content: Mapped["GeneratedContent | None"] = relationship(
        back_populates="video", uselist=False
    )
    validations: Mapped[list["Validation"]] = relationship(
        back_populates="video", order_by="Validation.created_at"
    )


class Transcript(Base):
    __tablename__ = "transcripts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("videos.id"), unique=True
    )
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    meta_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    video: Mapped["Video"] = relationship(back_populates="transcript")


class GeneratedContent(Base):
    __tablename__ = "generated_content"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("videos.id"), unique=True
    )
    medium_text: Mapped[str] = mapped_column(Text, nullable=False)
    habr_text: Mapped[str] = mapped_column(Text, nullable=False)
    linkedin_text: Mapped[str] = mapped_column(Text, nullable=False)
    reduce_summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    video: Mapped["Video"] = relationship(back_populates="generated_content")


class Validation(Base):
    __tablename__ = "validations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("videos.id")
    )
    overall_verdict: Mapped[str] = mapped_column(String(20), nullable=False)
    report_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    video: Mapped["Video"] = relationship(back_populates="validations")
