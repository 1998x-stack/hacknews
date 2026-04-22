"""Article content extraction from URLs with fallback chain."""

from __future__ import annotations

import logging
from io import BytesIO

import fitz  # type: ignore[import-untyped]
import requests  # type: ignore[import-untyped]
from gne import GeneralNewsExtractor  # type: ignore[import-untyped]
from newspaper import Article  # type: ignore[import-untyped]
from newspaper.configuration import Configuration  # type: ignore[import-untyped]
from readability import Document  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)


class ExtractionError(Exception):
    pass


class ContentExtractor:
    def __init__(
        self,
        timeout: int = 3,
        proxy: str | None = None,
        save_html: bool = False,
        date: str | None = None,
    ) -> None:
        self.timeout = timeout
        self.proxy = proxy
        self.save_html = save_html
        self.date = date
        self._newspaper_config = Configuration()
        self._request_args: dict = {"timeout": timeout}
        if proxy:
            self._request_args["proxies"] = {
                "http": f"http://{proxy}",
                "https": f"http://{proxy}",
            }

    def extract(self, url: str, lang: str = "en", story_id: int | None = None) -> str:
        if url.endswith(".pdf"):
            return self._extract_pdf(url)
        return self._extract_html(url, lang, story_id)

    def _extract_pdf(self, url: str) -> str:
        resp = requests.get(url, stream=True, **self._request_args)
        resp.raise_for_status()
        doc = fitz.open(stream=BytesIO(resp.content), filetype="pdf")
        try:
            text = "".join(page.get_text() for page in doc)
        finally:
            doc.close()
        if not text.strip():
            raise ExtractionError(f"No text extracted from PDF: {url}")
        logger.info("Extracted PDF via PyMuPDF: %s", url)
        return text

    def _extract_html(self, url: str, lang: str, story_id: int | None = None) -> str:
        try:
            self._newspaper_config.headers = {"User-Agent": "Mozilla/5.0"}
            self._newspaper_config.set_language(lang)
            article = Article(url, config=self._newspaper_config)
            article.download()
            article.parse()
            if article.text.strip():
                logger.info("Extracted via newspaper3k: %s", url)
                return str(article.text)
        except Exception as e:
            logger.warning("newspaper3k failed for %s: %s", url, e)

        html = ""
        try:
            html = self._fetch_html(url)
            if self.save_html and story_id:
                from hacknews import storage
                storage.save_html(story_id, html, self.date)
        except Exception as e:
            logger.warning("HTML fetch failed for %s: %s", url, e)

        try:
            content = Document(html).summary()
            if content and str(content).strip():
                logger.info("Extracted via readability: %s", url)
                return str(content)
        except Exception as e:
            logger.warning("readability failed for %s: %s", url, e)

        try:
            result = GeneralNewsExtractor().extract(html, normalize=True)
            content = result.get("content", "")
            if content and str(content).strip():
                logger.info("Extracted via GNE: %s", url)
                return str(content)
        except Exception as e:
            logger.warning("GNE failed for %s: %s", url, e)

        raise ExtractionError(f"All extraction methods failed for: {url}")

    def _fetch_html(self, url: str) -> str:
        resp = requests.get(url, **self._request_args)
        resp.raise_for_status()
        return str(resp.text)
