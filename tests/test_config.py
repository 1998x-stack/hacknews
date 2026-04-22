import os
from unittest.mock import patch

import pytest

from hacknews.config import Config


def test_from_env_with_minimal_vars():
    env = {"EMAIL_ADDRESS": "a@b.com", "EMAIL_PASSWORD": "pass"}
    with patch.dict(os.environ, env, clear=True):
        cfg = Config.from_env()
    assert cfg.email_address == "a@b.com"
    assert cfg.email_password == "pass"
    assert cfg.smtp_server == "smtp.gmail.com"
    assert cfg.smtp_port == 587
    assert cfg.to_emails == []
    assert cfg.proxy is None
    assert cfg.top_n == 10
    assert cfg.timeout == 3


def test_from_env_with_all_vars():
    env = {
        "EMAIL_ADDRESS": "x@y.com",
        "EMAIL_PASSWORD": "secret",
        "SMTP_SERVER": "smtp.example.com",
        "SMTP_PORT": "465",
        "TO_EMAILS": "r1@a.com,r2@b.com",
        "PROXY": "proxy.local:8080",
        "HN_TOP_N": "20",
        "REQUEST_TIMEOUT": "5",
    }
    with patch.dict(os.environ, env, clear=True):
        cfg = Config.from_env()
    assert cfg.smtp_server == "smtp.example.com"
    assert cfg.smtp_port == 465
    assert cfg.to_emails == ["r1@a.com", "r2@b.com"]
    assert cfg.proxy == "proxy.local:8080"
    assert cfg.top_n == 20
    assert cfg.timeout == 5


def test_from_env_missing_email_address():
    with patch.dict(os.environ, {"EMAIL_PASSWORD": "pass"}, clear=True):
        with pytest.raises(ValueError, match="EMAIL_ADDRESS"):
            Config.from_env(require_email=True)


def test_from_env_missing_email_password():
    with patch.dict(os.environ, {"EMAIL_ADDRESS": "a@b.com"}, clear=True):
        with pytest.raises(ValueError, match="EMAIL_PASSWORD"):
            Config.from_env(require_email=True)


def test_from_env_empty_email_address():
    env = {"EMAIL_ADDRESS": "  ", "EMAIL_PASSWORD": "pass"}
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(ValueError, match="EMAIL_ADDRESS"):
            Config.from_env(require_email=True)


def test_from_env_to_emails_strips_whitespace():
    env = {"EMAIL_ADDRESS": "a@b.com", "EMAIL_PASSWORD": "p", "TO_EMAILS": " x@y.com , z@w.com "}
    with patch.dict(os.environ, env, clear=True):
        cfg = Config.from_env()
    assert cfg.to_emails == ["x@y.com", "z@w.com"]


def test_from_env_empty_to_emails():
    env = {"EMAIL_ADDRESS": "a@b.com", "EMAIL_PASSWORD": "p", "TO_EMAILS": ""}
    with patch.dict(os.environ, env, clear=True):
        cfg = Config.from_env()
    assert cfg.to_emails == []


def test_from_env_filters_invalid_emails():
    env = {
        "EMAIL_ADDRESS": "a@b.com",
        "EMAIL_PASSWORD": "p",
        "TO_EMAILS": "valid@x.com,invalid,bad@,also@y.com",
    }
    with patch.dict(os.environ, env, clear=True):
        cfg = Config.from_env()
    assert cfg.to_emails == ["valid@x.com", "also@y.com"]


def test_config_is_immutable():
    env = {"EMAIL_ADDRESS": "a@b.com", "EMAIL_PASSWORD": "p"}
    with patch.dict(os.environ, env, clear=True):
        cfg = Config.from_env()
    with pytest.raises(AttributeError):
        cfg.smtp_server = "other"  # type: ignore[misc]


def test_from_env_without_email():
    with patch.dict(os.environ, {}, clear=True):
        cfg = Config.from_env(require_email=False)
    assert cfg.email_address == ""
    assert cfg.email_password == ""
    assert not cfg.has_email_credentials
