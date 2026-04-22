# System Design: Hacker News Email Digest (v2)

## 1. Problem Statement

The current system is a Python script that:
1. Fetches top Hacker News stories via Firebase API
2. Extracts article content from URLs (fallback chain: newspaper3k → readability → GNE; PDFs via PyMuPDF)
3. Formats as Markdown
4. Sends via SMTP

It works but carries significant technical debt: import hacks, dead code, no validation, no tests, no type hints, no linting, and inconsistent patterns.

## 2. Design Goals

- **Same core functionality** — fetch → extract → format → send
- **Drop unused components** — text_clean, keywords_extractor, word_cloud, scheduler
- **Proper Python packaging** — no `sys.path.append` hacks
- **Type-safe** — full type hints, mypy-clean
- **Testable** — unit tests for all components
- **Configurable** — no hardcoded values, validated env vars
- **Minimal** — no speculative features

## 3. Architecture

### 3.1 Package Structure

```
hacknews/
├── pyproject.toml              # Build config, deps, lint, typecheck
├── src/
│   └── hacknews/
│       ├── __init__.py
│       ├── __main__.py          # Entry point (python -m hacknews)
│       ├── cli.py               # CLI interface
│       ├── config.py            # Validated configuration
│       ├── fetcher.py           # HN Firebase API client
│       ├── extractor.py         # Content extraction (fallback chain)
│       ├── formatter.py         # Markdown formatting
│       └── sender.py            # SMTP email sender
├── tests/
│   ├── __init__.py
│   ├── test_fetcher.py
│   ├── test_extractor.py
│   ├── test_formatter.py
│   └── test_sender.py
├── docs/
│   ├── LOGIC.md                 # Existing logic documentation
│   └── DESIGN.md                # This file
└── AGENTS.md
```

### 3.2 Key Changes from Current System

| Current | v2 | Rationale |
|---------|----|-----------|
| `sys.path.append` in every file | Proper `src/` layout + `pyproject.toml` | Standard Python packaging, no hacks |
| `EMAIL_ADDRESS` defaults to `''` | `ValueError` if missing | Fail fast with clear message |
| `@retry` returns `''` on exhaustion | Raises `ExtractionError` | Errors should propagate, not silently disappear |
| Custom `Log` class | Standard `logging` module | No reason to reinvent |
| `smtplib.encode_base64` monkey-patch | Remove if Python 3.9+ handles it; otherwise isolate | Monkey-patches are fragile |
| `top_n=10` hardcoded | Configurable via env var / CLI flag | Flexibility without complexity |
| `print()` in production code | `logging` throughout | Consistent, configurable output |
| No tests | Unit tests for all components | Prevent regressions |
| Mixed Chinese/English comments | English only | Consistency |

## 4. Component Design

### 4.1 Configuration (`config.py`)

```python
from dataclasses import dataclass, field
from os import environ
from typing import Optional

@dataclass(frozen=True)
class Config:
    email_address: str
    email_password: str
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    to_emails: list[str] = field(default_factory=list)
    proxy: Optional[str] = None
    top_n: int = 10
    timeout: int = 3

    @classmethod
    def from_env(cls) -> "Config":
        email_address = environ.get("EMAIL_ADDRESS", "")
        email_password = environ.get("EMAIL_PASSWORD", "")
        if not email_address:
            raise ValueError("EMAIL_ADDRESS is required")
        if not email_password:
            raise ValueError("EMAIL_PASSWORD is required")
        
        to_emails_str = environ.get("TO_EMAILS", "")
        to_emails = [e.strip() for e in to_emails_str.split(",") if e.strip()] if to_emails_str else []
        
        proxy = environ.get("PROXY")
        top_n = int(environ.get("HN_TOP_N", "10"))
        timeout = int(environ.get("REQUEST_TIMEOUT", "3"))
        
        return cls(
            email_address=email_address,
            email_password=email_password,
            smtp_server=environ.get("SMTP_SERVER", "smtp.gmail.com"),
            smtp_port=int(environ.get("SMTP_PORT", "587")),
            to_emails=to_emails,
            proxy=proxy,
            top_n=top_n,
            timeout=timeout,
        )
```

