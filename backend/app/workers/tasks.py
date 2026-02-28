import logging
import uuid

from app.core.config import settings
from app.db.models import GeneratedContent, Source, Transcript, Validation, utcnow
from app.db.sync_session import SyncSessionLocal
from app.providers.factory import get_llm_provider
from app.services.extractors import get_extractor
from app.services.generator import PAYLOAD_KEY_TO_PLATFORM, GeneratorService
from app.services.transcription import TranscriptionService
from app.services.validator import ValidatorService
from app.workers.celery_app import celery_app
from app.workers.cleanup import cleanup_source_tmp

logger = logging.getLogger(__name__)


def _update_source(session, source_id: uuid.UUID, **kwargs) -> Source:
    source = session.query(Source).filter(Source.id == source_id).first()
    if source is None:
        raise ValueError(f"Source {source_id} not found during update")
    for k, v in kwargs.items():
        setattr(source, k, v)
    source.updated_at = utcnow()
    session.commit()
    return source


def _classify_error(msg: str) -> str:
    for code in ("video_too_long", "too_many_chunks", "transcript_unavailable"):
        if code in msg:
            return code
    if "llm" in msg.lower() or "openai" in msg.lower():
        return "llm_error"
    return "internal_error"


def _get_failed_channels(report_json: dict) -> list[str]:
    """Return payload keys of channels that failed validation."""
    failed: list[str] = []
    for payload_key, platform in PAYLOAD_KEY_TO_PLATFORM.items():
        entry = report_json.get(platform) or report_json.get(payload_key)
        if entry is None:
            continue
        if "checks" in entry:
            if any(not c.get("passed", False) for c in entry["checks"]):
                failed.append(payload_key)
        elif not entry.get("passed", False):
            failed.append(payload_key)
    return failed


def _merge_validation(old_report: dict, new_report: dict) -> dict:
    """Merge new partial validation into existing full report, recompute verdict."""
    merged = {**old_report, **new_report}
    all_passed = True
    for entry in merged.values():
        if "checks" in entry:
            if any(not c.get("passed", False) for c in entry["checks"]):
                all_passed = False
        elif not entry.get("passed", False):
            all_passed = False
    verdict = "approved" if all_passed else "needs_revision"
    return {"overall_verdict": verdict, "report_json": merged}


