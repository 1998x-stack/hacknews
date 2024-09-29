# src/hacker_news_fetcher.py
import sys,os
sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/' + '..'))

import requests
from typing import List, Dict

from util.log_utils import logger

class HackerNewsFetcher:
    """用于从 Hacker News API 获取最新新闻的类。

    Attributes:
        top_n: 要获取的新闻数量。
    """

    def __init__(self, top_n: int = 10, logger=logger):
        """初始化 HackerNewsFetcher 实例。

        Args:
            top_n: 要获取的新闻数量，默认为 10 条。
        """
        self.top_n = top_n
        self.logger = logger

    def fetch_latest_news(self) -> List[Dict]:
        """获取最新的新闻列表。

        Returns:
            List[Dict]: 包含新闻详情的列表。
        """
        try:
            # 获取最新的新闻 ID 列表
            response = requests.get('https://hacker-news.firebaseio.com/v0/topstories.json')
            response.raise_for_status()
            news_ids = response.json()[:self.top_n]
            self.logger.log_info(f"获取到的新闻 ID：{news_ids}")

            # 获取每个新闻的详细信息
            news_list = []
            for news_id in news_ids:
                news_detail = self.fetch_news_detail(news_id)
                if news_detail:
                    news_list.append(news_detail)
            self.logger.log_info(f"共获取到 {len(news_list)} 条新闻。")
            return news_list
        except requests.RequestException as e:
            self.logger.log_exception()
            return []

    def fetch_news_detail(self, news_id: int) -> Dict:
        """获取单条新闻的详细信息。

        Args:
            news_id: 新闻的 ID。

        Returns:
            Dict: 新闻的详细信息。
        """
        try:
            url = f'https://hacker-news.firebaseio.com/v0/item/{news_id}.json'
            response = requests.get(url)
            response.raise_for_status()
            news_detail = response.json()
            self.logger.log_info(f"新闻 ID {news_id} 的详情已获取。")
            return news_detail
        except requests.RequestException as e:
            self.logger.log_exception()
            return {}
        
    def fetch_latest_urls(self) -> List[str]:
        """获取最新的新闻链接列表。

        Returns:
            List[str]: 新闻链接列表。
        """
        try:
            response = requests.get('https://hacker-news.firebaseio.com/v0/newstories.json')
            response.raise_for_status()
            news_ids = response.json()[:self.top_n]
            urls = []
            for news_id in news_ids:
                url = self.fetch_news_url(news_id)
                if url:
                    urls.append(url)
            self.logger.log_info(f"获取到 {len(urls)} 个新闻链接。")
            return urls
        except requests.RequestException as e:
            self.logger.log_exception()
            return []

    def fetch_news_url(self, news_id: int) -> str:
        """获取单条新闻的链接。

        Args:
            news_id (int): 新闻的 ID。

        Returns:
            str: 新闻的链接。
        """
        try:
            url = f'https://hacker-news.firebaseio.com/v0/item/{news_id}.json'
            response = requests.get(url)
            response.raise_for_status()
            news_detail = response.json()
            news_url = news_detail.get('url', '')
            return news_url
        except requests.RequestException as e:
            self.logger.log_exception()
            return ""
        
if __name__ == "__main__":
    fetcher = HackerNewsFetcher()
    news_list = fetcher.fetch_latest_news()
    from pprint import pprint
    pprint(news_list)
    news_urls = fetcher.fetch_latest_urls()
    pprint(news_urls)