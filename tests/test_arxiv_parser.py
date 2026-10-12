"""S4 seam: parse arXiv cs.AI list page HTML into Items.

arXiv list pages carry title, link, authors, comments and subjects — but no
abstract. The 'summary' field is assembled from authors + subjects (the
closest to an abstract the list page provides); content is left empty.
"""
from pathlib import Path

import pytest

from src.fetchers.arxiv import parse_arxiv_list

FIXTURE = Path(__file__).parent / "fixtures" / "arxiv_csai.html"


def test_parse_arxiv_returns_50_entries():
    items = parse_arxiv_list(FIXTURE.read_bytes())
    assert len(items) == 50


def test_parse_arxiv_first_item_fields():
    items = parse_arxiv_list(FIXTURE.read_bytes())
    first = items[0]
    assert first.source == "arxiv"
    assert first.title == "Can Language Models Play the Wikipedia Game?"
    assert first.link == "https://arxiv.org/abs/2610.13948"
    assert "Alexander Hickey" in first.summary
    # The accepted deviation assembles summary from authors AND subjects.
    assert "Subjects:" in first.summary
    assert "Artificial Intelligence" in first.summary


def test_parse_arxiv_uses_listing_date():
    items = parse_arxiv_list(FIXTURE.read_bytes())
    # The fixture header reads "Mon, 12 Oct 2026 (showing first 50 ...)"
    assert items[0].published.isoformat().startswith("2026-10-12")


def test_parse_arxiv_link_absolute():
    items = parse_arxiv_list(FIXTURE.read_bytes())
    assert all(i.link.startswith("https://arxiv.org/abs/") for i in items)


def test_parse_arxiv_content_empty():
    items = parse_arxiv_list(FIXTURE.read_bytes())
    assert all(i.content == "" for i in items)


def test_parse_arxiv_malformed_raises():
    with pytest.raises(ValueError, match="not a valid arXiv list page"):
        parse_arxiv_list(b"<html><body>nothing</body></html>")