**Key decisions:**
- Frozen dataclass — immutable after creation
- `from_env()` factory — single point of env var reading
- Fails fast on required vars — no silent runtime failures
- All defaults documented in one place

### 4.2 Fetcher (`fetcher.py`)

```python
import logging
from dataclasses import dataclass
from typing import Optional
import requests

logger = logging.getLogger(__name__)

@dataclass
class NewsItem:
    id: int
    title: str
    url: Optional[str]
    score: int = 0
    author: str = ""

class HackerNewsFetcher:
    BASE_URL = "https://hacker-news.firebaseio.com/v0"
    
    def __init__(self, top_n: int = 10, timeout: int = 3):
        self.top_n = top_n
        self.timeout = timeout
        self.session = requests.Session()
    
    def fetch_latest_news(self) -> list[NewsItem]:
        ids = self._fetch_top_story_ids()
        items = []
        for story_id in ids[:self.top_n]:
            item = self._fetch_item(story_id)
            if item and item.url:
                items.append(item)
        logger.info("Fetched %d stories with URLs", len(items))
        return items
    
    def _fetch_top_story_ids(self) -> list[int]:
        resp = self.session.get(f"{self.BASE_URL}/topstories.json", timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()
    
    def _fetch_item(self, story_id: int) -> Optional[NewsItem]:
        resp = self.session.get(f"{self.BASE_URL}/item/{story_id}.json", timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("url"):
            return None
        return NewsItem(
            id=data["id"],
            title=data.get("title", ""),
            url=data.get("url"),
            score=data.get("score", 0),
            author=data.get("by", ""),
        )
```

**Key decisions:**
- `NewsItem` dataclass — typed, structured data instead of raw dicts
- `requests.Session` — connection pooling, reusable headers
- No `sys.path.append` — proper imports
- `logging` instead of custom `Log` class
- `_fetch_item` returns `None` for items without URLs — caller filters

### 4.3 Extractor (`extractor.py`)

```python
import logging
from urllib.parse import urlparse
import requests
from newspaper import Article, Configuration
from readability import Document
from gne import GeneralNewsExtractor
import fitz  # PyMuPDF
from io import BytesIO

logger = logging.getLogger(__name__)

class ExtractionError(Exception):
    pass

class ContentExtractor:
    def __init__(self, timeout: int = 3, proxy: str | None = None):
        self.timeout = timeout
        self.proxy = proxy
        self._newspaper_config = Configuration()
        self._request_args = {"timeout": timeout}
        if proxy:
            self._request_args["proxies"] = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
    
    def extract(self, url: str, lang: str = "en") -> str:
        if url.endswith(".pdf"):
            return self._extract_pdf(url)
        return self._extract_html(url, lang)
    
    def _extract_pdf(self, url: str) -> str:
        resp = requests.get(url, stream=True, **self._request_args)
        resp.raise_for_status()
        doc = fitz.open(stream=BytesIO(resp.content), filetype="pdf")
        text = "".join(page.get_text() for page in doc)
        if not text.strip():
            raise ExtractionError(f"No text extracted from PDF: {url}")
        logger.info("Extracted PDF via PyMuPDF: %s", url)
        return text
    
    def _extract_html(self, url: str, lang: str) -> str:
        # Try newspaper3k
        try:
            self._newspaper_config.headers = {"User-Agent": "Mozilla/5.0"}
            self._newspaper_config.set_language(lang)
            article = Article(url, config=self._newspaper_config)
            article.download()
            article.parse()
            if article.text.strip():
                logger.info("Extracted via newspaper3k: %s", url)
                return article.text
        except Exception as e:
            logger.warning("newspaper3k failed for %s: %s", url, e)
        
        # Fallback: readability
        try:
            html = self._fetch_html(url)
            content = Document(html).summary()
            if content.strip():
                logger.info("Extracted via readability: %s", url)
                return content
        except Exception as e:
            logger.warning("readability failed for %s: %s", url, e)
        
        # Fallback: GNE
        try:
            html = html if 'html' in locals() else self._fetch_html(url)
            result = GeneralNewsExtractor().extract(html, normalize=True)
            content = result.get("content", "")
            if content.strip():
                logger.info("Extracted via GNE: %s", url)
                return content
        except Exception as e:
            logger.warning("GNE failed for %s: %s", url, e)
        
        raise ExtractionError(f"All extraction methods failed for: {url}")
    
    def _fetch_html(self, url: str) -> str:
        resp = requests.get(url, **self._request_args)
        resp.raise_for_status()
        return resp.text
```

