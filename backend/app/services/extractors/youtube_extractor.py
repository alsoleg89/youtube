from app.services.extractors.base import ContentExtractor, ExtractionResult
from app.services.youtube import YouTubeService


class YoutubeExtractor(ContentExtractor):
    def __init__(self) -> None:
        self._svc = YouTubeService()

    def extract(self, source) -> ExtractionResult:
        result = self._svc.extract(source.url, str(source.id))

        if result["source"] == "captions":
            return ExtractionResult(
                text=result["text"],
                meta=result["meta"],
            )

        return ExtractionResult(
            text="",
            meta=result["meta"],
            needs_transcription=True,
            audio_path=result["audio_path"],
        )
