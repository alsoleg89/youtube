import logging
import os
import re
from abc import ABC, abstractmethod

from app.core.config import settings

logger = logging.getLogger(__name__)

YT_ID_RE = re.compile(r"(?:v=|youtu\.be/)([\w\-]{11})")


class BaseYouTubeService(ABC):
    @abstractmethod
    def extract(self, url: str, video_id_db: str) -> dict:
        """
        Returns one of:
          {"source": "captions", "text": str, "meta": dict}
          {"source": "whisper",  "audio_path": str, "meta": dict}
        """
        ...


class YouTubeService(BaseYouTubeService):
    def _extract_video_id(self, url: str) -> str:
        match = YT_ID_RE.search(url)
        if not match:
            raise ValueError(f"Cannot extract video ID from URL: {url}")
        return match.group(1)

    def extract(self, url: str, video_id_db: str) -> dict:
        yt_id = self._extract_video_id(url)

        text, meta = self._try_captions(yt_id)
        if text:
            return {"source": "captions", "text": text, "meta": meta}

        return self._download_audio(url, yt_id, video_id_db)

    # ------------------------------------------------------------------

    def _try_captions(self, yt_id: str) -> tuple[str | None, dict]:
        try:
            from youtube_transcript_api import YouTubeTranscriptApi

            entries = YouTubeTranscriptApi.get_transcript(
                yt_id, languages=["ru", "en"]
            )
            text = " ".join(e["text"] for e in entries)
            return text, {"language": "ru/en", "source": "captions"}
        except Exception:
            pass

        try:
            from youtube_transcript_api import YouTubeTranscriptApi

            entries = YouTubeTranscriptApi.get_transcript(yt_id)
            text = " ".join(e["text"] for e in entries)
            return text, {"language": "auto", "source": "captions"}
        except Exception as e:
            logger.warning("Captions unavailable for %s: %s", yt_id, e)
            return None, {}

    def _download_audio(self, url: str, yt_id: str, video_id_db: str) -> dict:
        import yt_dlp

        work_dir = os.path.join(settings.tmp_dir, video_id_db)
        os.makedirs(work_dir, exist_ok=True)

        output_tpl = os.path.join(work_dir, "audio.%(ext)s")
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": output_tpl,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "5",
                }
            ],
            "quiet": True,
            "no_warnings": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            duration = info.get("duration", 0)

        if duration > settings.max_video_duration:
            raise ValueError(
                f"video_too_long: duration {duration}s exceeds "
                f"{settings.max_video_duration}s limit"
            )

        audio_file = os.path.join(work_dir, "audio.mp3")
        if not os.path.exists(audio_file):
            for ext in ("m4a", "webm", "opus", "ogg"):
                candidate = os.path.join(work_dir, f"audio.{ext}")
                if os.path.exists(candidate):
                    audio_file = candidate
                    break

        if not os.path.exists(audio_file):
            raise ValueError("transcript_unavailable: audio download failed")

        meta = {
            "language": info.get("language", "unknown"),
            "duration_sec": duration,
            "source": "whisper",
        }
        return {"source": "whisper", "audio_path": audio_file, "meta": meta}
