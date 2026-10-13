"""S13 seam: apply preferences to filter items for the digest (fetch stays full)."""
from datetime import datetime, timezone

from src.daily.preferences import Preferences
from src.daily.filter import filter_items_for_push
from src.fetchers.models import Item


def _item(source: str, title: str, content: str = "") -> Item:
    return Item(
        source=source,
        title=title,
        link=f"https://example.com/{source}/{title}",
        published=datetime(2026, 10, 13, tzinfo=timezone.utc),
        summary=content[:300],
        content=content,
    )


def test_no_preferences_keeps_all():
    items = [_item("arxiv", "A"), _item("smol.ai", "B")]
    kept, filtered = filter_items_for_push(items, Preferences())
    assert len(kept) == 2
    assert filtered == []


def test_keyword_blacklist_filters_matching_items():
    items = [
        _item("arxiv", "Reinforcement Learning Advances"),
        _item("arxiv", "Unrelated Paper"),
    ]
    prefs = Preferences(blocked_keywords=["reinforcement"])
    kept, filtered = filter_items_for_push(items, prefs)
    assert [i.title for i in kept] == ["Unrelated Paper"]
    assert len(filtered) == 1
    assert filtered[0].title == "Reinforcement Learning Advances"


def test_keyword_match_is_case_insensitive_and_searches_content():
    items = [
        _item("arxiv", "Title Only", "body mentions AGENTS for workflow"),
        _item("arxiv", "Other", "nothing relevant"),
    ]
    prefs = Preferences(blocked_keywords=["agents"])
    kept, filtered = filter_items_for_push(items, prefs)
    assert [i.title for i in kept] == ["Other"]
    assert len(filtered) == 1


def test_disabled_source_filters_whole_source():
    items = [
        _item("thebatch", "Weekly A"),
        _item("arxiv", "Paper B"),
    ]
    prefs = Preferences(disabled_sources=["thebatch"])
    kept, filtered = filter_items_for_push(items, prefs)
    assert [i.source for i in kept] == ["arxiv"]
    assert len(filtered) == 1


def test_filter_returns_lists_but_never_mutates_items():
    items = [_item("arxiv", "A"), _item("smol.ai", "B")]
    prefs = Preferences(disabled_sources=["smol.ai"])
    kept, filtered = filter_items_for_push(items, prefs)
    # Original list untouched (fetch stays full; filtering is only the push view)
    assert len(items) == 2
    assert len(kept) == 1
    assert len(filtered) == 1
