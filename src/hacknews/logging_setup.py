"""Structured JSON logging to stdout."""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


class JsonFormatter(logging.Formatter):
    EXTRA_FIELDS = ("stories", "elapsed", "recipients", "job_id")

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "job": getattr(record, "job", None),
            "event": getattr(record, "event", None),
            "message": record.getMessage(),
        }
        for key in self.EXTRA_FIELDS:
            value = getattr(record, key, None)
            if value is not None and key not in payload:
                payload[key] = value
        return json.dumps(payload, ensure_ascii=False, default=str)


class _DefaultJobFilter(logging.Filter):
    def __init__(self) -> None:
        super().__init__()
        self.job: str | None = None

    def filter(self, record: logging.LogRecord) -> bool:
        if record.__dict__.get("job") is None and self.job:
            record.__dict__["job"] = self.job
        return True


_job_filter = _DefaultJobFilter()


def setup_logging(level: str = "INFO", job: str | None = None) -> None:
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    for handler in list(root.handlers):
        root.removeHandler(handler)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    if job:
        set_default_job(job)


def set_default_job(job: str | None) -> None:
    """Set the default job name attached to records emitted by get_logger()."""
    _job_filter.job = job


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.addFilter(_job_filter)
    return logger
