"""S2 seam: store deduplicates Items by link and reports counts."""
from datetime import datetime, timezone

from src.fetchers.models import Item
from src.fetchers.store import JSONStore


def _item(link: str, title: str = "t") -> Item:
    return Item(
        source="smol.ai",
        title=title,
        link=link,
        published=datetime(2026, 9, 9, 5, 44, 39, tzinfo=timezone.utc),
        summary="s",
    )


def test_store_starts_empty(tmp_path):
    store = JSONStore(tmp_path / "items.json")
    assert store.is_seen("https://news.smol.ai/x") is False


def test_store_new_items_reported_as_added(tmp_path):
    store = JSONStore(tmp_path / "items.json")
    a = _item("https://news.smol.ai/a")
    b = _item("https://news.smol.ai/b")
    added, duplicate = store.store([a, b])
    assert added == 2
    assert duplicate == 0


def test_store_deduplicates_by_link(tmp_path):
    store = JSONStore(tmp_path / "items.json")
    a1 = _item("https://news.smol.ai/a", title="first")
    a2 = _item("https://news.smol.ai/a", title="second")
    added, duplicate = store.store([a1])
    assert added == 1
    added2, duplicate2 = store.store([a2])
    assert added2 == 0
    assert duplicate2 == 1


def test_store_persists_across_instances(tmp_path):
    path = tmp_path / "items.json"
    store1 = JSONStore(path)
    store1.store([_item("https://news.smol.ai/persist")])
    store2 = JSONStore(path)
    assert store2.is_seen("https://news.smol.ai/persist") is True


def test_store_reports_added_items_content(tmp_path):
    store = JSONStore(tmp_path / "items.json")
    item = _item("https://news.smol.ai/c", title="contentful")
    item.content = "full markdown body"
    added, _ = store.store([item])
    assert added == 1
    stored = store.all_items()
    assert stored[0].content == "full markdown body"


def test_store_recovers_from_corrupted_file(tmp_path):
    path = tmp_path / "items.json"
    path.write_text("{ this is not valid json", encoding="utf-8")
    store = JSONStore(path)
    assert store.all_items() == []
    added, _ = store.store([_item("https://news.smol.ai/after-corrupt")])
    assert added == 1
