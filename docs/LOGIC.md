# Hacker News Email Digest - Technical Documentation

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Data Flow](#data-flow)
3. [Module Breakdown](#module-breakdown)
4. [Content Extraction Pipeline](#content-extraction-pipeline)
5. [Configuration & Environment Variables](#configuration--environment-variables)
6. [Error Handling](#error-handling)
7. [Known Issues & Technical Debt](#known-issues--technical-debt)
8. [Dependencies](#dependencies)

---

## Architecture Overview

### System Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            MAIN ENTRY POINT                                  │
│                                   main.py                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                            │
                                            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DATA FETCHING LAYER                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │           HackerNewsFetcher (util/hacker_news_fetcher.py)            │  │
│  │  • Fetches top story IDs from Firebase API                           │  │
│  │  • Fetches individual news details (title, url, id)                  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                            │
                                            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      CONTENT EXTRACTION LAYER                                │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │         ContentExtractor (src/url_extractor.py)                      │  │
│  │  ┌────────────────────────────────────────────────────────────────┐  │  │
│  │  │  PDF Handler (PyMuPDF)                                         │  │  │
│  │  │  • Downloads PDF via HTTP                                      │  │  │
│  │  │  • Extracts text from each page                                │  │  │
│  │  └────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                       │  │
│  │  ┌────────────────────────────────────────────────────────────────┐  │  │
│  │  │  Fallback Chain:                                               │  │  │
│  │  │  1. newspaper3k (primary HTML extractor)                       │  │  │
│  │  │  2. readability-lxml (fallback 1)                              │  │  │
│  │  │  3. GNE - General News Extractor (fallback 2)                  │  │  │
│  │  └────────────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                            │
                                            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FORMATTING LAYER                                     │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │        MarkdownFormatter (util/markdown_formatter.py)                │  │
│  │  • Formats news list into Markdown                                   │  │
│  │  • Adds header with date and title                                   │  │
│  │  • Wraps paragraphs in blockquotes                                   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                            │
                                            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        EMAIL SENDING LAYER                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │              EmailSender (util/email_sender.py)                      │  │
│  │  • Monkey-patches smtplib.encode_base64 to return str                │  │
│  │  • Converts Markdown to HTML using markdown library                  │  │
│  │  • Sends via SMTP with TLS encryption                                │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Descriptions

| Component | Responsibility | Key Dependencies |
|-----------|---------------|------------------|
| **HackerNewsFetcher** | Fetches news metadata from Firebase API | `requests` |
| **ContentExtractor** | Scrapes article content from URLs | `newspaper3k`, `readability-lxml`, `gne`, `PyMuPDF` |
| **MarkdownFormatter** | Formats news into Markdown email body | `datetime` |
| **EmailSender** | Sends formatted email via SMTP | `smtplib`, `markdown` |
| **Log** | Custom logging system | `logging`, `threading` |

---

## Data Flow

### Step-by-Step Execution Flow

#### 1. Entry Point (`main.py`)

```python
# Line 13: Initialize jieba for Chinese segmentation
jieba.cut("初始化")

# Lines 20, 25-26: Initialize components
content_extractor = ContentExtractor()
fetcher = HackerNewsFetcher(top_n=10)

# Lines 27-39: Main execution loop
news_list = fetcher.fetch_latest_news()          # Fetch news metadata
for news in news_list:
    url = news.get('url', '')
    text = content_extractor.extract_content(url, 'en')  # Extract content
    news['text'] = news.get('text', '') + '\n\n' + text  # Append content
body = MarkdownFormatter.format_news(news_list)       # Format as Markdown
email_sender.send_email(subject, body, TO_EMAILS)     # Send email
```

#### 2. Fetching Layer (`hacker_news_fetcher.py`)

```
Firebase API Call Flow:
1. GET https://hacker-news.firebaseio.com/v0/topstories.json
   → Returns list of story IDs [id1, id2, ...]
   
2. For each ID:
   GET https://hacker-news.firebaseio.com/v0/item/{id}.json
   → Returns {id, title, url, score, by, time, ...}
   
3. Filter out items without URLs
4. Return list of up to top_n news items
```

#### 3. Content Extraction (`url_extractor.py`)

```
extract_content(url, lang='en'):
    if url ends with '.pdf':
        → extract_pdf_content(url) using PyMuPDF
    else:
        try newspaper3k:
            Article(url).download().parse()
            → article.text
        except:
            html = fetch_html(url)
            try readability:
                Document(html).summary()
                → content
            except:
                try GNE:
                    extractor.extract(html)
                    → result['content']
                except:
                    return ""
    
    return content  # TextCleaner.clean_text() is commented out
```

#### 4. Formatting (`markdown_formatter.py`)

```
format_news(news_list):
    Header:
        "# 《Hacker News 最新新闻》 📰"
        "> 发布日期：{datetime.now().strftime('%Y-%m-%d')} 📅"
        "---"
    
    For each news item:
        ### [{title}]({url})
        
        > paragraph 1
        > paragraph 2
        ...
        
        ---
    
    Join all lines with '\n'
    Return Markdown string
```

#### 5. Email Sending (`email_sender.py`)

```
send_email(subject, body, to_emails):
    message = MIMEMultipart('alternative')
    message['From'] = username
    message['To'] = ", ".join(to_emails)
    message['Subject'] = subject
    
    html_body = markdown.markdown(body)  # Convert Markdown to HTML
    
    message.attach(MIMEText(body, 'plain', 'utf-8'))
    message.attach(MIMEText(html_body, 'html', 'utf-8'))
    
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(username, password)
        server.sendmail(username, to_emails, message.as_string())
```

---

## Module Breakdown

### `/src/main.py` (Entry Point)

**Purpose:** Orchestrates the entire workflow

**Key Components:**
- `pattern_replace_2_n`: Regex to replace 3+ newlines with 2
- `content_extractor`: ContentExtractor instance
- `main()`: Executes fetch → extract → format → send pipeline

**Dependencies:**
- `util.email_sender.EmailSender`
- `util.hacker_news_fetcher.HackerNewsFetcher`
- `util.markdown_formatter.MarkdownFormatter`
- `src.url_extractor.ContentExtractor`
- `config.config.*` (env vars)

---

### `/src/url_extractor.py` (Content Extraction)

**Purpose:** Extracts article content from URLs (HTML and PDF)

**Class: `ContentExtractor`**

**Attributes:**
| Name | Type | Description |
|------|------|-------------|
| `header_generator` | Headers | Fake user agent headers |
| `newspaper_config` | Configuration | newspaper3k config |
| `request_args` | dict | Request parameters (proxies, timeout, verify) |
| `scrape_count` | int | Counter for scraping attempts |
| `logger` | Log | Logging instance |
| `text_cleaner` | TextCleaner | Text cleaning utilities (currently unused) |
| `quality_dict` | dict | Tracks extraction method success counts |

**Methods:**

| Method | Purpose | Notes |
|--------|---------|-------|
| `__init__()` | Initialize extractor | Sets up configs and request args |
| `fetch_html(url)` | Download raw HTML | Handles cookies for baidu.com |
| `_get_html_from_response(response)` | Decode response | Handles ISO-8859-1 encoding |
| `extract_content(url, lang)` | Main extraction logic | Implements fallback chain |
| `extract_content_by_readability(html)` | Extract via readability-lxml | Returns HTML summary |
| `extract_content_by_gne(html)` | Extract via GNE | Returns normalized content |
| `extract_pdf_content(pdf_url)` | Extract PDF text | Uses PyMuPDF |
| `batch_extract_content(urls, langs)` | Parallel extraction | ThreadPoolExecutor |

**Key Constants:**
- `FAIL_ENCODING = 'ISO-8859-1'`

---

### `/util/hacker_news_fetcher.py` (HN API Client)

**Purpose:** Fetches news from Hacker News Firebase API

**Class: `HackerNewsFetcher`**

**Attributes:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `top_n` | int | 10 | Number of stories to fetch |
| `logger` | Log | logger | Logging instance |

**Methods:**

| Method | Purpose | Returns |
|--------|---------|---------|
| `fetch_latest_news()` | Get top stories | List[Dict] |
| `fetch_news_detail(news_id)` | Get single story detail | Dict |
| `fetch_latest_urls()` | Get latest story URLs | List[str] |
| `fetch_news_url(news_id)` | Get single story URL | str |

**API Endpoints Used:**
- `https://hacker-news.firebaseio.com/v0/topstories.json`
- `https://hacker-news.firebaseio.com/v0/newstories.json`
- `https://hacker-news.firebaseio.com/v0/item/{id}.json`

---

### `/util/markdown_formatter.py` (Formatting)

**Purpose:** Formats news list into Markdown email body

**Class: `MarkdownFormatter`**

**Static Methods:**

| Method | Purpose | Input | Output |
|--------|---------|-------|--------|
| `format_news(news_list)` | Format news list | List[Dict] | str (Markdown) |

**Output Format:**
```markdown
# 《Hacker News 最新新闻》 📰
> 发布日期：2024-01-01 📅
---

### [Title](URL)

> paragraph 1
> paragraph 2

---
```

---

### `/util/email_sender.py` (SMTP Sender)

**Purpose:** Sends formatted email via SMTP

**Monkey Patch:**
```python
def encode_base64(bytestr, eol='\n'):
    """Encode bytestr in base64 and return as str."""
    enc = base64.b64encode(bytestr).decode('ascii')
    if eol:
        enc += eol
    return enc

smtplib.encode_base64 = encode_base64
```

**Why?** Python 3's `smtplib.encode_base64()` returns bytes, but email library expects str. This patch ensures compatibility.

**Class: `EmailSender`**

**Attributes:**
| Name | Type | Description |
|------|------|-------------|
| `smtp_server` | str | SMTP server address |
| `smtp_port` | int | SMTP port |
| `username` | str | Sender email |
| `password` | str | Email password/app password |

**Methods:**

| Method | Purpose | Raises |
|--------|---------|--------|
| `send_email(subject, body, to_emails)` | Send email | Exception on failure |

**Email Structure:**
- MIME type: `multipart/alternative`
- Part 1: Plain text (Markdown)
- Part 2: HTML (converted via `markdown.markdown()`)

---

### `/util/log_utils.py` (Logging)

**Purpose:** Custom logging system with file and console output

**Class: `Log`**

**Attributes:**
| Name | Type | Description |
|------|------|-------------|
| `dir_name` | str | Log directory path |
| `additional_info` | str | Additional context info |

**Methods:**

| Method | Purpose | Parameters |
|--------|---------|------------|
| `log_info(message, print_screen=True)` | Log info message | message: str, print_screen: bool |
| `log_exception(print_screen=True)` | Log exception traceback | print_screen: bool |

**Singleton:**
```python
logger = Log()  # Global logger instance
```

**Features:**
- Thread-safe file writes (uses `threading.Lock`)
- Daily log files: `YYYY-MM-DD-HH.log`
- Root logging level set to ERROR (suppresses third-party logs)

---

### `/util/utils.py` (Utilities)

**Purpose:** Common utility functions

**Custom Exception:**
```python
class EmptyContentError(Exception):
    """Raised when content extraction returns empty or None."""
    pass
```

**Decorator: `@retry`**

```python
@retry(retries=2, delay=0.2)
def extract_content(self, url, lang='en'):
    ...
```

**Behavior:**
- Retries N times on exception or empty return
- Waits `delay` seconds between attempts
- Returns `''` on exhaustion
- Logs failures if logger provided

---

### `/util/text_clean.py` (Text Cleaning - UNUSED)

**Purpose:** Text cleaning utilities (NOT currently used in production)

**Note:** The `clean_text()` method is imported but **commented out** in `url_extractor.py` line 146:
```python
# return self.text_cleaner.clean_text(content)
return content  # Actual code
```

**Class: `TextCleaner`**

**Methods:**
| Method | Purpose |
|--------|---------|
| `remove_html_tags(text)` | Strip HTML tags |
| `remove_urls(text)` | Remove URLs |
| `remove_exception_char(text)` | Remove special chars |
| `convert_full2half(text)` | Full-width to half-width |
| `remove_email(text)` | Remove email addresses |
| `remove_redundant_char(text)` | Remove redundant chars |
| `remove_ip_address(text)` | Remove IP addresses |
| `clean_text(text)` | Full cleanup pipeline |

**Dependencies:**
- Imports patterns from `util.rule_patterns`

---

### `/util/rule_patterns.py` (Regex Patterns)

**Purpose:** Regular expression patterns for text cleaning

**Key Patterns:**
- `CELL_PHONE_PATTERN`: Chinese phone numbers
- `LANDLINE_PHONE_PATTERN`: Fixed-line phones
- `EMAIL_PATTERN`: Email addresses
- `HTML_TAG_PATTERN`: HTML/XML tags
- `EXCEPTION_PATTERN`: Invalid Unicode characters
- `IP_ADDRESS_PATTERN`: IP addresses
- `ID_CARD_PATTERN`: Chinese ID cards

---

### `/util/keywords_extractor.py` (Keyword Extraction - UNUSED)

**Purpose:** Extract keywords using multiple algorithms

**Supported Algorithms:**
- TF-IDF (sklearn)
- RAKE (rake-nltk)
- spaCy noun chunks
- TextRank (gensim)
- YAKE
- POS tagging with frequency analysis

**Status:** Not integrated into main workflow

---

### `/util/news_email_scheduler.py` (Scheduler - UNUSED)

**Purpose:** Scheduled email sending using `schedule` library

**Class: `NewsEmailScheduler`**

**Not Currently Used:** The project uses GitHub Actions cron instead of this scheduler.

---

### `/util/word_cloud.py` (Word Cloud - UNUSED)

**Purpose:** Generate word clouds from paper abstracts

**Status:** Unused in current workflow

---

### `/config/config.py` (Configuration)

**Purpose:** Read environment variables

**Variables:**

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `TIMEOUT` | No | 3 | Request timeout (seconds) |
| `PROXIES` | No | `{}` | If `PROXY` env var set |
| `SMTP_SERVER` | No | `'smtp.gmail.com'` | |
| `SMTP_PORT` | No | `587` | |
| `EMAIL_ADDRESS` | **Yes** | `''` | **Empty string causes runtime error** |
| `EMAIL_PASSWORD` | **Yes** | `''` | |
| `TO_EMAILS` | No | `''` | Comma-separated list |

**Critical Bug:**
```python
EMAIL_ADDRESS = os.environ['EMAIL_ADDRESS'] if 'EMAIL_ADDRESS' in os.environ else ''
EMAIL_PASSWORD = os.environ['EMAIL_PASSWORD'] if 'EMAIL_PASSWORD' in os.environ else ''
```
If these are empty, the email sender will fail at runtime (no validation).

---

## Content Extraction Pipeline

### Fallback Chain Logic

```
┌─────────────────────────────────────────────────────────────────────┐
│                     extract_content(url, lang)                       │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
                    ┌────────────────────┐
                    │ URL ends with .pdf │
                    └────────────────────┘
                               │
               ┌───────────────┴───────────────┐
               ▼                               ▼
        Yes (PDF)                          No (HTML)
               │                               │
               ▼                               ▼
    ┌──────────────────┐            ┌─────────────────────┐
    │ PyMuPDF Extract  │            │  Try newspaper3k    │
    │ (fitz.open)      │            └─────────────────────┘
    └──────────────────┘                       │
               │                               │
        Success?                              │
          ┌──┴──┐                             │
         Yes   No                            ▼
          │    └─────────→ Return ""   ┌──────────────────┐
          ▼                           │ Extract article  │
    Return text                       │ text             │
                                      └──────────────────┘
                                                  │
                                          Success?
                                            ┌──┴──┐
                                           Yes   No
                                            │    └─────────→ Fetch HTML
                                            ▼               │
                                      Return text           ▼
                                                        ┌─────────────────┐
                                                        │ Try readability │
                                                        └─────────────────┘
                                                                    │
                                                            Success?
                                                              ┌──┴──┐
                                                             Yes   No
                                                              │    └─────────→ Return ""
                                                              ▼
                                                        Return text
```

### Quality Tracking

The `quality_dict` tracks which method succeeded:

```python
self.quality_dict = {
    "newspaper3k": 0,
    "readability": 0,
    "gne": 0,
    "failed": 0,
}
```

Incremented after successful extraction via each method.

---

## Configuration & Environment Variables

### Runtime Configuration Flow

```
Environment Variables
         │
         ▼
┌─────────────────────┐
│  config/config.py   │
│  (reads os.environ) │
└─────────────────────┘
         │
         ├──► SMTP_SERVER, SMTP_PORT
         ├──► EMAIL_ADDRESS, EMAIL_PASSWORD (REQUIRED)
         ├──► TO_EMAILS
         └──► PROXIES (if PROXY set)
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  Passed to components during initialization             │
│  • EmailSender(SMTP_SERVER, SMTP_PORT, ...)            │
│  • ContentExtractor(request_args={'proxies': PROXIES}) │
└─────────────────────────────────────────────────────────┘
```

### GitHub Actions Secrets

Required secrets in repository settings:
- `EMAIL_ADDRESS`
- `EMAIL_PASSWORD`
- `SMTP_SERVER` (optional, defaults to gmail)
- `SMTP_PORT` (optional, defaults to 587)
- `TO_EMAILS`
- `PROXY` (optional)

---

## Error Handling

### Error Handling Patterns

#### 1. Network Errors (`hacker_news_fetcher.py`)

```python
try:
    response = requests.get(url)
    response.raise_for_status()
    # process
except requests.RequestException as e:
    self.logger.log_exception()
    return []  # or {}
```

#### 2. Content Extraction Errors (`url_extractor.py`)

```python
try:
    article.download()
    article.parse()
    content = article.text
    assert content, f"Empty content from {url}"
except Exception as e:
    self.logger.log_exception()
    # Fall through to next method
```

#### 3. Retry Mechanism (`utils.py`)

```python
@retry(retries=2, delay=0.2)
def extract_content(self, url, lang='en'):
    # Returns '' on exhaustion
```

#### 4. Email Sending Errors (`email_sender.py`)

```python
try:
    with smtplib.SMTP(...) as server:
        server.starttls()
        server.login(...)
        server.sendmail(...)
except Exception as e:
    logger.log_exception()
    # Swallows exception, no re-raise
```

### Known Error Cases

| Location | Error | Mitigation |
|----------|-------|------------|
| `config.py` | Empty `EMAIL_ADDRESS` | No validation, fails at runtime |
| `email_sender.py` | SMTP authentication failed | Caught, logged, silently ignored |
| `url_extractor.py` | All extraction methods fail | Returns empty string |
| `main.py` | No news fetched | Skips email sending |

---

## Known Issues & Technical Debt

### 1. Stale README

**Issue:** README lists incorrect file structure

**README says:**
```
src/
├── email_sender.py
├── hacker_news_fetcher.py
├── markdown_formatter.py
```

**Actual structure:**
```
src/
├── main.py
└── url_extractor.py

util/
├── email_sender.py
├── hacker_news_fetcher.py
├── markdown_formatter.py
├── log_utils.py
├── utils.py
├── text_clean.py
├── keywords_extractor.py
├── news_email_scheduler.py
├── word_cloud.py
└── rule_patterns.py

config/
└── config.py
```

### 2. Import Hack

**Every file does:**
```python
import sys, os
sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/' + '..'))
```

**Why:** Makes `util/` and `config/` importable from `src/`

**Warning:** Do NOT "fix" this — it's fundamental to how the project imports work.

### 3. Dead Code

**Unused modules:**
- `util/text_clean.py` — Imported but `clean_text()` is commented out
- `util/keywords_extractor.py` — Not used anywhere
- `util/news_email_scheduler.py` — Not used (GitHub Actions handles scheduling)
- `util/word_cloud.py` — Not used

**Unused test:**
- `tests/test_news_email_scheduler.py` — Tests unused component

### 4. Missing Validation

**In `config/config.py`:**
```python
EMAIL_ADDRESS = os.environ['EMAIL_ADDRESS'] if 'EMAIL_ADDRESS' in os.environ else ''
EMAIL_PASSWORD = os.environ['EMAIL_PASSWORD'] if 'EMAIL_PASSWORD' in os.environ else ''
```

**Problem:** No validation that these are non-empty. Will fail at runtime with cryptic error.

**Recommendation:** Add assertion:
```python
assert EMAIL_ADDRESS, "EMAIL_ADDRESS environment variable is required"
assert EMAIL_PASSWORD, "EMAIL_PASSWORD environment variable is required"
```

### 5. Hardcoded Values

| Location | Value | Recommendation |
|----------|-------|----------------|
| `hacker_news_fetcher.py` | `top_n=10` | Make configurable |
| `url_extractor.py` | Baidu cookies | Should be conditional on domain |
| `markdown_formatter.py` | Emoji in header | Fine, but consider localization |

### 6. No Type Hints

Most functions lack type hints, making refactoring risky.

### 7. No Linting/Type Checking

No `pyproject.toml`, `setup.cfg`, `.flake8`, `mypy`, or similar configuration.

### 8. Print Statements in Production Code

Several files contain `print()` statements that should be removed:
- `text_clean.py`: Multiple `print(f"...")` calls
- `url_extractor.py`: Some debug prints

### 9. Missing Test Coverage

No tests for:
- `ContentExtractor`
- `MarkdownFormatter`
- `Log` class
- `utils.retry` decorator

### 10. Inconsistent Naming

- Files use snake_case (`hacker_news_fetcher.py`)
- Classes use PascalCase (`HackerNewsFetcher`)
- Some comments in Chinese, some in English
- Mixed quoting styles (single vs double)

---

## Dependencies

### Primary Dependencies (requirements.txt)

| Package | Purpose | Usage Location |
|---------|---------|----------------|
| `requests` | HTTP client | All network operations |
| `schedule` | Task scheduling | `news_email_scheduler.py` (unused) |
| `markdown` | Markdown → HTML | `email_sender.py` |
| `fake-headers` | User-agent generation | `url_extractor.py` |
| `newspaper3k` | Article extraction | `url_extractor.py` (primary) |
| `readability-lxml` | HTML parsing | `url_extractor.py` (fallback 1) |
| `gne` | General News Extractor | `url_extractor.py` (fallback 2) |
| `PyMuPDF` (fitz) | PDF text extraction | `url_extractor.py` (PDF handler) |
| `pandas` | Data manipulation | Test script usage only |
| `jieba` | Chinese segmentation | `main.py` (initialization) |
| `certifi` | SSL certificates | `url_extractor.py` |
| `lxml[html_clean]` | HTML parsing | `readability-lxml` dependency |
| `rake-nltk` | Keyword extraction | `keywords_extractor.py` (unused) |
| `spacy` | NLP | `keywords_extractor.py` (unused) |
| `scikit-learn` | ML | `keywords_extractor.py` (TF-IDF, unused) |
| `gensim` | NLP | `keywords_extractor.py` (TextRank, unused) |
| `yake` | Keyword extraction | `keywords_extractor.py` (unused) |
| `nltk` | NLP | `keywords_extractor.py` (POS tagging, unused) |
| `wordcloud` | Word cloud generation | `word_cloud.py` (unused) |

### Transitive Dependencies

Many packages pull in their own dependencies (e.g., `newspaper3k` → `feedparser`, `chardet`, etc.)

### CI/CD Requirements

GitHub Actions workflow installs spaCy model explicitly:
```yaml
python -m spacy download en_core_web_sm
```

This is **not** in `requirements.txt` but required for `keywords_extractor.py` functionality.

---

## Appendix: File Inventory

### Active Files (Used in Production)

| Path | Purpose |
|------|---------|
| `src/main.py` | Entry point |
| `src/url_extractor.py` | Content extraction |
| `util/hacker_news_fetcher.py` | HN API client |
| `util/email_sender.py` | SMTP sender |
| `util/markdown_formatter.py` | Markdown formatting |
| `util/log_utils.py` | Logging |
| `util/utils.py` | Utilities (@retry) |
| `config/config.py` | Config reader |
| `util/rule_patterns.py` | Regex patterns (imported by text_clean) |

### Unused Files (Can Be Removed)

| Path | Reason |
|------|--------|
| `util/text_clean.py` | clean_text() commented out |
| `util/keywords_extractor.py` | Never called |
| `util/news_email_scheduler.py` | GitHub Actions handles scheduling |
| `util/word_cloud.py` | Never called |
| `tests/test_news_email_scheduler.py` | Tests unused code |

### Test Files

| Path | Tests |
|------|-------|
| `tests/test_email_sender.py` | EmailSender |
| `tests/test_hacker_news_fetcher.py` | HackerNewsFetcher |

---

*Document generated: April 2026*
