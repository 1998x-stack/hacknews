"""Build an HTML + plaintext digest message from story metadata."""
from __future__ import annotations

import html
from dataclasses import dataclass

from hacknews.models import DigestJob, Story

HN_ITEM = "https://news.ycombinator.com/item?id={id}"


@dataclass
class DigestMessage:
    subject: str
    html: str
    plain: str


def _plain_entry(story: Story, include_text: bool) -> str:
    lines = [story.title or f"Story {story.id}"]
    if story.url:
        lines.append(story.url)
    meta = []
    meta.append(f"{story.score} pts")
    meta.append(f"{story.comments} comments")
    if story.domain:
        meta.append(story.domain)
    lines.append(" · ".join(meta))
    lines.append(f"HN: {HN_ITEM.format(id=story.id)}")
    if include_text and story.text:
        lines.append(story.text[:500])
    return "\n".join(lines)


def _html_entry(story: Story, include_text: bool) -> str:
    title = html.escape(story.title or f"Story {story.id}")
    link = html.escape(story.url or HN_ITEM.format(id=story.id))
    meta = " · ".join(
        part
        for part in [
            f"{story.score} pts" if story.score else "",
            f"{story.comments} comments" if story.comments else "",
            html.escape(story.domain or "") or "",
        ]
        if part
    )
    out = [f"<li><a href='{link}'>{title}</a>"]
    if meta:
        out.append(f" <span>({meta})</span>")
    out.append(f"<br/><a href='{HN_ITEM.format(id=story.id)}'>HN discussion</a>")
    if include_text and story.text:
        out.append(f"<blockquote>{html.escape(story.text[:500])}</blockquote>")
    out.append("</li>")
    return "".join(out)


def build(
    job: DigestJob, stories: list[Story], include_self_text: bool | None = None
) -> DigestMessage:
    if include_self_text is None:
        include_self_text = job.rules.include_self_text if job.rules else True
    plain_lines = [job.subject, "=" * len(job.subject), ""]
    for story in stories:
        plain_lines.append(_plain_entry(story, include_self_text))
        plain_lines.append("")
    items = "".join(_html_entry(s, include_self_text) for s in stories)
    html_body = (
        f"<html><body><h2>{html.escape(job.subject)}</h2>"
        f"<ol>{items}</ol></body></html>"
    )
    return DigestMessage(
        subject=job.subject,
        html=html_body,
        plain="\n".join(plain_lines).strip(),
    )
