import logging
import uuid

from app.core.config import settings
from app.db.models import GeneratedContent, Transcript, Validation, Video, utcnow
from app.db.sync_session import SyncSessionLocal
from app.providers.openai_provider import OpenAIProvider
from app.services.generator import GeneratorService
from app.services.transcription import TranscriptionService
from app.services.validator import ValidatorService
from app.services.youtube import YouTubeService
from app.workers.celery_app import celery_app
from app.workers.cleanup import cleanup_video_tmp

logger = logging.getLogger(__name__)


def _update_video(session, video_id: uuid.UUID, **kwargs) -> Video:
    video = session.query(Video).filter(Video.id == video_id).first()
    for k, v in kwargs.items():
        setattr(video, k, v)
    video.updated_at = utcnow()
    session.commit()
    return video


def _classify_error(msg: str) -> str:
    for code in ("video_too_long", "too_many_chunks", "transcript_unavailable"):
        if code in msg:
            return code
    if "llm" in msg.lower() or "openai" in msg.lower():
        return "llm_error"
    return "internal_error"


@celery_app.task(bind=True)
def process_video_task(self, video_id_str: str) -> None:
    video_id = uuid.UUID(video_id_str)
    session = SyncSessionLocal()

    try:
        video = session.query(Video).filter(Video.id == video_id).first()
        if not video:
            logger.error("Video %s not found", video_id)
            return

        llm = OpenAIProvider()
        youtube_svc = YouTubeService()
        transcription_svc = TranscriptionService()
        generator_svc = GeneratorService(llm)
        validator_svc = ValidatorService(llm)

        # --- Step 1: Extract ------------------------------------------------
        _update_video(
            session,
            video_id,
            status="extracting",
            progress_json={"stage": "extracting", "percent": 0},
        )
        extract_result = youtube_svc.extract(video.url, video_id_str)
        _update_video(
            session,
            video_id,
            progress_json={"stage": "extracting", "percent": 10},
        )

        # --- Step 2: Transcribe ---------------------------------------------
        _update_video(
            session,
            video_id,
            status="transcribing",
            progress_json={"stage": "transcribing", "percent": 10},
        )

        if extract_result["source"] == "captions":
            raw_text = extract_result["text"]
            meta = extract_result["meta"]
            source = "captions"
        else:
            raw_text, whisper_meta = transcription_svc.transcribe(
                extract_result["audio_path"]
            )
            meta = {**extract_result["meta"], **whisper_meta}
            source = "whisper"

        transcript_row = Transcript(
            video_id=video_id, source=source, raw_text=raw_text, meta_json=meta
        )
        session.add(transcript_row)
        session.commit()
        _update_video(
            session,
            video_id,
            progress_json={"stage": "transcribing", "percent": 30},
        )

        # --- Step 3: Chunk --------------------------------------------------
        _update_video(
            session,
            video_id,
            status="chunking",
            progress_json={"stage": "chunking", "percent": 30},
        )
        chunks = generator_svc.chunk_transcript(raw_text)
        if len(chunks) > settings.max_chunks:
            raise ValueError(
                f"too_many_chunks: {len(chunks)} exceeds {settings.max_chunks} limit"
            )
        _update_video(
            session,
            video_id,
            progress_json={"stage": "chunking", "percent": 35},
        )

        # --- Step 4: Map ----------------------------------------------------
        _update_video(
            session,
            video_id,
            status="mapping",
            progress_json={"stage": "mapping", "percent": 35},
        )
        summaries = generator_svc.map_chunks(chunks)
        _update_video(
            session,
            video_id,
            progress_json={"stage": "mapping", "percent": 60},
        )

        # --- Step 5: Reduce -------------------------------------------------
        _update_video(
            session,
            video_id,
            status="reducing",
            progress_json={"stage": "reducing", "percent": 60},
        )
        content = generator_svc.reduce(summaries)
        _save_generated_content(session, video_id, content)
        _update_video(
            session,
            video_id,
            progress_json={"stage": "reducing", "percent": 85},
        )

        # --- Step 6: Validate -----------------------------------------------
        _update_video(
            session,
            video_id,
            status="validating",
            progress_json={"stage": "validating", "percent": 85},
        )
        val_result = validator_svc.validate(content, raw_text)
        _save_validation(session, video_id, val_result)

        # --- Step 7: Finalize (with optional autofix) -----------------------
        video = session.query(Video).filter(Video.id == video_id).first()

        if (
            val_result["overall_verdict"] == "needs_revision"
            and video.regen_count == 0
        ):
            _update_video(
                session,
                video_id,
                status="reducing",
                regen_count=1,
                progress_json={"stage": "reducing", "percent": 60},
            )
            previous_texts = {
                "medium_text": content["medium_text"],
                "habr_text": content["habr_text"],
                "linkedin_text": content["linkedin_text"],
            }
            content = generator_svc.reduce(
                summaries,
                validation_report=val_result["report_json"],
                previous_texts=previous_texts,
            )
            _save_generated_content(session, video_id, content)

            _update_video(
                session,
                video_id,
                status="validating",
                progress_json={"stage": "validating", "percent": 85},
            )
            val_result = validator_svc.validate(content, raw_text)
            _save_validation(session, video_id, val_result)

        if val_result["overall_verdict"] == "approved":
            _update_video(
                session,
                video_id,
                status="approved",
                progress_json={"stage": "done", "percent": 100},
            )
        else:
            _update_video(
                session,
                video_id,
                status="needs_review",
                progress_json={"stage": "done", "percent": 100},
            )

    except Exception as e:
        logger.exception("Pipeline failed for video %s", video_id)
        error_msg = str(e)
        try:
            _update_video(
                session,
                video_id,
                status="failed",
                error_code=_classify_error(error_msg),
                error_message=error_msg,
                progress_json={"stage": "failed", "percent": 0},
            )
        except Exception:
            logger.exception("Failed to update video status to failed")
    finally:
        cleanup_video_tmp(video_id_str)
        session.close()


