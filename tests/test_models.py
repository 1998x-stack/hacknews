from hacknews.models import DigestJob, Rules, Story


def test_story_derives_domain():
    story = Story(id=1, title="t", url="https://example.com/path")
    assert story.score == 0
    assert story.domain == "example.com"


def test_rules_defaults():
    rules = Rules()
    assert rules.top_n == 10
    assert rules.max_age_hours == 24.0


def test_digestjob_rules_optional():
    job = DigestJob(name="a", cron="0 8 * * *", subject="S")
    assert job.rules is None
