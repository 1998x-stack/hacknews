"""SMTP email sender with Markdown-to-HTML conversion."""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import markdown  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)


class EmailSender:
    def __init__(
        self, smtp_server: str, smtp_port: int, username: str, password: str
    ) -> None:
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password

    def send(self, subject: str, body: str, to_emails: list[str]) -> None:
        msg = MIMEMultipart("alternative")
        msg["From"] = self.username
        msg["To"] = ", ".join(to_emails)
        msg["Subject"] = subject

        html_body = markdown.markdown(body)
        msg.attach(MIMEText(body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls()
            server.login(self.username, self.password)
            server.sendmail(self.username, to_emails, msg.as_string())

        logger.info("Email sent to %s", to_emails)
