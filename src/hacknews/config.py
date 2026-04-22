"""Validated configuration from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Config:
    """Immutable application configuration."""

    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    email_address: str = ""
    email_password: str = ""
    to_emails: list[str] = field(default_factory=list)
    proxy: str | None = None
    top_n: int = 10
    timeout: int = 3

    @property
    def has_email_credentials(self) -> bool:
        return bool(self.email_address and self.email_password)

    @classmethod
    def from_env(cls, require_email: bool = False) -> Config:
        """Load configuration from environment variables.

        Args:
            require_email: If True, raises ValueError when email creds are missing.

        Raises:
            ValueError: If required variables are missing.
        """
        email_address = os.environ.get("EMAIL_ADDRESS", "").strip()
        email_password = os.environ.get("EMAIL_PASSWORD", "").strip()

        if require_email:
            if not email_address:
                raise ValueError("EMAIL_ADDRESS environment variable is required")
            if not email_password:
                raise ValueError("EMAIL_PASSWORD environment variable is required")

        to_emails_str = os.environ.get("TO_EMAILS", "").strip()
        to_emails = []
        if to_emails_str:
            for addr in to_emails_str.split(","):
                addr = addr.strip()
                if "@" in addr and "." in addr.split("@")[-1]:
                    to_emails.append(addr)

        proxy = os.environ.get("PROXY", "").strip() or None
        top_n = int(os.environ.get("HN_TOP_N", "10"))
        timeout = int(os.environ.get("REQUEST_TIMEOUT", "3"))

        return cls(
            email_address=email_address,
            email_password=email_password,
            smtp_server=os.environ.get("SMTP_SERVER", "smtp.gmail.com"),
            smtp_port=int(os.environ.get("SMTP_PORT", "587")),
            to_emails=to_emails,
            proxy=proxy,
            top_n=top_n,
            timeout=timeout,
        )
