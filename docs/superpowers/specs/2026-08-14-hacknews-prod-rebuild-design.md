# HackNews Production Rebuild — Design

**Date:** 2026-08-14
**Status:** Approved (sections 1–4)

## Goal

Totally reconstruct the existing Hacker News email project into a genuine
production-grade system: robust, observable, well-architected, and
deployable. The pipeline delivers one or more scheduled email digests of
Hacker News **metadata** (no fragile external article scraping).

## Decisions (from brainstorming)

| # | Decision |
|---|----------|
| Scope | Full production-grade rebuild — robustness, architecture, and deployment |
| Runtime | Containerized app deployable via CI; GitHub Actions retained as a trigger (one-shot `--once`) |
| Product | Digest + key context from the HN API: score, comment count, age, author, domain, HN comments URL, Ask/Show self-text. No article-body scraping |
| Recipients | Single shared recipient list for all jobs |
| Schedules | Multiple config-defined cron jobs (arbitrary cadences), defined in YAML |
| Selection | Custom rules per job: min score, min comments, max age, keyword include/exclude, N cap |
| Ops | Structured JSON logs + ops alert email (throttled) + readiness/last-success probe |
| Language | English everywhere (code, docs, email) |
| Config | Hybrid: YAML for structure, env for secrets/overrides |
| Scheduler | In-process cron scheduler + `--once` CLI; clean injectable core (Option 3) |

## Architecture & project layout

Clean-room structure replacing the current `src/` + `util/` layout:

```
hacknews/
├── pyproject.toml            # packaging + pinned deps + ruff/pytest config
├── config.yaml               # the one human-edited config
├── Dockerfile                # slim image, non-root, healthcheck
├── docker-compose.yml        # local dev
├── .github/workflows/ci.yml      # lint + unit tests on push/PR
├── .github/workflows/deploy.yml  # build & push image; schedule as a trigger
├── src/hacknews/
│   ├── config.py             # YAML + env overlay → validated model (pydantic)
│   ├── models.py             # pydantic dataclasses (Digest, Rules, Recipient, Job, Settings)
│   ├── hn_client.py          # HackerNewsClient: topstories + item fetch, retry/backoff, proxy
│   ├── selector.py           # SelectionRules apply → ranked/deduped stories
│   ├── digest_builder.py     # HTML + plaintext digest from HN metadata
│   ├── email_sender.py       # SMTP+TLS, retries, raises on hard failure
│   ├── ops.py                # OpsNotifier: ops alert email + last-success state
│   ├── logging_setup.py      # structured JSON logger
│   ├── scheduler.py          # in-process cron scheduler (apscheduler) + /healthz
│   └── cli.py                # CLI: run | --once | doctor | readiness
├── tests/                    # pytest per module
└── state/                    # runtime state (last-success files)
```

Core design principle: `hn_client`, `selector`, `digest_builder`, and
`email_sender` are pure, injectable, dependency-light units with no I/O
globals, each testable in isolation. `config`, `scheduler`, `ops`, and `cli`
are thin integration/orchestration layers. The same code runs as a long-lived
container or as a one-shot under GitHub Actions (`--once`).

### Component responsibilities

- **HackerNewsClient** — fetch top stories + item details; retries/backoff;
  optional proxy; returns clean `Story` models (title, url, domain, score,
  comments, age, author, dead/flagged flags, `text` for Ask/Show).
- **Selector** — applies each job's `rules`: min score, min comments, max age,
  keyword include/exclude (title/domain/self-text), N cap, stable ranking and
  dedupe within the job.
- **DigestBuilder** — builds HTML body + plaintext fallback from selected
  `Story` metadata (title→link, domain, score, comment count, age, HN comments
  URL, Ask/Show self-text snippet). No external article scraping.
- **EmailSender** — SMTP config from env secrets; TLS; HTML+text multipart;
  bounded retries on transient errors; raises on hard failure.
- **OpsNotifier** — on failure sends an ops alert email (throttled) and, on
  success, writes a last-success state record.
- **Scheduler** — APScheduler cron jobs loaded from YAML (each with cron +
  timezone), SIGTERM graceful shutdown, tiny `/healthz` HTTP endpoint.

## Config model & scheduling

Hybrid config: structure in `config.yaml`, secrets in environment variables.

### config.yaml

