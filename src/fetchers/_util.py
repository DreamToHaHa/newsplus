"""Shared helpers for fetcher modules.

Keeps the per-source modules to "URL + selector" by factoring out the fetch
and HTML-cleaning shapes that would otherwise be duplicated five times.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

import requests

logger = logging.getLogger(__name__)


def fetch_bytes(url: str, timeout: int = 25) -> bytes:
    """GET a URL, raise on HTTP error, return raw content bytes."""
    logger.info("fetching %s", url)
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.content


def strip_html(text: str) -> str:
    """Remove tags and collapse runs of whitespace to single spaces."""
    stripped = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", stripped).strip()


def now_utc() -> datetime:
    """Current time in UTC — the fallback/primary publish stamp for sources
    that don't expose a real date."""
    return datetime.now(timezone.utc)
