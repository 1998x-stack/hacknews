from hacknews.models import Rules, Story
from hacknews.selector import select


def _story(id_, score=0, comments=0, hours=0.0, title="t", url=None):
    return Story(id=id_, title=title, url=url, score=score, comments=comments, hours_old=hours)


def test_filters_and_orders_by_score():
    stories = [_story(1, score=100), _story(2, score=5), _story(3, score=50)]
    out = select(stories, Rules(min_score=10))
    assert [s.id for s in out] == [1, 3]


def test_dedupes_by_url():
    stories = [_story(1, url="https://a.example"), _story(2, url="https://a.example")]
    assert len(select(stories, Rules())) == 1


def test_drops_dead():
    story = Story(id=1, title="", is_dead=True)
    assert select([story], Rules()) == []


def test_keyword_include():
    stories = [_story(1, title="Rust news"), _story(2, title="Cooking")]
    out = select(stories, Rules(keywords_include=["rust"]))
    assert [s.id for s in out] == [1]



def test_age_filter_removes_old_stories():
    story = _story(1, score=50, hours=100.0)
    assert select([story], Rules(max_age_hours=24)) == []
