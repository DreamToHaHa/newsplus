"""S6 seam: parse The Batch issue page HTML into Items.

The Batch issue pages (e.g. /the-batch/issue-374) render the week's articles
as h1 headings followed by <p> paragraphs — 4 articles per issue. Articles
share one page URL, so dedup identity lives in dedup_key, not link.
"""
from pathlib import Path

from src.fetchers.thebatch import parse_thebatch_issue

FIXTURE = Path(__file__).parent / "fixtures" / "thebatch_issue.html"


def test_parse_thebatch_returns_4_articles():
    items = parse_thebatch_issue(FIXTURE.read_bytes())
    assert len(items) == 4


def test_parse_thebatch_first_item_fields():
    items = parse_thebatch_issue(FIXTURE.read_bytes())
    first = items[0]
    assert first.source == "thebatch"
    assert first.title == "Sol Nearly Eclipses Astra"
    # link is the clean issue page URL; dedup identity is separate
    assert first.link == "https://www.deeplearning.ai/the-batch/issue-374/"
    assert first.dedup_key == (
        "https://www.deeplearning.ai/the-batch/issue-374/"
        "#sol-nearly-eclipses-astra"
    )


def test_parse_thebatch_items_have_content():
    items = parse_thebatch_issue(FIXTURE.read_bytes())
    assert all(i.content for i in items)


def test_parse_thebatch_dedup_keys_are_unique():
    items = parse_thebatch_issue(FIXTURE.read_bytes())
    keys = [i.dedup_key for i in items]
    assert len(set(keys)) == len(keys) == 4


def test_parse_thebatch_empty_bytes_is_natural_absence():
    # "无更新时自然缺席": empty input yields no items, not an error
    assert parse_thebatch_issue(b"") == []


def test_parse_thebatch_unrecognized_page_yields_nothing():
    assert parse_thebatch_issue(b"<html><body>no news here</body></html>") == []
