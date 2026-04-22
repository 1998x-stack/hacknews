from unittest.mock import MagicMock, patch

from hacknews.sender import EmailSender


class TestEmailSender:
    def setup_method(self):
        self.sender = EmailSender("smtp.gmail.com", 587, "user@gmail.com", "pass")

    def test_send_connects_and_authenticates(self):
        with patch("hacknews.sender.smtplib.SMTP") as mock_smtp_class:
            mock_server = MagicMock()
            mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

            self.sender.send("Subject", "Body", ["to@example.com"])

            mock_smtp_class.assert_called_once_with("smtp.gmail.com", 587)
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once_with("user@gmail.com", "pass")
            mock_server.sendmail.assert_called_once()
            call_args = mock_server.sendmail.call_args
            assert call_args[0][0] == "user@gmail.com"
            assert call_args[0][1] == ["to@example.com"]

    def test_send_multiple_recipients(self):
        with patch("hacknews.sender.smtplib.SMTP") as mock_smtp_class:
            mock_server = MagicMock()
            mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

            self.sender.send("Subject", "Body", ["a@x.com", "b@y.com"])

            call_args = mock_server.sendmail.call_args
            assert call_args[0][1] == ["a@x.com", "b@y.com"]
