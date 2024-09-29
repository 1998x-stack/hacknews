# src/content_extractor.py
import sys,os
sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/' + '..'))

import requests
import logging
import certifi
import jieba
import fitz  # PyMuPDF
from io import BytesIO
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional

from fake_headers import Headers
from gne import GeneralNewsExtractor
from newspaper import Article
from newspaper.configuration import Configuration
from readability import Document

# 初始化 jieba，防止首次调用时卡顿
_ = jieba.cut("初始化")

FAIL_ENCODING = 'ISO-8859-1'


class ContentExtractor:
    """内容提取器类，用于从给定的 URL 中提取文本内容。

    Attributes:
        timeout (int): 请求超时时间。
        logger (logging.Logger): 日志记录器。
        newspaper_config (Configuration): newspaper3k 的配置对象。
        request_args (Dict): 请求参数，如代理、超时等。
        header_generator (Headers): 用于生成随机请求头的对象。
    """

    def __init__(self, timeout: int = 10, logger: Optional[logging.Logger] = None) -> None:
        """初始化 ContentExtractor 实例。

        Args:
            timeout (int, optional): 请求超时时间。默认为 10。
            logger (logging.Logger, optional): 日志记录器。默认为 None。
        """
        self.timeout = timeout
        self.logger = logger or logging.getLogger(__name__)
        self.header_generator = Headers(headers=False)

        # 配置代理，如果不需要代理，可以将 proxies 设置为 None
        self.proxies = None
        # 示例代理配置
        # self.proxies = {
        #     'http': 'http://username:password@proxyserver:port',
        #     'https': 'http://username:password@proxyserver:port',
        # }

        self.newspaper_config = Configuration()
        self.newspaper_config.proxies = self.proxies

        self.request_args = {
            'proxies': self.proxies,
            'timeout': self.timeout,
            'verify': certifi.where(),
        }

        self.text_cleaner = TextCleaner()
        self.quality_dict = {
            "newspaper3k": 0,
            "readability": 0,
            "gne": 0,
            "PDF": 0,
            "failed": 0,
        }

    def fetch_html(self, url: str) -> str:
        """从给定的 URL 中获取 HTML 内容。

        Args:
            url (str): 目标 URL。

        Returns:
            str: 获取到的 HTML 内容。
        """
        if not url:
            return ""

        headers = self.header_generator.generate()
        headers["Host"] = urlparse(url).netloc
        cookies = None

        try:
            response = requests.get(url, headers=headers, cookies=cookies, **self.request_args)
            response.raise_for_status()
            html = self._get_html_from_response(response)
            self.logger.info(f"成功获取 {url} 的 HTML 内容。")
            return html
        except requests.RequestException as e:
            self.logger.error(f"获取 {url} 的 HTML 内容失败：{e}")
            return ""

    @staticmethod
    def _get_html_from_response(response: requests.Response) -> str:
        """从响应中提取 HTML 内容。

        Args:
            response (requests.Response): HTTP 响应对象。

        Returns:
            str: HTML 内容。
        """
        if response.encoding != FAIL_ENCODING:
            html = response.text
        else:
            html = response.content
            if 'charset' not in response.headers.get('content-type', ''):
                encodings = requests.utils.get_encodings_from_content(response.text)
                if encodings:
                    response.encoding = encodings[0]
                    html = response.text
        return html or ''

    def extract_content(self, url: str, lang: str = 'en') -> str:
        """提取给定 URL 的内容。

        Args:
            url (str): 目标 URL。
            lang (str, optional): 语言代码。默认为 'en'。

        Returns:
            str: 提取的文本内容。
        """
        host = urlparse(url).netloc
        content = ''

        if url.endswith('.pdf'):
            content = self.extract_pdf_content(url)
            if content:
                self.logger.info(f"成功从 {url} 提取 PDF 内容。")
                self.quality_dict['PDF'] += 1
            else:
                self.logger.warning(f"从 {url} 提取 PDF 内容失败。")
                return ""
        else:
            try:
                self.newspaper_config.headers = self.header_generator.generate()
                self.newspaper_config.set_language(lang)
                article = Article(url, config=self.newspaper_config)
                article.download()
                article.parse()
                content = article.text
                assert content, f"从 {url} 提取到空内容。"
                self.logger.info(f"成功从 {url} 提取内容（newspaper3k）。")
                self.quality_dict['newspaper3k'] += 1
            except Exception as e:
                self.logger.error(f"使用 newspaper3k 提取 {url} 内容失败：{e}")
                html = self.fetch_html(url)
                if not html:
                    self.logger.warning(f"无法获取 {url} 的 HTML 内容。")
                    return ""
                content = self.extract_content_by_readability(html)
                if not content:
                    content = self.extract_content_by_gne(html)
                    if not content:
                        self.logger.warning(f"所有方法均无法提取 {url} 的内容。")
                        self.quality_dict['failed'] += 1
                        return ""
                    else:
                        self.logger.info(f"成功从 {url} 提取内容（gne）。")
                        self.quality_dict['gne'] += 1
                else:
                    self.logger.info(f"成功从 {url} 提取内容（readability）。")
                    self.quality_dict['readability'] += 1

        return self.text_cleaner.clean_text(content)

    def extract_content_by_readability(self, html: str) -> str:
        """使用 readability 提取 HTML 内容。

        Args:
            html (str): HTML 内容。

        Returns:
            str: 提取的文本内容。
        """
        try:
            doc = Document(html)
            content = doc.summary()
            return content
        except Exception as e:
            self.logger.error(f"使用 readability 提取内容失败：{e}")
            return ""

    def extract_content_by_gne(self, html: str) -> str:
        """使用 gne 提取 HTML 内容。

        Args:
            html (str): HTML 内容。

        Returns:
            str: 提取的文本内容。
        """
        try:
            extractor = GeneralNewsExtractor()
            result = extractor.extract(html, normalize=True)
            content = result.get('content', '')
            return content
        except Exception as e:
            self.logger.error(f"使用 gne 提取内容失败：{e}")
            return ""

    def extract_pdf_content(self, pdf_url: str) -> str:
        """从 PDF 文件中提取文本内容。

        Args:
            pdf_url (str): PDF 文件的 URL。

        Returns:
            str: 提取的文本内容。
        """
        try:
            response = requests.get(pdf_url, stream=True)
            response.raise_for_status()
            pdf_file = BytesIO(response.content)
            pdf_document = fitz.open(stream=pdf_file, filetype="pdf")
            text = ""
            for page_num in range(len(pdf_document)):
                page = pdf_document.load_page(page_num)
                text += page.get_text()
            return text
        except Exception as e:
            self.logger.error(f"提取 PDF 内容失败：{e}")
            return ""

    def batch_extract_content(self, urls: List[str], langs: List[str], max_workers: int = 5) -> List[str]:
        """批量提取多个 URL 的内容。

        Args:
            urls (List[str]): URL 列表。
            langs (List[str]): 语言列表，与 URL 对应。
            max_workers (int, optional): 最大线程数。默认为 5。

        Returns:
            List[str]: 提取的内容列表。
        """
        self.logger.info(f"开始批量提取 {len(urls)} 个 URL 的内容。")
        if not urls:
            return []
        results = [None] * len(urls)
        with ThreadPoolExecutor(max_workers=min(max_workers, len(urls))) as executor:
            tasks = {executor.submit(self.extract_content, url, lang): i for i, (url, lang) in enumerate(zip(urls, langs))}
            for future in as_completed(tasks):
                index = tasks[future]
                try:
                    results[index] = future.result()
                except Exception as e:
                    self.logger.error(f"提取 {urls[index]} 内容时出错：{e}")
                    results[index] = ""
        return results


class TextCleaner:
    """文本清理器类，用于清理提取的文本内容。"""

    @staticmethod
    def clean_text(text: str) -> str:
        """清理文本内容，去除多余的空白字符。

        Args:
            text (str): 原始文本。

        Returns:
            str: 清理后的文本。
        """
        return ' '.join(text.split())