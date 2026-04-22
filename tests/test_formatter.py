from hacknews.formatter import MarkdownFormatter


class TestMarkdownFormatter:
    def test_format_single_article(self):
        news = [
            {
                "id": 1,
                "title": "Test Article",
                "url": "https://example.com",
                "text": "Body text here.",
            }
        ]
        result = MarkdownFormatter.format(news)

        assert "# Hacker News Digest" in result
        assert "## [Test Article](https://example.com)" in result
        assert "> Body text here." in result

    def test_format_multiple_articles(self):
        news = [
            {"id": 1, "title": "A", "url": "https://a.com", "text": "Text A"},
            {"id": 2, "title": "B", "url": "https://b.com", "text": "Text B"},
        ]
        result = MarkdownFormatter.format(news)

        assert "## [A](https://a.com)" in result
        assert "## [B](https://b.com)" in result
        assert result.count("---") == 3

    def test_format_without_text(self):
        news = [{"id": 1, "title": "No Text", "url": "https://x.com", "text": ""}]
        result = MarkdownFormatter.format(news)

        assert "## [No Text](https://x.com)" in result

    def test_format_without_url_uses_hn_link(self):
        news = [{"id": 42, "title": "Ask HN", "url": None, "text": ""}]
        result = MarkdownFormatter.format(news)

        assert "https://news.ycombinator.com/item?id=42" in result

    def test_format_multiline_paragraphs(self):
        news = [
            {
                "id": 1,
                "title": "Multi",
                "url": "https://x.com",
                "text": "Para 1.\n\nPara 2.\n\nPara 3.",
            }
        ]
        result = MarkdownFormatter.format(news)

        assert "> Para 1." in result
        assert "> Para 2." in result
        assert "> Para 3." in result

    def test_format_empty_list(self):
        result = MarkdownFormatter.format([])
        assert "# Hacker News Digest" in result
