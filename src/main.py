# src/main.py
import sys,os
sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/' + '..'))

import os
from util.email_sender import EmailSender
from util.hacker_news_fetcher import HackerNewsFetcher
from util.news_email_scheduler import NewsEmailScheduler

from config.config import SMTP_PORT, SMTP_SERVER, EMAIL_ADDRESS, EMAIL_PASSWORD

if __name__ == "__main__":
    email_sender = EmailSender(SMTP_SERVER, SMTP_PORT, EMAIL_ADDRESS, EMAIL_PASSWORD)
    # 初始化 HackerNewsFetcher
    fetcher = HackerNewsFetcher(top_n=10)
    # 初始化并启动新闻邮件调度器
    scheduler = NewsEmailScheduler(email_sender, fetcher, interval_minutes=60 * 4)
    scheduler.start()