**Key decisions:**
- Raises `ExtractionError` instead of returning `''` — errors propagate
- No `@retry` decorator at this level — retry handled at orchestrator level if needed
- No `TextCleaner` — dead code removed
- No `quality_dict` tracking — use logging for observability
- Clean fallback chain with explicit error logging per step

### 4.4 Formatter (`formatter.py`)

```python
from datetime import datetime

class MarkdownFormatter:
    @staticmethod
    def format(news: list[dict]) -> str:
        lines = [
            "# Hacker News Digest",
            f"> {datetime.now().strftime('%Y-%m-%d')}",
            "---",
        ]
        for item in news:
            title = item.get("title", "Untitled")
            url = item.get("url", f"https://news.ycombinator.com/item?id={item.get('id')}")
            lines.append(f"## [{title}]({url})")
            
            text = item.get("text", "")
            if text:
                for paragraph in text.split("\n\n"):
                    if paragraph.strip():
                        lines.append(f"> {paragraph.strip().replace(chr(10), chr(10) + '> ')}")
            
            lines.append("---")
        
        return "\n\n".join(lines)
```

**Key decisions:**
- Static method — no state needed
- Removed emojis — cleaner, more professional
- Removed Chinese title — use English consistently (can be localized later if needed)
- Simpler paragraph wrapping

### 4.5 Sender (`sender.py`)

```python
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import markdown

logger = logging.getLogger(__name__)

class EmailSender:
    def __init__(self, smtp_server: str, smtp_port: int, username: str, password: str):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
    
    def send(self, subject: str, body: str, to_emails: list[str]) -> None:
        msg = MIMEMultipart("alternative")
        msg["From"] = self.username
        msg["To"] = ", ".join(to_emails)
        msg["Subject"] = subject
        
        html_body = markdown.markdown(body)
        msg.attach(MIMEText(body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))
        
        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls()
            server.login(self.username, self.password)
            server.sendmail(self.username, to_emails, msg.as_string())
        
        logger.info("Email sent to %s", to_emails)
```

**Key decisions:**
- No monkey-patch — test if Python 3.9+ still needs it; if so, isolate in a separate module with clear comment
- `send()` raises on failure — no silent swallowing
- Minimal, focused responsibility

### 4.6 Entry Point (`__main__.py`)

```python
import logging
import sys
from hacknews.config import Config
from hacknews.fetcher import HackerNewsFetcher
from hacknews.extractor import ContentExtractor, ExtractionError
from hacknews.formatter import MarkdownFormatter
from hacknews.sender import EmailSender

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

def main() -> None:
    config = Config.from_env()
    
    fetcher = HackerNewsFetcher(top_n=config.top_n, timeout=config.timeout)
    news_items = fetcher.fetch_latest_news()
    
    if not news_items:
        logger.warning("No stories with URLs found. Exiting.")
        return
    
    extractor = ContentExtractor(timeout=config.timeout, proxy=config.proxy)
    for item in news_items:
        try:
            text = extractor.extract(item.url, lang="en")
            item_dict = {
                "id": item.id,
                "title": item.title,
                "url": item.url,
                "text": text,
            }
            # Store extracted text back
            item.__dict__["text"] = text
        except ExtractionError as e:
            logger.warning("Skipping %s: %s", item.url, e)
    
    # Build news list for formatter
    news_list = [
        {"id": n.id, "title": n.title, "url": n.url, "text": getattr(n, "text", "")}
        for n in news_items
    ]
    
    body = MarkdownFormatter.format(news_list)
    subject = f"Hacker News Digest - {news_list[0].get('date', '')}"
    
    sender = EmailSender(config.smtp_server, config.smtp_port, config.email_address, config.email_password)
    sender.send(subject, body, config.to_emails)

if __name__ == "__main__":
    main()
```

