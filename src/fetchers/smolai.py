"""Fetch and parse news.smol.ai (AINews) RSS feed into Items.

smol.ai exposes a full RSS feed at /rss.xml with title, link, published date,
a summary (markdown) and an optional content body per entry.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser

from ._util import fetch_bytes
from .models import Item

logger = logging.getLogger(__name__)

SOURCE = "smol.ai"
RSS_URL = "https://news.smol.ai/rss.xml"


def fetch_smolai_rss(timeout: int = 20) -> bytes:
    """Fetch the raw smol.ai RSS feed over HTTP."""
    return fetch_bytes(RSS_URL, timeout=timeout)


def _parse_rfc822(value: str) -> datetime:
    """Parse an RFC-822/RSS date string into a timezone-aware datetime."""
    parsed = parsedate_to_datetime(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def parse_smolai_rss(data: bytes) -> list[Item]:
    """Parse raw smol.ai RSS bytes into a list of Items.

    Raises ValueError when the data is not a parseable smol.ai RSS feed.
    """
    parsed = feedparser.parse(data)

    if not parsed.get("version"):
        raise ValueError("data is not a valid smol.ai RSS feed")

    items: list[Item] = []
    for entry in parsed.entries:
        title = entry.get("title")
        link = entry.get("link")
        if not title or not link:
            logger.warning("skipping smol.ai entry missing title or link: %r", title)
            continue

        content = ""
        if entry.get("content"):
            content = entry.content[0].get("value", "")
        if not content:
            content = entry.get("summary", "")

        published = datetime.now(timezone.utc)
        if entry.get("published"):
            try:
                published = _parse_rfc822(entry.published)
            except (TypeError, ValueError):
                logger.warning("unparseable published date %r, using now", entry.published)

        items.append(
            Item(
                source=SOURCE,
                title=title,
                link=link,
                published=published,
                summary=entry.get("summary", ""),
                content=content,
            )
        )
    return items
