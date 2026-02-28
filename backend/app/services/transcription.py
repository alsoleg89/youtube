import logging
import os
import subprocess
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
                    model=settings.transcription_model, file=f
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

        return self._split_with_ffmpeg(audio_path)

    @staticmethod
    def _split_with_ffmpeg(audio_path: str) -> list[str]:
        work_dir = os.path.dirname(audio_path)
        file_size = os.path.getsize(audio_path)

        probe = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_path,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        total_sec = float(probe.stdout.strip())
        if total_sec <= 0:
            return [audio_path]

        bytes_per_sec = file_size / total_sec
        chunk_sec = int(MAX_CHUNK_BYTES / bytes_per_sec * 0.95)
        chunk_sec = max(chunk_sec, 10)

        chunks: list[str] = []
        start = 0
        idx = 0
        while start < total_sec:
            out = os.path.join(work_dir, f"chunk_{idx}.mp3")
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-ss", str(start),
                    "-t", str(chunk_sec),
                    "-i", audio_path,
                    "-c", "copy",
                    "-loglevel", "error",
                    out,
                ],
                check=True,
            )
            if os.path.exists(out) and os.path.getsize(out) > 0:
                chunks.append(out)
            start += chunk_sec
            idx += 1

        return chunks if chunks else [audio_path]
