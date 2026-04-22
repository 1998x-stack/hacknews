# Hacker News 每日摘要

> 自动抓取 Hacker News 热门文章，提取正文内容，生成 Markdown 邮件摘要并定时发送。

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![CI](https://github.com/1998x-stack/hacknews/actions/workflows/news_email.yaml/badge.svg)](https://github.com/1998x-stack/hacknews/actions/workflows/news_email.yaml)

---

## 功能特性

- **自动抓取** — 通过 Hacker News Firebase API 获取每日热门文章
- **智能提取** — 三级降级策略（newspaper3k → readability → GNE），支持 PDF 解析
- **邮件投递** — Markdown + HTML 双格式，SMTP 加密发送
- **定时执行** — GitHub Actions 每日自动运行，无需服务器
- **类型安全** — 全量类型注解，mypy 严格检查
- **测试覆盖** — 27 个单元测试，覆盖配置、抓取、提取、格式化、发送全流程

## 快速开始

### 环境要求

- Python 3.10+

### 安装

```bash
# 克隆仓库
git clone https://github.com/1998x-stack/hacknews.git
cd hacknews

# 安装依赖
pip install -e .
```

### 配置

设置以下环境变量：

| 变量 | 必填 | 默认值 | 说明 |
|---|---|---|---|
| `EMAIL_ADDRESS` | ✅ | — | 发件人邮箱地址 |
| `EMAIL_PASSWORD` | ✅ | — | 发件人密码或应用专用密码 |
| `SMTP_SERVER` | 否 | `smtp.gmail.com` | SMTP 服务器地址 |
| `SMTP_PORT` | 否 | `587` | SMTP 端口 |
| `TO_EMAILS` | 否 | 空 | 收件人列表，逗号分隔 |
| `PROXY` | 否 | 无 | HTTP/HTTPS 代理地址 |
| `HN_TOP_N` | 否 | `10` | 每次抓取的文章数量 |
| `REQUEST_TIMEOUT` | 否 | `3` | 请求超时时间（秒） |

```bash
export EMAIL_ADDRESS="your_email@gmail.com"
export EMAIL_PASSWORD="your_app_password"
export TO_EMAILS="recipient@example.com"
```

### 运行

```bash
python -m hacknews
```

## 开发

### 安装开发依赖

```bash
pip install -e '.[dev]'
```

### 测试

```bash
pytest tests/ -v
```

### 代码检查

```bash
# Lint
ruff check src/hacknews tests

# 类型检查
mypy src/hacknews
```

### 一键验证

```bash
ruff check src/hacknews tests && mypy src/hacknews && pytest tests/ -v
```

## 架构

```
src/hacknews/
├── __main__.py       # 入口 (python -m hacknews)
├── config.py         # 环境变量配置（带校验）
├── fetcher.py        # HN Firebase API 客户端
├── extractor.py      # 文章内容提取（三级降级）
├── formatter.py      # Markdown 格式化
└── sender.py         # SMTP 邮件发送
```

### 内容提取流程

```
URL 输入
  │
  ├── PDF 链接 → PyMuPDF 提取文本
  │
  └── HTML 链接
       │
       ├── newspaper3k（主方案）
       ├── readability（降级 1）
       └── GNE（降级 2）
            │
            └── 全部失败 → 抛出 ExtractionError
```

## CI/CD

项目通过 GitHub Actions 实现自动化：

1. **测试阶段** — 运行 lint、类型检查、单元测试
2. **发送阶段** — 测试通过后执行邮件发送任务

触发条件：
- 每日 21:40 CST（UTC `40 13 * * *`）
- 手动触发（`workflow_dispatch`）

### 配置 GitHub Secrets

在仓库 Settings → Secrets and variables → Actions 中添加：

- `EMAIL_ADDRESS`
- `EMAIL_PASSWORD`
- `SMTP_SERVER`（可选）
- `SMTP_PORT`（可选）
- `TO_EMAILS`
- `PROXY`（可选）

## 依赖

| 包 | 用途 |
|---|---|
| `requests` | HTTP 请求 |
| `newspaper3k` | 文章内容提取（主方案） |
| `readability-lxml` | 文章内容提取（降级 1） |
| `gne` | 文章内容提取（降级 2） |
| `PyMuPDF` | PDF 文本提取 |
| `markdown` | Markdown → HTML 转换 |
| `certifi` | SSL 证书验证 |

开发依赖：`pytest`、`mypy`、`ruff`

## 许可证

MIT
