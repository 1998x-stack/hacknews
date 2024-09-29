import sys,os
sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/' + '..'))

# 从环境变量中获取配置
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
EMAIL_ADDRESS = os.environ['EMAIL_ADDRESS'] if 'EMAIL_ADDRESS' in os.environ else ''
EMAIL_PASSWORD = os.environ['EMAIL_PASSWORD'] if 'EMAIL_PASSWORD' in os.environ else ''
TO_EMAILS = os.environ['TO_EMAILS'] if 'TO_EMAILS' in os.environ else ''
TO_EMAILS = TO_EMAILS.split(',')