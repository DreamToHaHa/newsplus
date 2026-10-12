"""Fetch and parse Hugging Face papers page into Items.

HF papers cards carry title (h3>a) and a link to /papers/<id>. No abstract
is present on the card, so summary/content stay empty.
"""
from __future__ import annotations

import logging
import re

from ._util import fetch_bytes, now_utc, strip_html
from .models import Item

logger = logging.getLogger(__name__)

SOURCE = "huggingface"
PAPERS_URL = "https://huggingface.co/papers"


def fetch_hf_papers(timeout: int = 25) -> bytes:
    """Fetch the raw HF papers page."""
    return fetch_bytes(PAPERS_URL, timeout=timeout)


def parse_hf_papers(data: bytes) -> list[Item]:
    """Parse an HF papers page into Items.

    Raises ValueError when the data is not a recognizable HF papers page.
    """
    text = data.decode("utf-8", errors="replace")

    # Card pattern: <h3><a href="/papers/2610.12572">Title</a></h3>
    matches = re.findall(
        r'<h3[^>]*>\s*<a[^>]*href="(/papers/[0-9]+\.[0-9]+)"[^>]*>(.*?)</a>\s*</h3>',
        text,
        flags=re.S,
    )

    items: list[Item] = []
    for path, raw_title in matches:
        title = strip_html(raw_title)
        if not title:
            continue
        items.append(
            Item(
                source=SOURCE,
                title=title,
                link=f"https://huggingface.co{path}",
                published=now_utc(),
                summary="",
                content="",
            )
        )

    if not items:
        raise ValueError("data is not a valid HF papers page")
    return items
