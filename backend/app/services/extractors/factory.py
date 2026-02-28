from app.services.extractors.base import ContentExtractor
from app.services.extractors.epub_extractor import EpubExtractor
from app.services.extractors.pdf_extractor import PdfExtractor
from app.services.extractors.web_extractor import WebExtractor
from app.services.extractors.youtube_extractor import YoutubeExtractor

_REGISTRY: dict[str, type[ContentExtractor]] = {
    "youtube": YoutubeExtractor,
    "pdf": PdfExtractor,
    "epub": EpubExtractor,
    "web": WebExtractor,
}


def get_extractor(source_type: str) -> ContentExtractor:
    cls = _REGISTRY.get(source_type)
    if cls is None:
        raise ValueError(f"Unknown source_type: {source_type}")
    return cls()
