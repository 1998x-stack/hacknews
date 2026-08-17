"""SMTP email sending with bounded retries."""
from __future__ import annotations

import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from hacknews.digest_builder import DigestMessage


class EmailSender:
    def __init__(self, host: str, port: int, from_addr: str, password: str) -> None:
        self.host = host
        self.port = port
        self.from_addr = from_addr
        self.password = password

    def send(self, msg: DigestMessage, to_emails: list[str], retries: int = 3) -> None:
        last_exc: Exception | None = None
        for attempt in range(retries):
            try:
                self._send_once(msg, to_emails)
                return
            except smtplib.SMTPAuthenticationError:
                raise  # auth failures are hard - never retry them
            except (smtplib.SMTPServerDisconnected, smtplib.SMTPSenderRefused, OSError) as exc:
                last_exc = exc
                time.sleep(0.5 * (attempt + 1))
        raise RuntimeError(f"SMTP send failed: {last_exc}") from last_exc

    def _send_once(self, msg: DigestMessage, to_emails: list[str]) -> None:
        root = MIMEMultipart("alternative")
        root["From"] = self.from_addr
        root["To"] = ", ".join(to_emails)
        root["Subject"] = msg.subject
        root.attach(MIMEText(msg.plain, "plain", "utf-8"))
        root.attach(MIMEText(msg.html, "html", "utf-8"))
        with smtplib.SMTP(self.host, self.port) as server:
            server.starttls()
            server.login(self.from_addr, self.password)
            server.sendmail(self.from_addr, to_emails, root.as_string())
