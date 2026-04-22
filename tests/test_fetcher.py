from unittest.mock import MagicMock, patch

from hacknews.fetcher import HackerNewsFetcher, NewsItem


def _make_response(json_data, status_code=200):
    resp = MagicMock()
    resp.json.return_value = json_data
    resp.status_code = status_code
    resp.raise_for_status.return_value = None
    return resp


class TestHackerNewsFetcher:
    def setup_method(self):
        self.fetcher = HackerNewsFetcher(top_n=3, timeout=1)

    def test_fetch_latest_news(self):
        story_ids = [1, 2, 3, 4, 5]
        items = {
            1: {"id": 1, "title": "A", "url": "https://a.com", "score": 10, "by": "u1"},
            2: {"id": 2, "title": "B", "url": "https://b.com", "score": 5, "by": "u2"},
            3: {"id": 3, "title": "C", "url": None, "score": 3, "by": "u3"},
        }

        with patch.object(self.fetcher.session, "get") as mock_get:
            mock_get.side_effect = [
                _make_response(story_ids),
                _make_response(items[1]),
                _make_response(items[2]),
                _make_response(items[3]),
            ]
            results = self.fetcher.fetch_latest_news()

        assert len(results) == 2
        assert results[0] == NewsItem(id=1, title="A", url="https://a.com", score=10, author="u1")
        assert results[1] == NewsItem(id=2, title="B", url="https://b.com", score=5, author="u2")

    def test_fetch_latest_news_limits_to_top_n(self):
        story_ids = list(range(100))
        with patch.object(self.fetcher.session, "get") as mock_get:
            mock_get.side_effect = [
                _make_response(story_ids),
                *[
                    _make_response({"id": i, "title": f"T{i}", "url": f"https://t{i}.com"})
                    for i in range(3)
                ],
            ]
            results = self.fetcher.fetch_latest_news()

        assert len(results) == 3
        calls = mock_get.call_args_list
        assert "item/0.json" in calls[1].args[0]
        assert "item/1.json" in calls[2].args[0]
        assert "item/2.json" in calls[3].args[0]

    def test_fetch_item_without_url(self):
        with patch.object(self.fetcher.session, "get") as mock_get:
            mock_get.return_value = _make_response(
                {"id": 1, "title": "Ask HN", "text": "Hello", "by": "u1"}
            )
            result = self.fetcher._fetch_item(1)

        assert result is None

    def test_fetch_item_with_empty_data(self):
        with patch.object(self.fetcher.session, "get") as mock_get:
            mock_get.return_value = _make_response(None)
            result = self.fetcher._fetch_item(1)

        assert result is None
