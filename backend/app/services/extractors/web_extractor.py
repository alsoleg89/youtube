import logging
from urllib.parse import quote, urlsplit, urlunsplit

from newspaper import Article

from app.services.extractors.base import ContentExtractor, ExtractionResult

logger = logging.getLogger(__name__)


def _encode_url(url: str) -> str:
    """Percent-encode non-ASCII characters in URL path/query (keeps scheme & host)."""
    parts = urlsplit(url)
    encoded = urlunsplit((
        parts.scheme,
        parts.netloc,
        quote(parts.path, safe="/:@!$&'()*+,;=-._~"),
        quote(parts.query, safe="/:@!$&'()*+,;=-._~?"),
        parts.fragment,
    ))
    return encoded


class WebExtractor(ContentExtractor):
    def extract(self, source) -> ExtractionResult:
        safe_url = _encode_url(source.url)
        article = Article(safe_url)
        article.download()
        article.parse()

        text = article.text
        if not text or not text.strip():
            raise ValueError(
                "transcript_unavailable: could not extract text from web page"
            )

        meta = {
            "source": "web",
            "url": source.url,
            "title": article.title or "",
            "authors": article.authors or [],
        }
        return ExtractionResult(text=text, meta=meta)
