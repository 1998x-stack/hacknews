"""pydantic domain + config models."""
from __future__ import annotations

from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class Story(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: int
    title: str
    url: str | None = None
    domain: str | None = None
    score: int = 0
    comments: int = 0
    hours_old: float = 0.0
    author: str = ""
    is_dead: bool = False
    text: str | None = None

    @model_validator(mode="after")
    def _derive_domain(self) -> Story:
        if self.domain is None and self.url:
            self.domain = urlparse(self.url).netloc or None
        return self


class Rules(BaseModel):
    min_score: int = 0
    min_comments: int = 0
    max_age_hours: float = 24.0
    top_n: int = 10
    keywords_include: list[str] = Field(default_factory=list)
    keywords_exclude: list[str] = Field(default_factory=list)
    include_self_text: bool = True


class Recipient(BaseModel):
    name: str = ""
    email: EmailStr


class OpsConfig(BaseModel):
    alert_emails: list[EmailStr] = Field(default_factory=list)
    min_alert_interval_minutes: int = 60


class Settings(BaseModel):
    timezone: str = "UTC"
    log_level: str = "INFO"
    max_recipients_per_scan: int = 100


class DigestJob(BaseModel):
    name: str
    cron: str
    timezone: str | None = None
    subject: str
    rules: Rules | None = None


class AppConfig(BaseModel):
    settings: Settings = Field(default_factory=Settings)
    recipients: list[Recipient] = Field(default_factory=list)
    ops: OpsConfig = Field(default_factory=OpsConfig)
    rules_defaults: Rules = Field(default_factory=Rules)
    jobs: list[DigestJob] = Field(default_factory=list)
