"""In-process cron scheduler for digest jobs."""
from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from hacknews.logging_setup import get_logger
from hacknews.pipeline import run_job

logger = get_logger(__name__)


def _job_handler(job, cfg, hn, sender, ops):
    def _handle() -> None:
        try:
            run_job(cfg, job, hn, sender, ops)
        except Exception as exc:
            logger.exception(
                "job_failed", extra={"event": "job_failed", "job": job.name}
            )
            ops.notify_failure(job.name, str(exc))

    return _handle


def create_scheduler(cfg, hn, sender, ops):
    scheduler = BackgroundScheduler()
    for job in cfg.jobs:
        timezone = job.timezone or cfg.settings.timezone
        scheduler.add_job(
            _job_handler(job, cfg, hn, sender, ops),
            trigger=CronTrigger.from_crontab(job.cron, timezone=timezone),
            id=job.name,
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
    return scheduler
