# HackNews

Scheduled Hacker News email digests delivered by email. Production-grade:
a resilient HN API client, configurable selection rules, cron scheduling
(in-process or via CI), structured JSON logs, SMTP sending with ops alert
emails, and a readiness/last-success signal. Runs as a containerized
long-lived service or as a one-shot job (e.g. GitHub Actions).

No external article scraping — each digest is built purely from Hacker News
metadata: title, link, score, comment count, age, author, domain, and
Ask/Show self-text.

## Install

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

## Layout

```
src/hacknews/
    models.py          pydantic domain + config models
    config.py          YAML + env -> validated AppConfig
    logging_setup.py   structured JSON logging to stdout
    hn_client.py       resilient HN API client (retries/backoff)
    selector.py        apply per-job selection rules
    digest_builder.py  build HTML + plaintext digest
    email_sender.py    SMTP send with bounded retries
    ops.py             ops alerts + last-success state
    pipeline.py        orchestrate fetch -> select -> build -> send -> record
    scheduler.py       in-process cron scheduler (APScheduler)
    health.py          /healthz endpoint
    cli.py             entry points (doctor / run / readiness / serve)
```

The same pipeline runs as a long-lived service (`serve`) or a one-shot job
(`run <job>`).

## Quickstart

```bash
.venv/bin/hacknews doctor               # validate config, print report
.venv/bin/hacknews run morning_digest   # run one digest and exit
.venv/bin/hacknews readiness            # 0 if all jobs fresh, else 1 + stale list
.venv/bin/hacknews serve                # cron scheduler + /healthz on :8080
```

## Configuration

Structure lives in `config.yaml`; **secrets only in the environment**.

`config.yaml` sections: `settings` (timezone, log level),
`recipients` (who receives digests), `ops` (alert email + throttle),
`jobs` (cron-scheduled deliveries, each with optional `rules`), and
`rules_defaults` (merged into every job).

Selection rules per job: `min_score`, `min_comments`, `max_age_hours`,
`top_n`, `keywords_include`, `keywords_exclude`, `include_self_text`.

Environment variables:

| Variable | Purpose |
|----------|---------|
| `SMTP_HOST` | SMTP server (required to send) |
| `SMTP_PORT` | SMTP port, default `587` |
| `EMAIL_FROM` | Sender address / login user |
| `EMAIL_FROM_PASSWORD` | Sender password / app password |
| `PROXY` | Optional HTTP(S) proxy for HN fetch |
| `TZ` | Overrides `settings.timezone` |
| `LOG_LEVEL` | Overrides `settings.log_level` |
| `TO_EMAILS` | Comma-separated recipient override (e.g. CI trigger) |

Every job: fetch → select → build digest → SMTP send → record last-success.
On failure it logs a structured error, sends a throttled ops alert email, and
does not record success — so a silent miss is impossible.

## Docker / deploy

```bash
docker compose up --build   # local run (cron + healthz, ports 8080)
```

`Dockerfile` runs as non-root with a `HEALTHCHECK` against `/healthz`.
Persist the `state/` directory (last-success JSON) across restarts.

`.github/workflows/ci.yml` lints + runs tests on every push/PR.
`.github/workflows/deploy.yml` builds the image and can trigger a one-shot
`run` via `schedule`/`workflow_dispatch` (set SMTP secrets in GH Secrets).