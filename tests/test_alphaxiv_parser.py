"""S7 seam: parse alphaXiv home page JSON-LD (Trending Papers) into Items."""
from pathlib import Path

import pytest

from src.fetchers.alphaxiv import parse_alphaxiv

FIXTURE = Path(__file__).parent / "fixtures" / "alphaxiv.html"


def test_parse_alphaxiv_returns_trending_papers():
    items = parse_alphaxiv(FIXTURE.read_bytes())
    assert len(items) == 20


def test_parse_alphaxiv_first_item_fields():
    items = parse_alphaxiv(FIXTURE.read_bytes())
    first = items[0]
    assert first.source == "alphaxiv"
    assert first.title == (
        "Embodied Turing Machines: Stateful Code for Robot Recursive Self-Improvement"
    )
    assert first.link == "https://www.alphaxiv.org/abs/2610.12369"
    assert len(first.summary) > 0


def test_parse_alphaxiv_links_absolute():
    items = parse_alphaxiv(FIXTURE.read_bytes())
    assert all(i.link.startswith("https://www.alphaxiv.org/abs/") for i in items)


def test_parse_alphaxiv_malformed_raises():
    with pytest.raises(ValueError, match="not a valid alphaXiv page"):
        parse_alphaxiv(b"<html><body>empty</body></html>")
