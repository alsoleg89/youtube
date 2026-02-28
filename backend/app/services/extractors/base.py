from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ExtractionResult:
    text: str
    meta: dict = field(default_factory=dict)
    needs_transcription: bool = False
    audio_path: str | None = None


class ContentExtractor(ABC):
    @abstractmethod
    def extract(self, source) -> ExtractionResult:
        """Extract text content from a source record.

        Args:
            source: a Source ORM instance with url, file_path, source_type, id.

        Returns:
            ExtractionResult with extracted text or audio_path for whisper.
        """
        ...
