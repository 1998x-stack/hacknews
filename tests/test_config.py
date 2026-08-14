
from hacknews.config import load_config

SAMPLE = """settings: { timezone: "UTC", log_level: "INFO" }
recipients: [{name: A, email: a@x.com}]
ops: {alert_emails: ["ops@x.com"], min_alert_interval_minutes: 60}
rules_defaults: {top_n: 10}
jobs:
  - {name: morning, cron: "0 8 * * *", subject: "Morning"}
"""


def _write_sample(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(SAMPLE)
    return str(path)


def test_load_config_applies_rules_defaults(tmp_path):
    cfg = load_config(_write_sample(tmp_path))
    assert cfg.jobs[0].rules is not None
    assert cfg.jobs[0].rules.top_n == 10
    assert cfg.settings.timezone == "UTC"


def test_load_config_env_overrides_recipients(tmp_path):
    cfg = load_config(_write_sample(tmp_path), env={"TO_EMAILS": "b@x.com,c@x.com"})
    assert [r.email for r in cfg.recipients] == ["b@x.com", "c@x.com"]
