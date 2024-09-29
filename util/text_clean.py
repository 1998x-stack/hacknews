import sys,os
sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/' + '..'))

import re
from typing import Optional
from util.rule_patterns \
    import (
            HTML_TAG_PATTERN,
            EXCEPTION_PATTERN, 
            FULL_ANGLE_ALPHABET, 
            HALF_ANGLE_ALPHABET,
            EMAIL_PATTERN,
            REDUNDANT_PATTERN,
            IP_ADDRESS_PATTERN
        )

class TextCleaner:
    """文本清理类，用于移除文本中的HTML标签和URL。

    此类提供了用于清理文本的函数，这些函数通过正则表达式来匹配和删除
    特定的模式，如HTML标签和URL。它还可以轻松扩展以执行其他清理任务。

    Attributes:
        html_tag_pattern (re.Pattern): 匹配HTML标签的正则表达式模式。
        url_pattern (re.Pattern): 匹配URL的正则表达式模式。
    """

    def __init__(self) -> None:
        """初始化TextCleaner类，定义用于匹配HTML标签和URL的正则表达式模式。"""
        self.html_tag_pattern: re.Pattern = re.compile(HTML_TAG_PATTERN)
        # self.url_pattern: re.Pattern = re.compile(URL_PATTERN)
        self.url_pattern: re.Pattern = re.compile(
            r'https?://(?:www\.)?[-\w@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-\w@:%_\+.~#?&//=]*)'
        )
        self.exception_pattern: re.Pattern = re.compile(EXCEPTION_PATTERN)
        self.email_pattern: re.Pattern = re.compile(EMAIL_PATTERN)
        self.redundant_pattern = self.generate_redundant_pattern()
        self.full_angle_pattern = str.maketrans(FULL_ANGLE_ALPHABET, HALF_ANGLE_ALPHABET)
        self.ip_address_pattern = re.compile(IP_ADDRESS_PATTERN)
        
    def generate_redundant_pattern(self, redundant_chars=None):
        pattern_list = list()
        if redundant_chars is None:
            redundant_chars = REDUNDANT_PATTERN

        for char in redundant_chars:
            pattern_tmp = '(?<={char}){char}+'.format(
                char=re.escape(char))
            pattern_list.append(pattern_tmp)
        
        redundant_pattern = '|'.join(pattern_list)
        redundant_pattern = re.compile(redundant_pattern)
        return redundant_pattern

    def remove_html_tags(self, text: str) -> str:
        """移除文本中的HTML标签。

        Args:
            text (str): 包含HTML标签的文本。

        Returns:
            str: 移除HTML标签后的文本。
        """
        cleaned_text = self.html_tag_pattern.sub('', text)
        print(f"HTML标签已移除: {cleaned_text}")  # 打印移除标签后的文本
        return cleaned_text

    def remove_urls(self, text: str) -> str:
        """移除文本中的URL。

        Args:
            text (str): 包含URL的文本。

        Returns:
            str: 移除URL后的文本。
        """
        cleaned_text = self.url_pattern.sub('', text)
        print(f"URL已移除: {cleaned_text}")  # 打印移除URL后的文本
        return cleaned_text

    def remove_exception_char(self, text: str) -> str:
        """移除文本中的异常字符。

        Args:
            text (str): 包含异常字符的文本。

        Returns:
            str: 移除异常字符后的文本。
        """
        cleaned_text = self.exception_pattern.sub('', text)
        print(f"异常字符已移除: {cleaned_text}")
        return cleaned_text

    def convert_full2half(self, text):
        """ 将全角字符转换为半角字符
        其中分为空格字符和非空格字符
        """
        return text.translate(self.full_angle_pattern)
    
    def remove_email(self, text: str) -> str:
        """移除文本中的邮箱地址。

        Args:
            text (str): 包含邮箱地址的文本。

        Returns:
            str: 移除邮箱地址后的文本。
        """
        cleaned_text = self.email_pattern.sub('', text)
        print(f"邮箱地址已移除: {cleaned_text}")
        return cleaned_text
    
    def remove_redundant_char(self, text):
        """去除冗余字符

        Args:
            text(str): 待处理文本
            redundant_chars(str|list): 自定义待去除的冗余字符串 或 list，
                如 ”哈嗯~“，或 ['哈', '嗯', '\u3000']，若不指定则采用默认的冗余字符串。

        Returns:
            删除冗余字符后的文本

        """
        return self.redundant_pattern.sub('', text)
    
    def remove_ip_address(self, text):
        """ 删除文本中的 ip 地址

        Args:
            text(str): 字符串文本

        Returns:
            str: 删除 ip 地址后的文本

        """
            
        text = ''.join(['#', text, '#'])
        return self.ip_address_pattern.sub('', text)[1:-1]
    
    def clean_text(self, text: Optional[str]) -> str:
        """清理文本，移除HTML标签和URL。

        Args:
            text (Optional[str]): 需要清理的文本。如果为None，则返回空字符串。

        Returns:
            str: 完成清理后的文本。
        """
        if not text:
            print("输入文本为空或无效。")  # 打印无效输入提示
            return ''

        # 依次调用移除HTML标签和URL的函数
        cleaned_text = self.remove_html_tags(text)
        cleaned_text = self.remove_urls(cleaned_text)
        cleaned_text = self.remove_exception_char(cleaned_text)
        cleaned_text = self.remove_email(cleaned_text)
        cleaned_text = self.convert_full2half(cleaned_text)
        cleaned_text = self.remove_redundant_char(cleaned_text)
        cleaned_text = self.remove_ip_address(cleaned_text)
        
        print(f"清理后的文本: {cleaned_text}")  # 打印清理后的最终文本
        return cleaned_text


# 验证步骤：测试TextCleaner类
if __name__ == "__main__":
    cleaner = TextCleaner()
    sample_text = (
        "<html><head><title>Example</title></head><body>"
        "<p>Visit our website at <a href='https://example.com'>https://example.com</a></p>"
        "</body></html>"
    )
    # 清理样本文本
    cleaned_text = cleaner.clean_text(sample_text)
    print(f"最终文本: {cleaned_text}")  # 打印最终文本