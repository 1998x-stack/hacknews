# src/main.py
import sys,os
sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/' + '..'))

import os, time, jieba
from util.email_sender import EmailSender
from util.hacker_news_fetcher import HackerNewsFetcher
from util.markdown_formatter import MarkdownFormatter

from util.log_utils import logger
from src.url_extractor import ContentExtractor

jieba.cut("初始化")

from config.config import SMTP_PORT, SMTP_SERVER, EMAIL_ADDRESS, EMAIL_PASSWORD, TO_EMAILS


content_extractor = ContentExtractor()

def main():
    email_sender = EmailSender(SMTP_SERVER, SMTP_PORT, EMAIL_ADDRESS, EMAIL_PASSWORD)
    # 初始化 HackerNewsFetcher
    fetcher = HackerNewsFetcher(top_n=10)
    news_list = fetcher.fetch_latest_news()
    if news_list:
        for news in news_list:
            url = news.get('url', '')
            if url:
                text = content_extractor.extract_content(url, 'en')
                news['text'] = news.get('text', '') + '\n\n' + text
                logger.log_info(f"新闻内容已提取: {url}")
        body = MarkdownFormatter.format_news(news_list)
        subject = f" 《Hacker News 最新新闻》 - ({time.strftime('%Y-%m-%d %H:%M')})"
        email_sender.send_email(subject, body, TO_EMAILS)
        logger.log_info("邮件已发送。")
    
if __name__ == "__main__":
    main()