```yaml
settings:
  timezone: "Asia/Shanghai"
  log_level: INFO
  max_recipients_per_scan: 100

recipients:                      # shared digest recipients
  - name: Jane
    email: jane@example.com

ops:                             # ops alert channel
  alert_emails: [ops-alerts@example.com]
  min_alert_interval_minutes: 60

rules_defaults:                  # base rules inherited by jobs
  min_score: 0
  min_comments: 0
  max_age_hours: 24
  top_n: 10
  keywords_include: []
  keywords_exclude: []
  include_self_text: true

jobs:                            # scheduled deliveries
  - name: morning_digest
    cron: "0 8 * * *"
    timezone: Asia/Shanghai
    rules:
      top_n: 5
      keywords_include: [AI, LLM, Rust]
    subject: "Morning HN Digest"
  - name: evening_top10
    cron: "0 20 * * *"
    rules:
      min_score: 200
```

### Environment (secrets/overrides)

`SMTP_HOST`, `SMTP_PORT`, `EMAIL_FROM`, `EMAIL_FROM_PASSWORD`, `TZ`,
`LOG_LEVEL`, `PROXY`, and optional `TO_EMAILS` to override the YAML recipients
(for the GH-Acts test trigger). Secrets are read only from env at runtime.

- `config.py` parses all YAML into **pydantic-validated models**; malformed
  config fails fast and loudly at startup (config error), not mid-run.
- `scheduler.py` registers each `DigestJob` with APScheduler at its cron +
  timezone. A job lock prevents concurrent runs of the same job and handles
  misfires/overlaps. Container holds scheduler + `/healthz` in one process.
- `deploy.yml` keeps a GH Actions schedule calling the same image with
  `--once job=<name>` as a cloud-triggered fallback (identical pipeline).

## Reliability, ops & error handling

Pipeline per job: `fetch → select → build → send → record last-success`, with
failure → ops alert.

- **Hardened fetching:** `urllib3` `Retry` with exponential backoff + jitter
  on transient errors (5xx, timeouts, resets), 3 retries; per-request timeout;
  optional proxy. Filters `dead`/`deleted`; tolerates individual item-fetch
  failures (skip that story) but fails the whole job if the HN API is
  unreachable entirely.
- **Failure model:** transient SMTP errors retried; hard failures (SMTP auth,
  invalid config, HN API down, bad cron) propagate to the job boundary. The
  boundary handler logs a structured error, calls `OpsNotifier.notify_failure`
  (throttled), and does **not** write last-success. Nothing is silently
  swallowed.
- **Structured JSON logging:** `ts`, `level`, `job`, `event`
  (fetch_started / digest_built / mail_sent / job_failed / config_invalid) +
  contextual fields (story count, elapsed, recipient count). `LOG_LEVEL` from
  env; logs to stdout, optionally file.
- **Health / last-success:** after a successful send, `ops.py` writes
  `state/last_success.json`: `{ job_id, last_success_ts, stories, recipients }`.
  `readiness` CLI + `/healthz` return liveness (200) and per-job
  last-success with staleness warning (e.g., ">48h stale"). Docker
  `HEALTHCHECK` curls `/healthz`.
- **Graceful shutdown:** scheduler traps `SIGTERM`/`SIGINT`, flushes in-flight
  work, writes no fake last-success, exits cleanly.

## Testing & deployment & cleanup

### Testing (pytest)

- `test_config.py` — YAML+env parsing, validation failures (bad cron, missing
  SMTP), env overlays.
- `test_hn_client.py` — mocked requests: success, transient-retry-then-succeed,
  hard failure raises, dead-item filtering, item-fetch tolerance.
- `test_selector.py` — rules in order (score, comments, age, keywords, N,
  dedupe), keyword include/exclude, ordering.
- `test_digest_builder.py` — snapshot tests of HTML + plaintext; self-text
  truncation; escaping of user content.
- `test_email_sender.py` — mocked SMTP: retry on transient, raise on hard
  failure, correct MIME.
- `test_ops.py` — last-success state write/read, staleness, alert throttling.
- `test_scheduler.py` — cron parsing, job registration, no-concurrency lock,
  `--once` path.

### Deployment / CI

- `ci.yml`: on push/PR — `ruff` lint + `pytest` (fast, no network; network
  faked). Green = deploy gate.
- `deploy.yml` + Dockerfile: build slim non-root image with `HEALTHCHECK` on
  `/healthz`, push to registry, deploy long-running scheduler container. Keep
  a GH Actions `schedule` using `--once` as a configurable fallback trigger.
- `docker-compose.yml` for local reproducibility.

### Cleanup of legacy code

- Remove `util/`, `src/url_extractor.py`, old `main.py`, and the content
  scraping stack (newspaper3k, readability, gne, fitz, jieba, fake-headers,
  pandas, etc.).
- Replace the stale README with English docs: quickstart, config reference,
  local run, deploy, ops/health.
- Replace the env-var contract (`EMAIL_ADDRESS` → `EMAIL_FROM`, etc.).