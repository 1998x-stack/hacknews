# src/email_sender.py
import sys,os
sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/' + '..'))

import smtplib, base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from typing import List

from util.log_utils import logger


# Monkey-patch smtplib.encode_base64 to return str
def encode_base64(bytestr, eol='\n'):
    """Encode bytestr in base64 and return as str."""
    # Ensure the encoded bytes are decoded into a str
    enc = base64.b64encode(bytestr).decode('ascii')
    if eol:
        enc += eol
    return enc

smtplib.encode_base64 = encode_base64

class EmailSender:
    """用于发送电子邮件的类。

    Attributes:
        smtp_server: SMTP 服务器地址。
        smtp_port: SMTP 服务器端口。
        username: 发件人邮箱用户名。
        password: 发件人邮箱密码或应用专用密码。
    """

    def __init__(self, smtp_server: str, smtp_port: int, username: str, password: str):
        """初始化 EmailSender 实例。

        Args:
            smtp_server: SMTP 服务器地址。
            smtp_port: SMTP 服务器端口。
            username: 发件人邮箱用户名。
            password: 发件人邮箱密码或应用专用密码。
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        logger.log_info("EmailSender 实例已创建。")

    def send_email(self, subject: str, body: str, to_emails: List[str]) -> None:
        """发送电子邮件。

        Args:
            subject: 邮件主题。
            body: 邮件正文内容（支持 Markdown）。
            to_emails: 收件人邮箱列表。

        Raises:
            Exception: 发送邮件失败时抛出异常。
        """
        # 创建邮件对象
        message = MIMEMultipart('alternative')
        message['From'] = self.username
        message['To'] = ", ".join(to_emails)
        message['Subject'] = subject

        # 将 Markdown 转换为 HTML
        try:
            import markdown
            html_body = markdown.markdown(body)
        except ImportError:
            html_body = body
            logger.log_info("未安装 markdown 库，邮件将不支持 HTML 格式。")

        # 添加邮件正文
        message.attach(MIMEText(body, 'plain', 'utf-8'))
        message.attach(MIMEText(html_body, 'html', 'utf-8'))
        logger.log_info("邮件内容已创建。")

        # 发送邮件
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # 开启 TLS 加密
                logger.log_info(f"已连接到 SMTP 服务器。 username: {self.username}")
                server.login(self.username, self.password)  # 登录邮箱
                server.sendmail(self.username, to_emails, message.as_string())
                logger.log_info(f"邮件已发送至: {to_emails}")
        except Exception as e:
            logger.log_exception()