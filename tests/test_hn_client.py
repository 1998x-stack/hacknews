from unittest.mock import MagicMock, patch

import pytest

from hacknews.hn_client import HackerNewsClient, HNAPIError
from hacknews.models import Story


def test_fetch_top_returns_stories():
    session = MagicMock()
    session.get.return_value.json.return_value = [1]
    client = HackerNewsClient(session=session, retries=1)
    with patch.object(client, "fetch_item", return_value=Story(id=1, title="T", url="https://x.com", score=5)):
        items = client.fetch_top(1)
    assert len(items) == 1
    assert items[0].score == 5


def test_fetch_top_raises_when_api_down():
    session = MagicMock()
    session.get.side_effect = Exception("boom")
    client = HackerNewsClient(session=session, retries=1)
    with pytest.raises(HNAPIError):
        client.fetch_top(5)


def test_fetch_item_returns_none_for_dead():
    client = HackerNewsClient(session=MagicMock(), retries=1)
    with patch.object(client, "_get_json", return_value={"dead": True}):
        assert client.fetch_item(1) is None



def test_fetch_item_sets_hours_old_from_time():
    client = HackerNewsClient(session=MagicMock(), retries=1)
    past = __import__("time").time() - 7200
    with patch.object(client, "_get_json", return_value={"id": 1, "title": "T", "time": past}):
        story = client.fetch_item(1)
    assert story is not None
    assert story.hours_old == pytest.approx(2.0, abs=0.1)
