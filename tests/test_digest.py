"""S9 seam: digest text assembly — organize new items into a push-ready digest."""
from datetime import datetime, timezone

from src.daily.digest import build_digest_input, no_update_message

from src.fetchers.models import Item


def _item(source: str, title: str, link: str, content: str = "") -> Item:
    return Item(
        source=source,
        title=title,
        link=link,
        published=datetime(2026, 10, 12, tzinfo=timezone.utc),
        summary=content[:300],
        content=content,
    )


def test_no_update_message_mentions_no_update():
    msg = no_update_message()
    assert "无新增" in msg
    assert len(msg) > 10


def test_build_digest_input_groups_by_source():
    items = [
        _item("arxiv", "Paper A", "https://arxiv.org/abs/1"),
        _item("smol.ai", "News B", "https://news.smol.ai/1"),
        _item("arxiv", "Paper C", "https://arxiv.org/abs/2"),
    ]
    out = build_digest_input(items)
    # Grouped by source, arxiv first section has 2 items
    assert "# arxiv" in out
    assert "# smol.ai" in out
    assert "Paper A" in out
    assert "Paper C" in out
    assert "News B" in out


def test_build_digest_input_includes_link_and_content():
    items = [_item("arxiv", "Paper A", "https://arxiv.org/abs/1", "full body here")]
    out = build_digest_input(items)
    assert "https://arxiv.org/abs/1" in out
    assert "full body here" in out


def test_build_digest_input_empty():
    assert build_digest_input([]) == ""
