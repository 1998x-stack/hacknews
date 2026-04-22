from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent / "data"
HTML_DIR = BASE_DIR / "html"
MARKDOWN_DIR = BASE_DIR / "markdown"


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def save_html(story_id: int, html: str, date: str | None = None) -> Path:
    date = date or _today()
    dir_path = HTML_DIR / date
    dir_path.mkdir(parents=True, exist_ok=True)
    file_path = dir_path / f"{story_id}.html"
    file_path.write_text(html, encoding="utf-8")
    logger.info("Saved HTML: %s", file_path)
    return file_path


def load_html(story_id: int, date: str | None = None) -> str:
    date = date or _today()
    file_path = HTML_DIR / date / f"{story_id}.html"
    if not file_path.exists():
        raise FileNotFoundError(f"HTML not found: {file_path}")
    return file_path.read_text(encoding="utf-8")


def save_markdown(content: str, date: str | None = None) -> Path:
    date = date or _today()
    MARKDOWN_DIR.mkdir(parents=True, exist_ok=True)
    file_path = MARKDOWN_DIR / f"{date}.md"
    file_path.write_text(content, encoding="utf-8")
    logger.info("Saved Markdown: %s", file_path)
    return file_path


def load_markdown(date: str | None = None) -> str:
    date = date or _today()
    file_path = MARKDOWN_DIR / f"{date}.md"
    if not file_path.exists():
        raise FileNotFoundError(f"Markdown not found: {file_path}")
    return file_path.read_text(encoding="utf-8")


def save_metadata(stories: list[dict], date: str | None = None) -> Path:
    date = date or _today()
    dir_path = HTML_DIR / date
    dir_path.mkdir(parents=True, exist_ok=True)
    file_path = dir_path / "metadata.json"
    file_path.write_text(json.dumps(stories, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Saved metadata: %s", file_path)
    return file_path


def load_metadata(date: str | None = None) -> list[dict]:
    date = date or _today()
    file_path = HTML_DIR / date / "metadata.json"
    if not file_path.exists():
        raise FileNotFoundError(f"Metadata not found: {file_path}")
    data = json.loads(file_path.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    return data
