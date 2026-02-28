import logging

import pdfplumber

from app.services.extractors.base import ContentExtractor, ExtractionResult

logger = logging.getLogger(__name__)


class PdfExtractor(ContentExtractor):
    def extract(self, source) -> ExtractionResult:
        pages_text: list[str] = []
        with pdfplumber.open(source.file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages_text.append(text)

        full_text = "\n\n".join(pages_text)
        if not full_text.strip():
            raise ValueError("transcript_unavailable: PDF contains no extractable text")

        import os
        title = os.path.splitext(os.path.basename(source.file_path))[0] if source.file_path else None
        meta = {
            "source": "pdf",
            "file_path": source.file_path,
            "page_count": len(pages_text),
            "title": title,
        }
        return ExtractionResult(text=full_text, meta=meta)
