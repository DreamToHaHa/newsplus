"""Summarize seam: prompt building + WeChat chunking (the model call is live-verified)."""
from datetime import datetime, timezone

from src.daily.summarize import (
    build_summary_prompt,
    chunk_for_wechat,
    WECHAT_CHUNK_LIMIT,
)

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


def test_build_summary_prompt_includes_date_and_items():
    from src.daily.summarize import _SUMMARY_SYSTEM

    items = [_item("arxiv", "Paper A", "https://arxiv.org/abs/1", "body")]
    prompt = build_summary_prompt(items, run_date="2026-10-12")
    assert "2026-10-12" in prompt
    assert "Paper A" in prompt
    # The format requirement (Chinese commentary) lives in the system prompt.
    assert "中文一句话点评" in _SUMMARY_SYSTEM


def test_build_summary_prompt_empty_items_returns_empty():
    assert build_summary_prompt([], run_date="2026-10-12") == ""


def test_chunk_for_wechat_short_text_single_chunk():
    text = "short digest"
    chunks = chunk_for_wechat(text)
    assert chunks == ["short digest"]


def test_chunk_for_wechat_splits_long_text():
    long_text = "X" * (WECHAT_CHUNK_LIMIT * 2 + 500)
    chunks = chunk_for_wechat(long_text)
    assert len(chunks) > 1
    assert all(len(c) <= WECHAT_CHUNK_LIMIT for c in chunks)
    # Reassembled content matches (minus chunk-boundary loss)
    assert "".join(chunks) == long_text


def test_chunk_for_wechat_does_not_split_paragraph_in_half():
    # A paragraph longer than the limit may be split, but normal paragraphs
    # under the limit must stay whole when possible.
    para = "y" * 100
    text = para + "\n\n" + para
    chunks = chunk_for_wechat(text)
    assert len(chunks) <= 2
