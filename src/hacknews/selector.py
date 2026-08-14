"""Apply selection rules to a list of stories."""
from __future__ import annotations

from hacknews.models import Rules, Story


def _matches_keywords(story: Story, rules: Rules) -> bool:
    hay = " ".join(
        filter(None, [story.title, story.domain or "", story.text or ""])
    ).lower()
    excluded = bool(rules.keywords_exclude) and any(k.lower() in hay for k in rules.keywords_exclude)
    included_ok = not rules.keywords_include or any(k.lower() in hay for k in rules.keywords_include)
    return not excluded and included_ok


def select(stories: list[Story], rules: Rules) -> list[Story]:
    seen: set[str] = set()
    kept: list[Story] = []
    for story in stories:
        if story.is_dead or story.score < rules.min_score:
            continue
        if story.comments < rules.min_comments or story.hours_old > rules.max_age_hours:
            continue
        if not _matches_keywords(story, rules):
            continue
        key = story.url or f"no-url:{story.id}"
        if key in seen:
            continue
        seen.add(key)
        kept.append(story)
    kept.sort(key=lambda s: s.score, reverse=True)
    return kept[: rules.top_n]
