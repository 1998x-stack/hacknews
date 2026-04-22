"""Format news items as Markdown."""

from __future__ import annotations

from datetime import datetime


class MarkdownFormatter:
    @staticmethod
    def format(news: list[dict]) -> str:
        lines = [
            "# Hacker News Digest",
            f"> {datetime.now().strftime('%Y-%m-%d')}",
            "---",
        ]
        for item in news:
            title = item.get("title", "Untitled")
            url = item.get("url") or f"https://news.ycombinator.com/item?id={item.get('id')}"
            lines.append(f"## [{title}]({url})")

            text = item.get("text", "")
            if text:
                for paragraph in text.split("\n\n"):
                    if paragraph.strip():
                        lines.append(
                            f"> {paragraph.strip().replace(chr(10), chr(10) + '> ')}"
                        )

            lines.append("---")

        return "\n\n".join(lines)
