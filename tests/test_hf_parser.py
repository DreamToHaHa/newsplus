"""S5 seam: parse Hugging Face papers page HTML into Items.

HF papers cards carry title (h3>a) and a link to /papers/<id>. No abstract
is on the card; summary stays empty.
"""
from pathlib import Path

import pytest

from src.fetchers.hf_papers import parse_hf_papers

FIXTURE = Path(__file__).parent / "fixtures" / "hf_papers.html"


def test_parse_hf_returns_35_entries():
    items = parse_hf_papers(FIXTURE.read_bytes())
    assert len(items) == 35


def test_parse_hf_first_item_fields():
    items = parse_hf_papers(FIXTURE.read_bytes())
    first = items[0]
    assert first.source == "huggingface"
    assert first.title == (
        "DiffusionART: Efficient, Stable and Scalable Reinforcement of Diffusion Models"
    )
    assert first.link == "https://huggingface.co/papers/2610.12572"


def test_parse_hf_links_absolute():
    items = parse_hf_papers(FIXTURE.read_bytes())
    assert all(i.link.startswith("https://huggingface.co/papers/") for i in items)


def test_parse_hf_summary_and_content_empty():
    items = parse_hf_papers(FIXTURE.read_bytes())
    assert all(i.summary == "" for i in items)
    assert all(i.content == "" for i in items)


def test_parse_hf_malformed_raises():
    with pytest.raises(ValueError, match="not a valid HF papers page"):
        parse_hf_papers(b"<html><body>nope</body></html>")
