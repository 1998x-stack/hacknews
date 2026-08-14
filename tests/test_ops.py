from hacknews.models import OpsConfig
from hacknews.ops import OpsNotifier


def test_record_and_read_success(tmp_path):
    ops = OpsNotifier(str(tmp_path), OpsConfig())
    ops.record_success("m", stories=3, recipients=2)
    status = ops.last_status("m")
    assert status and status["stories"] == 3 and status["recipients"] == 2


def test_staleness_when_no_state(tmp_path):
    ops = OpsNotifier(str(tmp_path), OpsConfig())
    assert ops.staleness_seconds("x", 1.0) > 3600


def test_notify_failure_throttled(tmp_path):
    ops = OpsNotifier(
        str(tmp_path),
        OpsConfig(alert_emails=["ops@x.com"], min_alert_interval_minutes=60),
        email_sender=object(),
    )
    assert ops.notify_failure("j", "boom") is True
    assert ops.notify_failure("j", "boom again") is False
