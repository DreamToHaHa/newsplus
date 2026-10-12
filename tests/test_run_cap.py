"""Tests for the daily run's per-source item cap."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.daily.run import MAX_ITEMS_PER_SOURCE, _recent_new_items
from src.fetchers.models import Item
from src.fetchers.store import JSONStore


def _make_store(tmp_path, items):
    store = JSONStore(tmp_path / "items.json")
    store.store(items)
    return store


def _item(source, title, published):
    return Item(
        source=source,
        title=title,
        link=f"https://example.com/{source}/{title}",
        published=published,
        summary="",
    )


def test_cap_limits_busy_source(tmp_path):
    now = datetime.now(timezone.utc)
    items = [_item("arxiv", f"paper-{i}", now - timedelta(hours=i)) for i in range(40)]
    _make_store(tmp_path, items)
    result = _recent_new_items(tmp_path / "items.json")
    arxiv_items = [i for i in result if i.source == "arxiv"]
    assert len(arxiv_items) <= MAX_ITEMS_PER_SOURCE
    assert len(arxiv_items) == MAX_ITEMS_PER_SOURCE


def test_cap_keeps_newest_first(tmp_path):
    now = datetime.now(timezone.utc)
    items = [
        _item("arxiv", "newest", now - timedelta(hours=1)),
        _item("arxiv", "oldest", now - timedelta(hours=30)),
    ]
    _make_store(tmp_path, items)
    result = _recent_new_items(tmp_path / "items.json")
    arxiv_items = [i for i in result if i.source == "arxiv"]
    assert arxiv_items[0].title == "newest"


def test_cap_filters_older_than_36h(tmp_path):
    now = datetime.now(timezone.utc)
    items = [
        _item("arxiv", "old", now - timedelta(hours=40)),
        _item("smol.ai", "recent", now - timedelta(hours=2)),
    ]
    _make_store(tmp_path, items)
    result = _recent_new_items(tmp_path / "items.json")
    titles = [i.title for i in result]
    assert "recent" in titles
    assert "old" not in titles
