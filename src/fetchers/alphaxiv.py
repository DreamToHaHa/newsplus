"""Fetch and parse the alphaXiv home page into Items.

The alphaXiv home page embeds a schema.org JSON-LD block, "Trending Papers"
(an ItemList of 20 papers), each with headline, url and description.
"""
from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterable

from ._util import fetch_bytes, now_utc
from .models import Item

logger = logging.getLogger(__name__)

SOURCE = "alphaxiv"
HOME_URL = "https://alphaxiv.org"


def fetch_alphaxiv(timeout: int = 25) -> bytes:
    """Fetch the raw alphaXiv home page."""
    return fetch_bytes(HOME_URL, timeout=timeout)


def parse_alphaxiv(data: bytes) -> list[Item]:
    """Parse alphaXiv home page JSON-LD into Items (Trending Papers).

    Raises ValueError when the data is not a recognizable alphaXiv page.
    """
    text = data.decode("utf-8", errors="replace")

    trending: list[Item] = []
    for block in re.findall(
        r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', text, flags=re.S
    ):
        try:
            parsed = json.loads(block)
        except json.JSONDecodeError:
            logger.exception("malformed JSON-LD block on alphaXiv page; skipping")
            continue

        papers = _find_trending_papers(parsed)
        if papers is None:
            continue
        for item in papers:
            title = item.get("headline", "")
            url = item.get("url", "")
            desc = item.get("description", "")
            if not title or not url:
                continue
            trending.append(
                Item(
                    source=SOURCE,
                    title=title.strip(),
                    link=url,
                    published=now_utc(),
                    summary=desc.strip(),
                    content="",
                )
            )
        # Only one Trending Papers list is expected; stop after it.
        break

    if not trending:
        raise ValueError("data is not a valid alphaXiv page")
    return trending


def _find_trending_papers(value) -> list[dict] | None:
    """Locate the ItemList named 'Trending Papers' in decoded JSON-LD.

    Searches the top level and any @graph; returns the paper item list or None.
    """
    candidates: Iterable[dict] = ()
    if isinstance(value, dict):
        candidates = [value] + (value.get("@graph", []) if isinstance(value.get("@graph"), list) else [])
    elif isinstance(value, list):
        candidates = value

    for node in candidates:
        if not isinstance(node, dict):
            continue
        if node.get("name") == "Trending Papers":
            elements = node.get("itemListElement", [])
            return [
                (e.get("item", {}) if isinstance(e, dict) else {})
                for e in elements
                if isinstance(e, dict)
            ]
    return None
