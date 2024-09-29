# src/news_email_scheduler.py
import sys,os
sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/' + '..'))

import schedule
import time
from util.markdown_formatter import MarkdownFormatter

from util.log_utils import logger

from config.config import TO_EMAILS

class NewsEmailScheduler:
    """新闻邮件调度器，用于定时发送新闻邮件。

    Attributes:
        email_sender: EmailSender 实例，用于发送邮件。
        fetcher: HackerNewsFetcher 实例，用于获取新闻。
        interval_minutes: 发送邮件的时间间隔（分钟）。
    """

    def __init__(self, email_sender, fetcher, interval_minutes: int = 60 * 4):
        """初始化 NewsEmailScheduler 实例。

        Args:
            email_sender: EmailSender 实例。
            fetcher: HackerNewsFetcher 实例。
        """
        self.email_sender = email_sender
        self.fetcher = fetcher
        self.interval_minutes = interval_minutes
        logger.log_info("NewsEmailScheduler 实例已创建。")

    def send_news_email(self):
        """获取新闻并发送邮件。"""
        news_list = self.fetcher.fetch_latest_news()
        if news_list:
            body = MarkdownFormatter.format_news(news_list)
            subject = f" 《Hacker News 最新新闻》 - ({time.strftime('%Y-%m-%d %H:%M')})"
            self.email_sender.send_email(subject, body, TO_EMAILS)
        else:
            logger.log_info("未获取到新闻，邮件未发送。")

    def start(self):
        """开始定时任务。"""
        def job_wrapper():
            logger.log_info("开始执行定时任务...")
            self.send_news_email()
            logger.log_info("定时任务执行完成。")
            
        schedule.every(self.interval_minutes).minutes.do(job_wrapper)
        logger.log_info(f"开始新闻邮件调度器，每 {self.interval_minutes} 分钟发送一次。")
        while True:
            schedule.run_pending()
            time.sleep(1)