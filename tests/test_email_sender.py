# tests/test_email_sender.py
import sys,os
sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/' + '..'))

import unittest
from unittest.mock import patch, MagicMock
from util.email_sender import EmailSender


class TestEmailSender(unittest.TestCase):
    """测试 EmailSender 类。"""

    @patch('smtplib.SMTP')
    def test_send_email_success(self, mock_smtp):
        """测试成功发送邮件的情况。"""
        smtp_instance = mock_smtp.return_value.__enter__.return_value
        smtp_instance.sendmail.return_value = {}

        email_sender = EmailSender('smtp.test.com', 587, 'user@test.com', 'password')
        email_sender.send_email('Test Subject', 'Test Body', ['receiver@test.com'])
        smtp_instance.sendmail.assert_called_once()

    @patch('smtplib.SMTP')
    def test_send_email_failure(self, mock_smtp):
        """测试发送邮件失败的情况。"""
        smtp_instance = mock_smtp.return_value.__enter__.return_value
        smtp_instance.sendmail.side_effect = Exception('SMTP Error')

        email_sender = EmailSender('smtp.test.com', 587, 'user@test.com', 'password')
        with self.assertRaises(Exception):
            email_sender.send_email('Test Subject', 'Test Body', ['receiver@test.com'])