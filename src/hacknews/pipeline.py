"""Orchestrate fetch -> select -> build -> send -> record success."""
from __future__ import annotations

import time

from hacknews.digest_builder import build
from hacknews.logging_setup import get_logger
from hacknews.models import AppConfig, DigestJob, Rules
from hacknews.selector import select

logger = get_logger(__name__)


def run_job(cfg: AppConfig, job: DigestJob, hn, sender, ops) -> dict:
    start = time.time()
    rules = job.rules or Rules()
    stories = select(hn.fetch_top(rules.top_n * 3), rules)
    email = build(job, stories)
    to_emails = [r.email for r in cfg.recipients]
    sender.send(email, to_emails)
    ops.record_success(job.name, stories=len(stories), recipients=len(to_emails))
    logger.info(
        "digest_sent",
        extra={
            "event": "digest_sent",
            "job": job.name,
            "stories": len(stories),
            "recipients": len(to_emails),
            "elapsed": round(time.time() - start, 2),
        },
    )
    return {"job": job.name, "stories": len(stories), "recipients": len(to_emails)}
