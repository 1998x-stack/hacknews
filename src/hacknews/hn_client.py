"""Resilient Hacker News Firebase API client."""
from __future__ import annotations

import time
from typing import Any

import requests

from hacknews.logging_setup import get_logger
from hacknews.models import Story

logger = get_logger(__name__)

TOP_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{id}.json"


class HNAPIError(Exception):
    """Raised when the HN API cannot be reached or topstories fails hard."""


class HackerNewsClient:
    def __init__(
        self,
        session: requests.Session | None = None,
        timeout: float = 10.0,
        retries: int = 3,
        proxy: str | None = None,
    ) -> None:
        self.session = session if session is not None else requests.Session()
        self.timeout = timeout
        self.retries = retries
        self.proxy = proxy

    def _request_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {"timeout": self.timeout}
        if self.proxy:
            kwargs["proxies"] = {"http": self.proxy, "https": self.proxy}
        return kwargs

    def _get_json(self, url: str) -> Any:
        last: Exception | None = None
        kwargs = self._request_kwargs()
        for attempt in range(self.retries):
            try:
                resp = self.session.get(url, **kwargs)
                resp.raise_for_status()
                return resp.json()
            except Exception as exc:  # noqa: BLE001 - transient/network errors
                last = exc
                time.sleep(0.5 * (attempt + 1))
        raise HNAPIError(f"failed to fetch {url}: {last}") from last

    def fetch_item(self, item_id: int) -> Story | None:
        data = self._get_json(ITEM_URL.format(id=item_id))
        if not data or data.get("deleted") or data.get("dead"):
            return None
        raw_time = data.get("time") or 0
        hours_old = (time.time() - raw_time) / 3600.0 if raw_time else 0.0
        return Story(
            id=data.get("id", item_id),
            title=data.get("title") or "",
            url=data.get("url"),
            score=data.get("score", 0),
            comments=data.get("descendants", 0),
            hours_old=hours_old,
            author=data.get("by") or "",
            text=data.get("text"),
        )

    def fetch_top(self, n: int) -> list[Story]:
        ids = self._get_json(TOP_URL)
        if not ids:
            raise HNAPIError("empty topstories response")
        stories: list[Story] = []
        for item_id in ids[:n]:
            story = self.fetch_item(item_id)
            if story is not None:
                stories.append(story)
        return stories
