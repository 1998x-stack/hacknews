import sys,os
sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/' + '..'))

import certifi
import requests, fitz
from io import BytesIO
from pprint import pprint
from fake_headers import Headers
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

from gne import GeneralNewsExtractor
from newspaper import Article
from newspaper.configuration import Configuration
from readability import Document

from config.config import PROXIES, TIMEOUT

from util.utils import retry
from util.text_clean import TextCleaner

from util.log_utils import logger

FAIL_ENCODING = 'ISO-8859-1'

class ContentExtractor:
    def __init__(self) -> None:
        self.header_generator = Headers(
            headers=False  # don`t generate misc headers
        )
        self.newspaper_config = Configuration()
        self.request_args = {
            'proxies': PROXIES,
            'timeout': TIMEOUT,
            'verify': certifi.where(),
        }
        self.scrape_count = 0
        self.logger = logger
        self.text_cleaner = TextCleaner()
        self.quality_dict = {
            "newspaper3k": 0,
            "readability": 0,
            "gne": 0,
            "failed": 0,
        }
    
    def fetch_html(self, url: str) -> str:
        """
        从给定的 URL 中获取 HTML 内容。

        Args:
            url (str): 目标 URL。
            request_args (Optional[Dict[str, Any]]): 请求的附加参数。

        Returns:
            str: 获取到的 HTML 内容。
        """
        if not url:
            return ""

        headers = self.header_generator.generate()
        headers["Host"] = urlparse(url).netloc
        cookies=None
        if 'baidu.com' in headers["Host"]:
            cookies = {'BA_HECTOR': '2g812k2g2k802k212la0812h1inl9r41q'}

        try:
            response = requests.get(url, headers=headers, cookies=cookies, **self.request_args)
            response.raise_for_status()  # 检查响应状态码是否为 200
            html = self._get_html_from_response(response)
            self.logger.log_info(f"【ContentExtractor】Successfully fetched HTML from {url}")
            return html
        except requests.RequestException as e:
            if self.logger:
                self.logger.log_exception()
            else:
                pprint(f"【ContentExtractor】Failed to fetch HTML from {url}: {e}")
            return ""

    @staticmethod
    def _get_html_from_response(response):
        if response.encoding != FAIL_ENCODING:
            # return response as a unicode string
            html = response.text
        else:
            html = response.content
            if 'charset' not in response.headers.get('content-type'):
                encodings = requests.utils.get_encodings_from_content(response.text)
                if len(encodings) > 0:
                    response.encoding = encodings[0]
                    html = response.text

        return html or ''
    
    @retry(retries=2, delay=0.2)
    def extract_content(self, url, lang='zh'):
        host = urlparse(url).netloc
        content = ''
        if url.endswith('.pdf'):
            content = self.extract_pdf_content(url)
            if content:
                self.logger.log_info(f"【PyMuPDF】Successfully extracted content from {url}")
                self.quality_dict['PDF'] = self.quality_dict.get('PDF', 0) + 1
            else:
                self.logger.log_info(f"【PyMuPDF】Failed to extract content from {url}")
                return ""
        else:
            try:
                self.newspaper_config.headers = self.header_generator.generate()
                self.newspaper_config.set_language(lang)
                article = Article(url, config=self.newspaper_config)
                article.download()
                article.parse()
                content = article.text
                assert content, f"Empty content from {url}"
                self.logger.log_info(f"【newspaper3k】Successfully extracted content from {url}")
                self.quality_dict['newspaper3k'] = self.quality_dict.get('newspaper3k', 0) + 1
            except Exception as e:
                if self.logger:
                    self.logger.log_exception()
                else:
                    pprint(f"【newspaper3k】Failed to extract content from {url}: {e}")
                html = self.fetch_html(url)
                if not html:
                    if self.logger:
                        self.logger.log_info(f"【Failed Host】{host}")
                    else:
                        pprint(f"【Failed Host】{host}")
                    return ""
                content = self.extract_content_by_readability(html)
                if not content:
                    content = self.extract_content_by_gne(html)
                    if not content:
                        if self.logger:
                            self.logger.log_info(f"【Failed Host】{host}")
                        else:
                            pprint(f"【Failed Host】{host}")
                        return ""
                    else:
                        self.logger.log_info(f"【gne】Successfully extracted content from {url}")
                        self.quality_dict['gne'] = self.quality_dict.get('gne', 0) + 1
                else:
                    self.logger.log_info(f"【readability】Successfully extracted content from {url}")
                    self.quality_dict['readability'] = self.quality_dict.get('readability', 0) + 1
        
        # return self.text_cleaner.clean_text(content)
        return content
            
    def extract_content_by_readability(self, html):
        try:
            doc = Document(html)
            content = doc.summary()
            if content:
                self.logger.log_info(f"【readability】Successfully extracted content from {html[:100]}")
                return content
            else:
                return ""
        except Exception as e:
            if self.logger:
                self.logger.log_exception()
            else:
                pprint(f"【readability】Failed to extract content from {html[:100]}: {e}")
            return ""
    
    def extract_content_by_gne(self, html):
        try:
            extractor = GeneralNewsExtractor()
            result = extractor.extract(html, normalize=True)
            content = result.get('content', '')
            if content:
                self.logger.log_info(f"【gne】Successfully extracted content from {html[:100]}")
                return content
            else:
                return ""
        except Exception as e:
            if self.logger:
                self.logger.log_exception()
            else:
                pprint(f"【gne】Failed to extract content from {html[:100]}: {e}")
            return ""
        
    def extract_pdf_content(self, pdf_url):
        try:
            # 从 URL 获取 PDF 文件流
            response = requests.get(pdf_url, stream=True)
            response.raise_for_status()  # 确保请求成功
            # 使用 BytesIO 从流中读取 PDF 文件
            pdf_file = BytesIO(response.content)
            # 使用 PyMuPDF 打开 PDF 文件
            pdf_document = fitz.open(stream=pdf_file, filetype="pdf")
            # 从每一页提取文本
            text = ""
            for page_num in range(len(pdf_document)):
                page = pdf_document.load_page(page_num)
                text += page.get_text()
            
            if text:
                self.logger.log_info(f"【PyMuPDF】Successfully extracted content from {pdf_url}")
            else:
                return ""
                
        except Exception as e:
            if self.logger:
                self.logger.log_exception()
            else:
                pprint(f"【PyMuPDF】Failed to extract content from {pdf_url}: {e}")
            return ""

        return text
    
    def batch_extract_content(self, urls, langs, max_workers=5):
        self.logger.log_info(f"【ContentExtractor】Start batch extracting content from {len(urls)} URLs")
        if not urls:
            return []
        results = [None] * len(urls)  # Initialize a list to hold results in order
        with ThreadPoolExecutor(max_workers=min(max_workers, len(urls))) as executor:
            tasks = {executor.submit(self.extract_content, url, lang): i for i, (url, lang) in enumerate(zip(urls, langs))}
            
            for future in as_completed(tasks):
                index = tasks[future]
                results[index] = future.result()
        
        return results


if __name__ == "__main__":
    import pandas as pd
    df = pd.read_csv("data/test.csv", sep="	")
    urls = df["url"].tolist()
    langs = ['zh'] * len(urls)
    config = CONFIG()
    logger = Log()
    extractor = ContentExtractor(config=config, logger=logger)
    url = 'https://blog.csdn.net/qq_38670588/article/details/108186884'
    result = extractor.extract_content(url)
    pprint(result)