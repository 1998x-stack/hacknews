from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime

from hacknews import storage
from hacknews.config import Config
from hacknews.extractor import ContentExtractor, ExtractionError
from hacknews.fetcher import HackerNewsFetcher
from hacknews.formatter import MarkdownFormatter
from hacknews.sender import EmailSender


def cmd_scrape(args: argparse.Namespace) -> None:
    config = Config.from_env(require_email=False)
    fetcher = HackerNewsFetcher(top_n=config.top_n, timeout=config.timeout)
    news_items = fetcher.fetch_latest_news()

    if not news_items:
        logging.warning("No stories with URLs found.")
        return

    date = datetime.now().strftime("%Y-%m-%d")
    extractor = ContentExtractor(
        timeout=config.timeout, proxy=config.proxy, save_html=True, date=date
    )
    stories = []
    for item in news_items:
        if not item.url:
            continue
        try:
            text = extractor.extract(item.url, lang="en", story_id=item.id)
            item.text = text
        except ExtractionError as e:
            logging.warning("Skipping %s: %s", item.url, e)

        story = {"id": item.id, "title": item.title, "url": item.url, "text": item.text}
        stories.append(story)

    if not stories:
        logging.warning("No stories extracted.")
        return

    storage.save_metadata(stories)
    body = MarkdownFormatter.format(stories)
    storage.save_markdown(body)
    logging.info("Scrape complete: %d stories saved.", len(stories))


def cmd_send(args: argparse.Namespace) -> None:
    config = Config.from_env(require_email=True)
    date = args.date if hasattr(args, "date") and args.date else None
    body = storage.load_markdown(date)

    subject = "Hacker News Digest"
    sender = EmailSender(
        config.smtp_server,
        config.smtp_port,
        config.email_address,
        config.email_password,
    )
    sender.send(subject, body, config.to_emails)
    logging.info("Email sent.")


def main() -> None:
    parser = argparse.ArgumentParser(prog="hacknews")
    sub = parser.add_subparsers(dest="command")

    scrape_p = sub.add_parser("scrape", help="Fetch HN stories, extract content, save locally")
    scrape_p.set_defaults(func=cmd_scrape)

    send_p = sub.add_parser("send", help="Send saved Markdown digest via email")
    send_p.add_argument(
        "--date", default=None, help="Digest date (YYYY-MM-DD, default: today)"
    )
    send_p.set_defaults(func=cmd_send)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )
    main()
