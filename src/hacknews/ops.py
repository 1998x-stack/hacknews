"""Ops alerting and last-success state."""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone

from hacknews.digest_builder import DigestMessage
from hacknews.models import OpsConfig


class OpsNotifier:
    def __init__(
        self,
        state_dir: str,
        ops: OpsConfig,
        email_sender=None,
    ) -> None:
        self.state_dir = state_dir
        self.ops = ops
        self.email_sender = email_sender
        os.makedirs(state_dir, exist_ok=True)
        self._last_alert: dict[str, float] = {}

    def _state_file(self, job: str) -> str:
        return os.path.join(self.state_dir, f"{job}.json")

    def record_success(self, job_id: str, stories: int, recipients: int) -> dict:
        payload = {
            "job_id": job_id,
            "last_success_ts": datetime.now(timezone.utc).isoformat(),
            "stories": stories,
            "recipients": recipients,
            "recorded_at": time.time(),
        }
        with open(self._state_file(job_id), "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        return payload

    def last_status(self, job: str) -> dict | None:
        try:
            with open(self._state_file(job), "r", encoding="utf-8") as fh:
                return json.load(fh)
        except FileNotFoundError:
            return None

    def staleness_seconds(self, job: str, max_age_hours: float) -> float:
        status = self.last_status(job)
        if status is None:
            return max_age_hours * 3600 + 1
        return max(0.0, time.time() - (status.get("recorded_at") or 0))

    def notify_failure(self, job: str, error: str) -> bool:
        now = time.time()
        interval = self.ops.min_alert_interval_minutes * 60.0
        if now - self._last_alert.get(job, 0.0) < interval:
            return False
        if self.email_sender is not None and self.ops.alert_emails:
            msg = DigestMessage(
                subject=f"[HackNews] job '{job}' failed",
                html=f"<p><b>{error}</b></p>",
                plain=f"{job} failed:\n{error}",
            )
            try:
                self.email_sender.send(msg, list(self.ops.alert_emails))
            except Exception as exc:  # noqa: BLE001 - alert must never break the job
                self._log_alert_failure(job, exc)
        self._last_alert[job] = now
        return True

    def _log_alert_failure(self, job: str, exc: Exception) -> None:
        if logging.getLogger().hasHandlers():
            logging.getLogger("hacknews.ops").warning(
                "ops alert send failed for job %s: %s", job, exc
            )
