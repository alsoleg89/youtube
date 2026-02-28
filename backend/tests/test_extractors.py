import uuid
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

from app.services.extractors.base import ExtractionResult
from app.services.extractors.epub_extractor import EpubExtractor
from app.services.extractors.factory import get_extractor
from app.services.extractors.pdf_extractor import PdfExtractor
from app.services.extractors.web_extractor import WebExtractor
from app.services.extractors.youtube_extractor import YoutubeExtractor


@dataclass
class FakeSource:
    id: uuid.UUID = uuid.UUID("00000000-0000-0000-0000-000000000001")
    url: str = "https://example.com"
    file_path: str = "/tmp/test.pdf"
    source_type: str = "youtube"


class TestFactory:
    def test_get_youtube_extractor(self):
        ext = get_extractor("youtube")
        assert isinstance(ext, YoutubeExtractor)

    def test_get_pdf_extractor(self):
        ext = get_extractor("pdf")
        assert isinstance(ext, PdfExtractor)

    def test_get_epub_extractor(self):
        ext = get_extractor("epub")
        assert isinstance(ext, EpubExtractor)

    def test_get_web_extractor(self):
        ext = get_extractor("web")
        assert isinstance(ext, WebExtractor)

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown source_type"):
            get_extractor("invalid")


class TestPdfExtractor:
    @patch("app.services.extractors.pdf_extractor.pdfplumber")
    def test_extracts_text(self, mock_pdfplumber):
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Page 1 text"
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = lambda s: mock_pdf
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdfplumber.open.return_value = mock_pdf

        ext = PdfExtractor()
        source = FakeSource(source_type="pdf", file_path="/tmp/test.pdf")
        result = ext.extract(source)

        assert isinstance(result, ExtractionResult)
        assert "Page 1 text" in result.text
        assert result.meta["source"] == "pdf"
        assert result.needs_transcription is False

    @patch("app.services.extractors.pdf_extractor.pdfplumber")
    def test_empty_pdf_raises(self, mock_pdfplumber):
        mock_page = MagicMock()
        mock_page.extract_text.return_value = ""
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = lambda s: mock_pdf
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdfplumber.open.return_value = mock_pdf

        ext = PdfExtractor()
        source = FakeSource(source_type="pdf")
        with pytest.raises(ValueError, match="transcript_unavailable"):
            ext.extract(source)


class TestEpubExtractor:
    @patch("app.services.extractors.epub_extractor.epub")
    def test_extracts_text(self, mock_epub):
        mock_item = MagicMock()
        mock_item.get_content.return_value = b"<p>Hello world</p>"
        mock_book = MagicMock()
        mock_book.get_items_of_type.return_value = [mock_item]
        mock_epub.read_epub.return_value = mock_book

        ext = EpubExtractor()
        source = FakeSource(source_type="epub", file_path="/tmp/test.epub")
        result = ext.extract(source)

        assert isinstance(result, ExtractionResult)
        assert "Hello world" in result.text
        assert result.meta["source"] == "epub"


class TestWebExtractor:
    @patch("app.services.extractors.web_extractor.Article")
    def test_extracts_text(self, mock_article_cls):
        mock_article = MagicMock()
        mock_article.text = "Article content here"
        mock_article.title = "Test Title"
        mock_article.authors = ["Author"]
        mock_article_cls.return_value = mock_article

        ext = WebExtractor()
        source = FakeSource(source_type="web", url="https://example.com/article")
        result = ext.extract(source)

        assert isinstance(result, ExtractionResult)
        assert "Article content here" in result.text
        assert result.meta["source"] == "web"
        mock_article.download.assert_called_once()
        mock_article.parse.assert_called_once()

    @patch("app.services.extractors.web_extractor.Article")
    def test_empty_page_raises(self, mock_article_cls):
        mock_article = MagicMock()
        mock_article.text = ""
        mock_article_cls.return_value = mock_article

        ext = WebExtractor()
        source = FakeSource(source_type="web")
        with pytest.raises(ValueError, match="transcript_unavailable"):
            ext.extract(source)


class TestYoutubeExtractor:
    @patch("app.services.extractors.youtube_extractor.YouTubeService")
    def test_captions_path(self, mock_yt_cls):
        mock_svc = MagicMock()
        mock_svc.extract.return_value = {
            "source": "captions",
            "text": "caption text",
            "meta": {"language": "en"},
        }
        mock_yt_cls.return_value = mock_svc

        ext = YoutubeExtractor()
        ext._svc = mock_svc
        source = FakeSource(source_type="youtube", url="https://youtube.com/watch?v=test1234567")
        result = ext.extract(source)

        assert result.text == "caption text"
        assert result.needs_transcription is False

    @patch("app.services.extractors.youtube_extractor.YouTubeService")
    def test_whisper_path(self, mock_yt_cls):
        mock_svc = MagicMock()
        mock_svc.extract.return_value = {
            "source": "whisper",
            "audio_path": "/tmp/audio.mp3",
            "meta": {"duration_sec": 300},
        }
        mock_yt_cls.return_value = mock_svc

        ext = YoutubeExtractor()
        ext._svc = mock_svc
        source = FakeSource(source_type="youtube", url="https://youtube.com/watch?v=test1234567")
        result = ext.extract(source)

        assert result.needs_transcription is True
        assert result.audio_path == "/tmp/audio.mp3"
