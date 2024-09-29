# src/markdown_formatter.py
import sys,os
sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/' + '..'))

from typing import List, Dict
from datetime import datetime

from util.log_utils import logger

class MarkdownFormatter:
    """用于将新闻数据格式化为 Markdown 格式的类。"""

    @staticmethod
    def format_news(news_list: List[Dict]) -> str:
        """将新闻列表格式化为 Markdown 字符串。

        Args:
            news_list: 包含新闻详情的列表。

        Returns:
            str: 格式化后的 Markdown 字符串。
        """
        markdown_lines = [
            "# 《Hacker News 最新新闻》 📰\n",  # 增加表情符号
            f"> 发布日期：{datetime.now().strftime('%Y-%m-%d')} 📅\n",
            "---\n"
        ]
        for news in news_list:
            title = news.get('title', '无标题')
            url = news.get('url', f"https://news.ycombinator.com/item?id={news.get('id')}")
            markdown_lines.append(f"### [{title}]({url})\n")
            markdown_lines.append('')
            markdown_lines.append("\n\n---\n\n")
            
        markdown_content = '\n'.join(markdown_lines)
        logger.log_info("新闻已格式化为 Markdown。")
        return markdown_content