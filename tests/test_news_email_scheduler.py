# tests/test_news_email_scheduler.py
import sys,os
sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/' + '..'))

import unittest
from unittest.mock import patch, MagicMock
from util.news_email_scheduler import NewsEmailScheduler
from util.email_sender import EmailSender
from util.hacker_news_fetcher import HackerNewsFetcher


class TestNewsEmailScheduler(unittest.TestCase):
    """测试 NewsEmailScheduler 类。"""

    @patch('schedule.every')
    def test_start(self, mock_schedule_every):
        """测试调度器的启动。"""
        email_sender = MagicMock(spec=EmailSender)
        fetcher = MagicMock(spec=HackerNewsFetcher)
        scheduler = NewsEmailScheduler(email_sender, fetcher)

        with patch('time.sleep', side_effect=InterruptedError):
            with self.assertRaises(InterruptedError):
                scheduler.start()
        mock_schedule_every.assert_called_once()