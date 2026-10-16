"""S15 seam: build an HTML email digest from filtered items."""
from datetime import datetime, timezone

from src.daily.email_digest import build_html_digest
from src.fetchers.models import Item


def _item(source: str, title: str, link: str, summary: str = "") -> Item:
    return Item(
        source=source,
        title=title,
        link=link,
        published=datetime(2026, 10, 13, tzinfo=timezone.utc),
        summary=summary,
        content="",
    )


def test_html_digest_is_complete_document():
    html = build_html_digest([], run_date="2026-10-13", title="AI 源头日报")
    assert html.startswith("<!DOCTYPE html>") or "<html" in html
    assert "2026-10-13" in html
    assert "AI 源头日报" in html


def test_html_digest_groups_by_source():
    items = [
        _item("arxiv", "Paper A", "https://arxiv.org/abs/1", "summary a"),
        _item("smol.ai", "News B", "https://news.smol.ai/1", "summary b"),
    ]
    html = build_html_digest(items, run_date="2026-10-13", title="AI 源头日报")
    assert "arxiv" in html
    assert "smol.ai" in html
    # Both titles and links present and clickable
    assert "Paper A" in html
    assert "href=\"https://arxiv.org/abs/1\"" in html
    assert "News B" in html


def test_html_digest_includes_summary():
    items = [_item("arxiv", "Paper A", "https://arxiv.org/abs/1", "this is the summary")]
    html = build_html_digest(items, run_date="2026-10-13", title="AI 源头日报")
    assert "this is the summary" in html


def test_html_digest_empty_items_still_valid():
    html = build_html_digest([], run_date="2026-10-13", title="今日无新增")
    assert "今日无新增" in html
    assert "<html" in html


def test_html_digest_includes_overview_block():
    items = [_item("arxiv", "Paper A", "https://arxiv.org/abs/1", "summary")]
    html = build_html_digest(
        items, run_date="2026-10-13", title="AI 源头日报", overview="今日模型与 Agent 进展显著。"
    )
    assert "今日要点" in html
    assert "今日模型与 Agent 进展显著。" in html


def test_html_digest_overview_multiline_renders_separate_paragraphs():
    items = [_item("arxiv", "Paper A", "https://arxiv.org/abs/1", "summary")]
    overview = "第一行要点\n第二行要点\n第三行要点"
    html = build_html_digest(
        items, run_date="2026-10-13", title="AI 源头日报", overview=overview
    )
    # Each line becomes its own <p> inside the overview block
    assert html.count("<p style=\"margin:4px 0;\">第一行要点</p>") == 1
    assert html.count("<p style=\"margin:4px 0;\">第二行要点</p>") == 1
    assert html.count("<p style=\"margin:4px 0;\">第三行要点</p>") == 1


def test_html_digest_drops_overview_containing_url():
    items = [_item("arxiv", "Paper A", "https://arxiv.org/abs/1", "summary")]
    # Model went off-script and listed an item with a URL → drop the block
    html = build_html_digest(
        items,
        run_date="2026-10-13",
        title="AI 源头日报",
        overview="今日要点\nhttps://arxiv.org/abs/1\n标题跑偏了",
    )
    assert "今日要点" not in html


def test_html_digest_uses_commentary_in_card():
    items = [_item("arxiv", "Paper A", "https://arxiv.org/abs/1", "summary")]
    html = build_html_digest(
        items,
        run_date="2026-10-13",
        title="AI 源头日报",
        commentary={"Paper A": "中文逐条点评"},
    )
    assert "中文逐条点评" in html
    # Without commentary the card falls back to the item summary
    plain = build_html_digest(items, run_date="2026-10-13", title="AI 源头日报")
    assert "summary" in plain
