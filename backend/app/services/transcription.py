import logging
import os
from abc import ABC, abstractmethod

from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

MAX_CHUNK_BYTES = 20 * 1024 * 1024  # 20 MB


class BaseTranscriptionService(ABC):
    @abstractmethod
    def transcribe(self, audio_path: str) -> tuple[str, dict]:
        """Returns (full_text, meta_dict)."""
        ...


class TranscriptionService(BaseTranscriptionService):
    def __init__(self) -> None:
        self.client = OpenAI(api_key=settings.openai_api_key)

    def transcribe(self, audio_path: str) -> tuple[str, dict]:
        chunks = self._split_if_needed(audio_path)
        if len(chunks) > settings.max_chunks:
            raise ValueError(
                f"too_many_chunks: {len(chunks)} exceeds {settings.max_chunks} limit"
            )

        texts: list[str] = []
        for i, chunk_path in enumerate(chunks):
            logger.info("Whisper chunk %d/%d: %s", i + 1, len(chunks), chunk_path)
            with open(chunk_path, "rb") as f:
                resp = self.client.audio.transcriptions.create(
                    model="whisper-1", file=f
                )
            texts.append(resp.text)

        full_text = " ".join(texts)
        meta = {"whisper_chunks": len(chunks)}
        return full_text, meta

    # ------------------------------------------------------------------

    def _split_if_needed(self, audio_path: str) -> list[str]:
        file_size = os.path.getsize(audio_path)
        if file_size <= MAX_CHUNK_BYTES:
            return [audio_path]

        from pydub import AudioSegment

        audio = AudioSegment.from_file(audio_path)
        ratio = MAX_CHUNK_BYTES / file_size * 0.95
        chunk_duration_ms = int(len(audio) * ratio)
        if chunk_duration_ms < 1000:
            chunk_duration_ms = 1000

        work_dir = os.path.dirname(audio_path)
        chunks: list[str] = []
        for idx, start in enumerate(range(0, len(audio), chunk_duration_ms)):
            segment = audio[start : start + chunk_duration_ms]
            chunk_path = os.path.join(work_dir, f"chunk_{idx}.mp3")
            segment.export(chunk_path, format="mp3")
            chunks.append(chunk_path)

        return chunks
