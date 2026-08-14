import smtplib
from unittest.mock import patch

import pytest

from hacknews.digest_builder import DigestMessage
from hacknews.email_sender import EmailSender


@patch("smtplib.SMTP")
def test_send_success(mock_smtp):
    ctx = mock_smtp.return_value.__enter__.return_value
    sender = EmailSender("host", 587, "a@x.com", "pw")
    sender.send(DigestMessage(subject="S", html="<b>x</b>", plain="x"), ["to@x.com"])
    ctx.sendmail.assert_called_once()


@patch("smtplib.SMTP")
def test_send_raises_after_retries_on_transient_error(mock_smtp):
    ctx = mock_smtp.return_value.__enter__.return_value
    ctx.sendmail.side_effect = smtplib.SMTPServerDisconnected("down")
    sender = EmailSender("host", 587, "a@x.com", "pw")
    with pytest.raises(RuntimeError):
        sender.send(DigestMessage("S", "<b>x</b>", "x"), ["to@x.com"], retries=2)
