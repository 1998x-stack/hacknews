from unittest.mock import MagicMock

import pytest

from hacknews.hn_client import HNAPIError
from hacknews.models import AppConfig, DigestJob, Recipient
from hacknews.pipeline import run_job


def _cfg():
    return AppConfig(
        recipients=[Recipient(name="", email="to@x.com")],
        jobs=[DigestJob(name="m", cron="0 8 * * *", subject="S")],
    )


def test_run_job_success():
    hn = MagicMock()
    hn.fetch_top.return_value = []
    sender = MagicMock()
    ops = MagicMock()
    cfg = _cfg()
    result = run_job(cfg, cfg.jobs[0], hn, sender, ops)
    assert result["recipients"] == 1
    sender.send.assert_called_once()
    ops.record_success.assert_called_once()


def test_run_job_propagates_api_failure():
    hn = MagicMock()
    hn.fetch_top.side_effect = HNAPIError("down")
    cfg = _cfg()
    with pytest.raises(HNAPIError):
        run_job(cfg, cfg.jobs[0], hn, MagicMock(), MagicMock())
