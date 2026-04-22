"""Hacker News Firebase API client."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import requests  # type: ignore[import-untyped]
from requests.adapters import HTTPAdapter  # type: ignore[import-untyped]
from urllib3.util.retry import Retry  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)


@dataclass
class NewsItem:
    id: int
    title: str
    url: str | None
    score: int = 0
    author: str = ""
    text: str = ""


class HackerNewsFetcher:
    BASE_URL = "https://hacker-news.firebaseio.com/v0"

    def __init__(self, top_n: int = 10, timeout: int = 3) -> None:
        self.top_n = top_n
        self.timeout = timeout
        self.session = requests.Session()
        retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def fetch_latest_news(self) -> list[NewsItem]:
        ids = self._fetch_top_story_ids()
        items: list[NewsItem] = []
        for story_id in ids[: self.top_n]:
            item = self._fetch_item(story_id)
            if item and item.url:
                items.append(item)
        logger.info("Fetched %d stories with URLs", len(items))
        return items

    def _fetch_top_story_ids(self) -> list[int]:
        resp = self.session.get(f"{self.BASE_URL}/topstories.json", timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        return [int(x) for x in data]

    def _fetch_item(self, story_id: int) -> NewsItem | None:
        resp = self.session.get(
            f"{self.BASE_URL}/item/{story_id}.json", timeout=self.timeout
        )
        resp.raise_for_status()
        data = resp.json()
        if not data or not data.get("url"):
            return None
        return NewsItem(
            id=data["id"],
            title=data.get("title", ""),
            url=data.get("url"),
            score=data.get("score", 0),
            author=data.get("by", ""),
        )
