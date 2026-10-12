"""Fetch and parse arXiv cs.AI listing pages into Items.

arXiv list pages (e.g. /list/cs.AI/recent) carry title, link, authors,
comments and subjects per entry, but no abstract. The Item.summary is
assembled from authors + subjects; content stays empty. The page header
carries the listing date, which becomes each Item's published date.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from email.utils import parsedate_to_datetime

from ._util import fetch_bytes, now_utc, strip_html
from .models import Item

logger = logging.getLogger(__name__)

SOURCE = "arxiv"
LIST_URL = "https://arxiv.org/list/cs.AI/recent"


def fetch_arxiv_list(timeout: int = 25) -> bytes:
    """Fetch the raw arXiv cs.AI recent listing."""
    return fetch_bytes(LIST_URL, timeout=timeout)


def parse_arxiv_list(data: bytes) -> list[Item]:
    """Parse an arXiv cs.AI list page into Items.

    Raises ValueError when the data is not a recognizable arXiv listing.
    """
    text = data.decode("utf-8", errors="replace")

    # The page header carries the listing date, e.g. "Mon, 12 Oct 2026".
    published = _parse_listing_date(text)

    items: list[Item] = []
    dt_blocks = re.split(r"<dt>", text)[1:]
    for block in dt_blocks:
        m = re.search(r'<a href\s*=\s*"/abs/([0-9.]+)"', block)
        if not m:
            continue
        abs_id = m.group(1)

        dd_match = re.search(r"<dd>(.*?)(?=<dt>|$)", block, flags=re.S)
        dd = dd_match.group(1) if dd_match else ""

        title_m = re.search(r"<div class='list-title mathjax'>(.*?)</div>", dd, flags=re.S)
        if not title_m:
            continue
        title = re.sub(r"^\s*Title:\s*", "", strip_html(title_m.group(1)))

        authors = _extract_authors(dd)
        subjects = _extract_subjects(dd)
        summary_parts = []
        if authors:
            summary_parts.append("Authors: " + ", ".join(authors))
        if subjects:
            summary_parts.append("Subjects: " + subjects)

        items.append(
            Item(
                source=SOURCE,
                title=title,
                link=f"https://arxiv.org/abs/{abs_id}",
                published=published,
                summary=" | ".join(summary_parts),
                content="",
            )
        )

    if not items:
        raise ValueError("data is not a valid arXiv list page")
    return items


def _parse_listing_date(text: str) -> datetime:
    """Extract the listing date from the page header.

    arXiv headers look like '<h3>Mon, 12 Oct 2026 (showing first 50 ...)';
    falls back to now when absent or unparseable.
    """
    m = re.search(r"<h3>([A-Z][a-z]{2}, \d{1,2} [A-Z][a-z]{2} \d{4})", text)
    if m:
        try:
            parsed = parsedate_to_datetime(m.group(1))
            if parsed.tzinfo is not None:
                return parsed
        except (TypeError, ValueError):
            pass
    logger.warning("could not parse arXiv listing date; using now")
    return now_utc()


def _extract_authors(dd: str) -> list[str]:
    authors_m = re.search(r"<div class='list-authors'>(.*?)</div>", dd, flags=re.S)
    if not authors_m:
        return []
    names = re.findall(r">([^<>]+)</a>", authors_m.group(1))
    cleaned = [re.sub(r"\s+", " ", n).strip() for n in names if n.strip()]
    return cleaned


def _extract_subjects(dd: str) -> str:
    subjects_m = re.search(r"<div class='list-subjects'>(.*?)</div>", dd, flags=re.S)
    if not subjects_m:
        return ""
    return strip_html(subjects_m.group(1))
