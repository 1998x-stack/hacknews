# tests/test_hacker_news_fetcher.py
import sys,os
sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/' + '..'))

import unittest
from unittest.mock import patch
from util.hacker_news_fetcher import HackerNewsFetcher


class TestHackerNewsFetcher(unittest.TestCase):
    """测试 HackerNewsFetcher 类。"""

    @patch('requests.get')
    def test_fetch_latest_news_success(self, mock_get):
        """测试成功获取新闻列表的情况。"""
        mock_get.return_value.json.return_value = [1, 2, 3]
        mock_get.return_value.raise_for_status = lambda: None

        fetcher = HackerNewsFetcher(top_n=2)
        news_list = fetcher.fetch_latest_news()
        self.assertEqual(len(news_list), 2)

    @patch('requests.get')
    def test_fetch_news_detail_success(self, mock_get):
        """测试成功获取新闻详情的情况。"""
        mock_get.return_value.json.return_value = {'id': 1, 'title': 'Test News'}
        mock_get.return_value.raise_for_status = lambda: None

        fetcher = HackerNewsFetcher()
        news_detail = fetcher.fetch_news_detail(1)
        self.assertEqual(news_detail['title'], 'Test News')
        
if __name__ == '__main__':
    unittest.main()