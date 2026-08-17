from hacknews.digest_builder import build
from hacknews.models import DigestJob, Rules, Story


def test_build_subject_and_escapes_html():
    story = Story(id=1, title="Hello & Goodbye", url="https://x.example/a", score=10, comments=3, domain="x.example")
    job = DigestJob(name="m", cron="0 8 * * *", subject="Morning")
    msg = build(job, [story])
    assert msg.subject == "Morning"
    assert "Hello &amp; Goodbye" in msg.html
    assert "https://x.example/a" in msg.plain


def test_build_includes_self_text():
    story = Story(id=2, title="Ask", text="Question here", url=None)
    job = DigestJob(name="t", cron="* * * * *", subject="S")
    assert "Question here" in build(job, [story]).plain



def test_build_respects_include_self_text_false():
    job = DigestJob(name="t", cron="* * * * *", subject="S", rules=Rules(include_self_text=False))
    msg = build(job, [Story(id=2, title="Ask", text="SECRET_BODY", url=None)])
    assert "SECRET_BODY" not in msg.plain
    assert "SECRET_BODY" not in msg.html