@celery_app.task(bind=True)
def process_source_task(self, source_id_str: str) -> None:
    source_id = uuid.UUID(source_id_str)
    session = SyncSessionLocal()

    try:
        source = session.query(Source).filter(Source.id == source_id).first()
        if not source:
            logger.error("Source %s not found", source_id)
            return

        llm = get_llm_provider()
        transcription_svc = TranscriptionService()
        generator_svc = GeneratorService(llm)
        validator_svc = ValidatorService(llm)

        extractor = get_extractor(source.source_type)

        # --- Step 1: Extract ------------------------------------------------
        _update_source(
            session,
            source_id,
            status="extracting",
            progress_json={"stage": "extracting", "percent": 0},
        )

        # Check for cached transcript (same URL processed before)
        cached_transcript = None
        if source.url and source.source_type == "youtube":
            cached_transcript = (
                session.query(Transcript)
                .join(Source, Source.id == Transcript.source_id)
                .filter(
                    Source.url == source.url,
                    Source.id != source_id,
                )
                .order_by(Transcript.id.desc())
                .first()
            )

        if cached_transcript:
            raw_text = cached_transcript.raw_text
            meta = cached_transcript.meta_json or {}
            source_label = cached_transcript.source_label
            title = meta.get("title") or source.url or ""
            logger.info("Reusing cached transcript for URL %s", source.url)
        else:
            extract_result = extractor.extract(source)
            title = extract_result.meta.get("title") or source.url or ""
            if source.file_path and not extract_result.meta.get("title"):
                import os
                title = os.path.splitext(os.path.basename(source.file_path))[0]

        _update_source(
            session,
            source_id,
            title=title,
            progress_json={"stage": "extracting", "percent": 10},
        )

        # --- Step 2: Transcribe (YouTube whisper only) ----------------------
        _update_source(
            session,
            source_id,
            status="transcribing",
            progress_json={"stage": "transcribing", "percent": 10},
        )

        if not cached_transcript:
            if extract_result.needs_transcription:
                raw_text, whisper_meta = transcription_svc.transcribe(
                    extract_result.audio_path
                )
                meta = {**extract_result.meta, **whisper_meta}
                source_label = "whisper"
            else:
                raw_text = extract_result.text
                meta = extract_result.meta
                source_label = meta.get("source", source.source_type)

        transcript_row = Transcript(
            source_id=source_id,
            source_label=source_label,
            raw_text=raw_text,
            meta_json=meta,
        )
        session.add(transcript_row)
        session.commit()
        _update_source(
            session,
            source_id,
            progress_json={"stage": "transcribing", "percent": 30},
        )

        # --- Step 3: Chunk --------------------------------------------------
        _update_source(
            session,
            source_id,
            status="chunking",
            progress_json={"stage": "chunking", "percent": 30},
        )
        chunks = generator_svc.chunk_transcript(raw_text)
        if len(chunks) > settings.max_chunks:
            raise ValueError(
                f"too_many_chunks: {len(chunks)} exceeds {settings.max_chunks} limit"
            )
        _update_source(
            session,
            source_id,
            progress_json={"stage": "chunking", "percent": 35},
        )

        # --- Step 4: Map ----------------------------------------------------
        _update_source(
            session,
            source_id,
            status="mapping",
            progress_json={"stage": "mapping", "percent": 35},
        )
        summaries = generator_svc.map_chunks(chunks)
        _update_source(
            session,
            source_id,
            progress_json={"stage": "mapping", "percent": 60},
        )

        # --- Step 5: Reduce -------------------------------------------------
        _update_source(
            session,
            source_id,
            status="reducing",
            progress_json={"stage": "reducing", "percent": 60},
        )
        content = generator_svc.reduce(summaries)
        reduce_summary = content.pop("reduce_summary_text", "")
        _save_generated_content(session, source_id, content)
        _update_source(
            session,
            source_id,
            progress_json={"stage": "reducing", "percent": 85},
        )

        # --- Step 6: Validate -----------------------------------------------
        _update_source(
            session,
            source_id,
            status="validating",
            progress_json={"stage": "validating", "percent": 85},
        )
        validation_source_text = reduce_summary or raw_text
        val_result = validator_svc.validate(content, validation_source_text)
        _save_validation(session, source_id, val_result)

        # --- Step 7: Finalize (with optional partial autofix) ----------------
        source = session.query(Source).filter(Source.id == source_id).first()

        if (
            val_result["overall_verdict"] == "needs_revision"
            and source.regen_count == 0
        ):
            failed = _get_failed_channels(val_result["report_json"])
            if failed:
                _update_source(
                    session,
                    source_id,
                    status="reducing",
                    regen_count=1,
                    progress_json={"stage": "reducing", "percent": 60},
                )
                patched = generator_svc.reduce(
                    summaries,
                    validation_report=val_result["report_json"],
                    previous_texts=content,
                    channels=failed,
                )
                patched.pop("reduce_summary_text", None)
                content = {**content, **patched}
                _save_generated_content(session, source_id, content)

                _update_source(
                    session,
                    source_id,
                    status="validating",
                    progress_json={"stage": "validating", "percent": 85},
                )
                new_val = validator_svc.validate(content, validation_source_text, channels=failed)
                val_result = _merge_validation(
                    val_result["report_json"], new_val["report_json"]
                )
                _save_validation(session, source_id, val_result)

        if val_result["overall_verdict"] == "approved":
            _update_source(
                session,
                source_id,
                status="approved",
                progress_json={"stage": "done", "percent": 100},
            )
        else:
            _update_source(
                session,
                source_id,
                status="needs_review",
                progress_json={"stage": "done", "percent": 100},
            )

    except Exception as e:
        logger.exception("Pipeline failed for source %s", source_id)
        error_msg = str(e)
        session.rollback()
        try:
            _update_source(
                session,
                source_id,
                status="failed",
                error_code=_classify_error(error_msg),
                error_message=error_msg,
                progress_json={"stage": "failed", "percent": 0},
            )
        except Exception:
            logger.exception("Failed to update source status to failed")
    finally:
        cleanup_source_tmp(source_id_str)
        session.close()