**Key decisions:**
- Standard `logging.basicConfig` — no custom Log class
- `Config.from_env()` — single source of configuration
- Graceful handling of extraction failures — log warning, continue
- Early exit if no stories — no pointless email attempt

## 5. Dependency Changes

### Keep
- `requests` — HTTP client
- `newspaper3k` — primary content extraction
- `readability-lxml` — fallback extraction
- `gne` — fallback extraction
- `PyMuPDF` — PDF extraction
- `markdown` — Markdown → HTML
- `certifi` — SSL certificates

### Remove
- `schedule` — unused (GitHub Actions handles scheduling)
- `fake-headers` — replace with static User-Agent string
- `pandas` — unused in production
- `jieba` — Chinese segmentation, not needed for English HN
- `lxml[html_clean]` — only needed if readability requires it
- `rake-nltk`, `spacy`, `scikit-learn`, `gensim`, `yake`, `nltk` — all unused (keywords_extractor)
- `wordcloud` — unused

### Add
- `pytest` — testing framework
- `mypy` — type checking
- `ruff` — linting + formatting

### Estimated requirements.txt (production)
```
requests
newspaper3k
readability-lxml
gne
PyMuPDF
markdown
certifi
```

### Estimated dev dependencies (pyproject.toml)
```
pytest>=7.0
mypy>=1.0
ruff>=0.1
```

## 6. CI/CD Changes

### GitHub Actions (`.github/workflows/news_email.yaml`)

```yaml
name: Hacker News Digest

on:
  schedule:
    - cron: '40 13 * * *'  # 21:40 CST
  workflow_dispatch:

jobs:
  send-digest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run
        env:
          EMAIL_ADDRESS: ${{ secrets.EMAIL_ADDRESS }}
          EMAIL_PASSWORD: ${{ secrets.EMAIL_PASSWORD }}
          SMTP_SERVER: ${{ secrets.SMTP_SERVER }}
          SMTP_PORT: ${{ secrets.SMTP_PORT }}
          TO_EMAILS: ${{ secrets.TO_EMAILS }}
          PROXY: ${{ secrets.PROXY }}
          HN_TOP_N: '10'
        run: python -m hacknews
```

**Changes:**
- Python 3.12 (from 3.9)
- No spaCy model download (removed unused dependency)
- `python -m hacknews` (proper package entry)
- Added `HN_TOP_N` env var

## 7. Testing Strategy

### Unit Tests
- `test_fetcher.py` — mock Firebase API responses, test NewsItem parsing
- `test_extractor.py` — mock HTTP responses, test each extraction method
- `test_formatter.py` — test Markdown output format
- `test_sender.py` — mock SMTP, test email construction
- `test_config.py` — test env var parsing, validation errors

### Integration Test
- End-to-end test with mocked external services

### Test Command
```bash
pytest tests/ -v
```

## 8. Migration Plan

### Phase 1: Foundation
- Create `pyproject.toml` with proper package structure
- Move config to validated dataclass
- Replace custom Log with standard logging

### Phase 2: Core Components
- Rewrite fetcher with NewsItem dataclass
- Rewrite extractor with proper error handling
- Rewrite formatter and sender

### Phase 3: Cleanup
- Remove all dead code
- Update CI workflow
- Add unit tests

### Phase 4: Verification
- Run full test suite
- Test with real HN API (dry run)
- Deploy to GitHub Actions

## 9. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| newspaper3k breaks on certain sites | High | Medium | Fallback chain already handles this |
| SMTP changes require monkey-patch | Low | High | Test on Python 3.12 before deploy |
| Firebase API changes | Low | High | Add response validation |
| Content extraction quality drops | Medium | Medium | Log extraction method success rates |

## 10. Success Criteria

- [ ] All tests pass (`pytest tests/ -v`)
- [ ] No mypy errors (`mypy src/`)
- [ ] No ruff errors (`ruff check src/`)
- [ ] Email sent successfully in staging
- [ ] CI workflow runs without errors
- [ ] No `sys.path.append` anywhere
- [ ] All dead code removed
- [ ] Configuration validated at startup
