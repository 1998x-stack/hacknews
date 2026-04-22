from unittest.mock import MagicMock, patch

import pytest

from hacknews.extractor import ContentExtractor, ExtractionError


class TestContentExtractor:
    def setup_method(self):
        self.extractor = ContentExtractor(timeout=1)

    def test_extract_pdf(self):
        mock_page = MagicMock()
        mock_page.get_text.return_value = "PDF content"
        mock_doc = MagicMock()
        mock_doc.__len__ = lambda self: 1
        mock_doc.__iter__ = lambda self: iter([mock_page])

        mock_resp = MagicMock()
        mock_resp.content = b"pdf data"
        mock_resp.raise_for_status.return_value = None

        with patch("hacknews.extractor.requests.get", return_value=mock_resp), \
             patch("hacknews.extractor.fitz.open", return_value=mock_doc):
            result = self.extractor.extract("https://example.com/doc.pdf")

        assert result == "PDF content"

    def test_extract_pdf_empty_text_raises(self):
        mock_doc = MagicMock()
        mock_doc.__len__ = lambda self: 1
        mock_page = MagicMock()
        mock_page.get_text.return_value = "   "
        mock_doc.__iter__ = lambda self: iter([mock_page])

        mock_resp = MagicMock()
        mock_resp.content = b"pdf"
        mock_resp.raise_for_status.return_value = None

        with patch("hacknews.extractor.requests.get", return_value=mock_resp), \
             patch("hacknews.extractor.fitz.open", return_value=mock_doc):
            with pytest.raises(ExtractionError, match="No text extracted"):
                self.extractor.extract("https://example.com/empty.pdf")

    def test_extract_html_newspaper3k_success(self):
        mock_article = MagicMock()
        mock_article.text = "Article body text"

        with patch("hacknews.extractor.Article", return_value=mock_article):
            result = self.extractor.extract("https://example.com/article", lang="en")

        assert result == "Article body text"

    def test_extract_html_falls_back_to_readability(self):
        mock_article = MagicMock()
        mock_article.text = ""
        mock_article.download.side_effect = Exception("network error")

        mock_html = "<html><body><p>Readability content</p></body></html>"
        mock_resp = MagicMock()
        mock_resp.text = mock_html
        mock_resp.raise_for_status.return_value = None

        mock_doc = MagicMock()
        mock_doc.summary.return_value = "<p>Readability content</p>"

        with patch("hacknews.extractor.Article", return_value=mock_article), \
             patch("hacknews.extractor.requests.get", return_value=mock_resp), \
             patch("hacknews.extractor.Document", return_value=mock_doc):
            result = self.extractor.extract("https://example.com/article", lang="en")

        assert "Readability content" in result

    def test_extract_html_all_methods_fail_raises(self):
        mock_article = MagicMock()
        mock_article.text = ""
        mock_article.download.side_effect = Exception("fail")

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("network error")

        with patch("hacknews.extractor.Article", return_value=mock_article), \
             patch("hacknews.extractor.requests.get", return_value=mock_resp):
            with pytest.raises(ExtractionError, match="All extraction methods failed"):
                self.extractor.extract("https://example.com/bad", lang="en")

    def test_extract_with_proxy(self):
        extractor = ContentExtractor(timeout=1, proxy="proxy.local:8080")
        assert "proxies" in extractor._request_args
        assert extractor._request_args["proxies"]["http"] == "http://proxy.local:8080"