@celery_app.task(bind=True)
def regenerate_task(self, video_id_str: str) -> None:
    video_id = uuid.UUID(video_id_str)
    session = SyncSessionLocal()

    try:
        video = session.query(Video).filter(Video.id == video_id).first()
        if not video or video.status != "needs_review":
            return

        llm = OpenAIProvider()
        generator_svc = GeneratorService(llm)
        validator_svc = ValidatorService(llm)

        transcript_row = (
            session.query(Transcript)
            .filter(Transcript.video_id == video_id)
            .first()
        )
        if not transcript_row:
            raise ValueError("transcript_unavailable")

        latest_val = (
            session.query(Validation)
            .filter(Validation.video_id == video_id)
            .order_by(Validation.created_at.desc())
            .first()
        )
        validation_report = latest_val.report_json if latest_val else None

        gen_content = (
            session.query(GeneratedContent)
            .filter(GeneratedContent.video_id == video_id)
            .first()
        )
        previous_texts = None
        if gen_content:
            previous_texts = {
                "medium_text": gen_content.medium_text,
                "habr_text": gen_content.habr_text,
                "linkedin_text": gen_content.linkedin_text,
            }

        # Re-chunk + re-map (summaries are not persisted separately)
        _update_video(
            session,
            video_id,
            status="chunking",
            regen_count=video.regen_count + 1,
            progress_json={"stage": "chunking", "percent": 30},
        )
        chunks = generator_svc.chunk_transcript(transcript_row.raw_text)

        _update_video(
            session,
            video_id,
            status="mapping",
            progress_json={"stage": "mapping", "percent": 35},
        )
        summaries = generator_svc.map_chunks(chunks)

        _update_video(
            session,
            video_id,
            status="reducing",
            progress_json={"stage": "reducing", "percent": 60},
        )
        content = generator_svc.reduce(
            summaries,
            validation_report=validation_report,
            previous_texts=previous_texts,
        )
        _save_generated_content(session, video_id, content)

        _update_video(
            session,
            video_id,
            status="validating",
            progress_json={"stage": "validating", "percent": 85},
        )
        val_result = validator_svc.validate(content, transcript_row.raw_text)
        _save_validation(session, video_id, val_result)

        if val_result["overall_verdict"] == "approved":
            _update_video(
                session,
                video_id,
                status="approved",
                progress_json={"stage": "done", "percent": 100},
            )
        else:
            _update_video(
                session,
                video_id,
                status="needs_review",
                progress_json={"stage": "done", "percent": 100},
            )

    except Exception as e:
        logger.exception("Regeneration failed for video %s", video_id)
        try:
            _update_video(
                session,
                video_id,
                status="failed",
                error_code=_classify_error(str(e)),
                error_message=str(e),
                progress_json={"stage": "failed", "percent": 0},
            )
        except Exception:
            logger.exception("Failed to update video status to failed")
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _save_generated_content(session, video_id: uuid.UUID, content: dict) -> None:
    existing = (
        session.query(GeneratedContent)
        .filter(GeneratedContent.video_id == video_id)
        .first()
    )
    if existing:
        existing.medium_text = content["medium_text"]
        existing.habr_text = content["habr_text"]
        existing.linkedin_text = content["linkedin_text"]
        existing.reduce_summary_text = content["reduce_summary_text"]
    else:
        session.add(GeneratedContent(video_id=video_id, **content))
    session.commit()


def _save_validation(session, video_id: uuid.UUID, val_result: dict) -> None:
    session.add(
        Validation(
            video_id=video_id,
            overall_verdict=val_result["overall_verdict"],
            report_json=val_result["report_json"],
        )
    )
    session.commit()
