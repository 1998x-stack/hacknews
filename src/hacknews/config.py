"""Load YAML config + environment overrides into validated models."""
from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

import yaml

from hacknews.models import AppConfig, DigestJob, Recipient, Rules


def _apply_rules_defaults(job: DigestJob, defaults: Rules) -> DigestJob:
    if job.rules is None:
        job.rules = defaults
    else:
        job.rules = defaults.model_copy(update=job.rules.model_dump())
    return job


def _apply_env(cfg: AppConfig, env: Mapping[str, str] | None) -> AppConfig:
    env = env if env is not None else os.environ
    if env.get("TO_EMAILS"):
        emails = [e.strip() for e in env["TO_EMAILS"].split(",") if e.strip()]
        cfg.recipients = [Recipient(name="", email=e) for e in emails]
    if env.get("TZ"):
        cfg.settings.timezone = env["TZ"]
    if env.get("LOG_LEVEL"):
        cfg.settings.log_level = env["LOG_LEVEL"]
    return cfg


def load_config(config_file: str, env: Mapping[str, str] | None = None) -> AppConfig:
    with open(config_file, "r", encoding="utf-8") as fh:
        raw: dict[str, Any] = yaml.safe_load(fh) or {}
    cfg = AppConfig.model_validate(raw)
    cfg.jobs = [_apply_rules_defaults(job, cfg.rules_defaults) for job in cfg.jobs]
    return _apply_env(cfg, env)