@celery_app.task(bind=True)
def regenerate_task(self, source_id_str: str) -> None:
    source_id = uuid.UUID(source_id_str)
    session = SyncSessionLocal()

    try:
        source = session.query(Source).filter(Source.id == source_id).first()
        if not source or source.status not in ("needs_review", "reducing"):
            return

        llm = get_llm_provider()
        generator_svc = GeneratorService(llm)
        validator_svc = ValidatorService(llm)

        transcript_row = (
            session.query(Transcript)
            .filter(Transcript.source_id == source_id)
            .first()
        )
        if not transcript_row:
            raise ValueError("transcript_unavailable")

        latest_val = (
            session.query(Validation)
            .filter(Validation.source_id == source_id)
            .order_by(Validation.created_at.desc())
            .first()
        )
        validation_report = latest_val.report_json if latest_val else None

        gen_content = (
            session.query(GeneratedContent)
            .filter(GeneratedContent.source_id == source_id)
            .first()
        )
        previous_texts = gen_content.content_payload if gen_content else None

        failed = _get_failed_channels(validation_report) if validation_report else []
        if not failed:
            logger.info("No failed channels to regenerate for %s", source_id)
            return

        _update_source(
            session,
            source_id,
            status="chunking",
            progress_json={"stage": "chunking", "percent": 30},
        )
        chunks = generator_svc.chunk_transcript(transcript_row.raw_text)

        _update_source(
            session,
            source_id,
            status="mapping",
            progress_json={"stage": "mapping", "percent": 35},
        )
        summaries = generator_svc.map_chunks(chunks)

        _update_source(
            session,
            source_id,
            status="reducing",
            progress_json={"stage": "reducing", "percent": 60},
        )
        patched = generator_svc.reduce(
            summaries,
            validation_report=validation_report,
            previous_texts=previous_texts,
            channels=failed,
        )
        reduce_summary = patched.pop("reduce_summary_text", "")
        content = {**(previous_texts or {}), **patched}
        _save_generated_content(session, source_id, content)

        _update_source(
            session,
            source_id,
            status="validating",
            progress_json={"stage": "validating", "percent": 85},
        )
        validation_source_text = reduce_summary or transcript_row.raw_text
        new_val = validator_svc.validate(
            content, validation_source_text, channels=failed
        )
        val_result = _merge_validation(
            validation_report, new_val["report_json"]
        )
        _save_validation(session, source_id, val_result)

        if val_result["overall_verdict"] == "approved":
            _update_source(
                session,
                source_id,
                status="approved",
                progress_json={"stage": "done", "percent": 100},
            )
        else:
            _update_source(
                session,
                source_id,
                status="needs_review",
                progress_json={"stage": "done", "percent": 100},
            )

    except Exception as e:
        logger.exception("Regeneration failed for source %s", source_id)
        session.rollback()
        try:
            _update_source(
                session,
                source_id,
                status="failed",
                error_code=_classify_error(str(e)),
                error_message=str(e),
                progress_json={"stage": "failed", "percent": 0},
            )
        except Exception:
            logger.exception("Failed to update source status to failed")
    finally:
        cleanup_source_tmp(source_id_str)
        session.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _save_generated_content(session, source_id: uuid.UUID, content: dict) -> None:
    existing = (
        session.query(GeneratedContent)
        .filter(GeneratedContent.source_id == source_id)
        .first()
    )
    if existing:
        existing.content_payload = content
    else:
        session.add(GeneratedContent(source_id=source_id, content_payload=content))
    session.commit()


def _save_validation(session, source_id: uuid.UUID, val_result: dict) -> None:
    session.add(
        Validation(
            source_id=source_id,
            overall_verdict=val_result["overall_verdict"],
            report_json=val_result["report_json"],
        )
    )
    session.commit()
