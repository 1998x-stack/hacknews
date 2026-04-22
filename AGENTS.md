# AGENTS.md — hacknews

## Project

Hacker News email digest: fetches top stories via Firebase API, extracts article content from URLs, formats as Markdown, and sends via SMTP. Runs on GitHub Actions daily (cron `40 13 * * *` UTC → 21:40 CST).

Repo: `github.com/1998x-stack/hacknews`

## Directory Layout

```
src/main.py              — entry point, orchestrates fetch → extract → format → send
src/url_extractor.py     — ContentExtractor: scrapes article text from URLs (PDF + HTML)
util/hacker_news_fetcher.py  — HN Firebase API client
util/email_sender.py     — SMTP sender (monkey-patches smtplib.encode_base64)
util/markdown_formatter.py   — news → Markdown
util/log_utils.py        — custom Log class, singleton `logger`
util/utils.py            — @retry decorator
util/text_clean.py       — TextCleaner (regex-based)
config/config.py         — env var reader
tests/                   — unittest test suite
```

## Commands

```bash
# Install deps
pip install -r requirements.txt

# Download spaCy English model (required by CI, not in requirements.txt)
python -m spacy download en_core_web_sm

# Run all tests
python -m unittest discover -s tests

# Run the script (requires env vars)
python src/main.py
python -m src.main          # equivalent, used by GitHub Actions
```

## Required Environment Variables

| Variable | Required | Default | Notes |
|---|---|---|---|
| `EMAIL_ADDRESS` | Yes | `''` (empty) | Sender email — empty string causes runtime error |
| `EMAIL_PASSWORD` | Yes | `''` (empty) | Sender password / app password |
| `SMTP_SERVER` | No | `smtp.gmail.com` | |
| `SMTP_PORT` | No | `587` | |
| `TO_EMAILS` | No | `''` (empty) | Comma-separated |
| `PROXY` | No | none | If set, all HTTP requests route through `http://$PROXY` |

## Key Quirks

- **Import hack**: Every file does `sys.path.append(...)` to make `util/` and `config/` importable from `src/`. Do NOT "fix" this without testing — the whole project depends on it.
- **README is stale**: It lists files under `src/` that actually live in `util/`. Trust the actual file layout, not the README.
- **No lint/typecheck/test config**: No pyproject.toml, setup.cfg, ruff, mypy, or similar. Plain Python with `unittest`.
- **Logging**: Uses custom `Log` class (`util/log_utils.py`), not standard `logging`. Methods are `logger.log_info()` and `logger.log_exception()`. Root logging level is set to `ERROR`.
- **@retry decorator**: `util/utils.py` — retries N times with delay, returns `''` on exhaustion. Used on `extract_content()`.
- **Content extraction fallback chain**: newspaper3k → readability → GNE. PDF URLs use PyMuPDF directly.
- **GitHub Actions**: Python 3.9 on `ubuntu-latest`. Installs deps + spaCy model, then runs `python -m src.main`.
