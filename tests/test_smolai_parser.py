"""S1 seam: parse smol.ai RSS bytes into Item list."""
from pathlib import Path

import pytest

from src.fetchers.smolai import parse_smolai_rss

FIXTURE = Path(__file__).parent / "fixtures" / "smolai.rss"


def _feed_bytes() -> bytes:
    return FIXTURE.read_bytes()


def test_parse_returns_entries_for_real_feed():
    items = parse_smolai_rss(_feed_bytes())
    # Independent source of truth: the fixture feed actually contains 716 entries.
    assert len(items) == 716


def test_parse_first_item_fields():
    items = parse_smolai_rss(_feed_bytes())
    first = items[0]
    # Values observed directly from the fixture feed's first entry.
    assert first.title == "not much happened today"
    assert first.link == "https://news.smol.ai/issues/26-09-09-not-much/"
    assert first.published.isoformat() == "2026-09-09T05:44:39+00:00"
    assert len(first.summary) > 0


def test_parse_item_has_content_and_source():
    items = parse_smolai_rss(_feed_bytes())
    first = items[0]
    assert first.source == "smol.ai"
    # The fixture's first entry has a non-empty markdown body.
    assert first.content is not None and len(first.content) > 0


def test_parse_malformed_input_raises_clear_error():
    with pytest.raises(ValueError, match="not a valid smol.ai RSS"):
        parse_smolai_rss(b"<html><body>not rss</body></html>")


def test_parse_empty_feed_returns_empty():
    empty = b'<?xml version="1.0"?><rss version="2.0"><channel><title>AINews</title></channel></rss>'
    assert parse_smolai_rss(empty) == []
