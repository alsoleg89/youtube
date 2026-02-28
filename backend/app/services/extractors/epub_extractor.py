import logging

import ebooklib
from bs4 import BeautifulSoup
from ebooklib import epub

from app.services.extractors.base import ContentExtractor, ExtractionResult

logger = logging.getLogger(__name__)


class EpubExtractor(ContentExtractor):
    def extract(self, source) -> ExtractionResult:
        book = epub.read_epub(source.file_path, options={"ignore_ncx": True})

        chapters_text: list[str] = []
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            soup = BeautifulSoup(item.get_content(), "html.parser")
            text = soup.get_text(separator="\n", strip=True)
            if text:
                chapters_text.append(text)

        full_text = "\n\n".join(chapters_text)
        if not full_text.strip():
            raise ValueError(
                "transcript_unavailable: EPUB contains no extractable text"
            )

        book_title = None
        try:
            dc_title = book.get_metadata("DC", "title")
            if dc_title:
                book_title = dc_title[0][0]
        except Exception:
            pass
        if not book_title and source.file_path:
            import os
            book_title = os.path.splitext(os.path.basename(source.file_path))[0]

        meta = {
            "source": "epub",
            "file_path": source.file_path,
            "chapter_count": len(chapters_text),
            "title": book_title,
        }
        return ExtractionResult(text=full_text, meta=meta)
