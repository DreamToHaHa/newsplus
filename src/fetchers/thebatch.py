"""Fetch and parse The Batch issue pages into Items.

The Batch issues live at https://www.deeplearning.ai/the-batch/issue-NNN/.
Each page renders the week's articles as h1 headings followed by <p>
paragraphs, after a "News" section heading.

The Batch is a weekly source: when there is no issue link on the index, or
the page yields no articles, the run yields zero Items (natural absence)
rather than failing — matching the spec's "无更新时自然缺席".

Several articles share one issue page URL, so each Item keeps the real issue
URL as its link and uses `issue_url#slug` as its dedup_key.
"""
from __future__ import annotations

import logging
import re

import requests

from ._util import fetch_bytes, now_utc, strip_html
from .models import Item

logger = logging.getLogger(__name__)

SOURCE = "thebatch"
INDEX_URL = "https://www.deeplearning.ai/the-batch/"


def fetch_thebatch_issue(timeout: int = 25) -> bytes:
    """Fetch the latest The Batch issue page HTML.

    Returns empty bytes when the index exposes no issue link, signalling
    "no update" to the pipeline rather than an error.
    """
    logger.info("fetching index %s", INDEX_URL)
    index = requests.get(INDEX_URL, timeout=timeout)
    index.raise_for_status()
    issues = [int(n) for n in re.findall(r"/the-batch/issue-(\d+)", index.text)]
    if not issues:
        logger.warning("no issue link on The Batch index; yielding nothing")
        return b""
    latest = max(issues)
    url = f"https://www.deeplearning.ai/the-batch/issue-{latest}/"
    return fetch_bytes(url, timeout=timeout)


def parse_thebatch_issue(data: bytes) -> list[Item]:
    """Parse a The Batch issue page into its articles.

    Returns an empty list (natural absence) when the page isn't a recognizable
    issue, so a stalled weekly source doesn't fail the run.
    """
    if not data:
        return []

    text = data.decode("utf-8", errors="replace")

    issue_url = "https://www.deeplearning.ai/the-batch/"
    issue_m = re.search(r"/the-batch/issue-(\d+)", text)
    if issue_m:
        issue_url = f"https://www.deeplearning.ai/the-batch/issue-{issue_m.group(1)}/"

    # Split the page on h1 headings; the first is the "News" section title,
    # the following h1s are article titles.
    segments = re.split(r"<h1[^>]*>", text)
    news_index = None
    for idx, seg in enumerate(segments):
        if strip_html(seg[:40]).lower().startswith("news"):
            news_index = idx
            break
    if news_index is None:
        logger.warning("no News section on The Batch page; yielding nothing")
        return []

    items: list[Item] = []
    for seg in segments[news_index + 1 :]:
        # The segment starts right after "<h1 ...>": the title is the text up
        # to the closing </h1>.
        close = seg.find("</h1>")
        title = strip_html(seg[:close] if close != -1 else seg[:300])
        if not title:
            continue
        paras = re.findall(r"<p[^>]*>(.*?)</p>", seg, flags=re.S)
        content = "\n\n".join(_clean_para(p) for p in paras)
        content = re.sub(r"\n{3,}", "\n\n", content).strip()
        if not content:
            continue
        slug = _slugify(title)
        items.append(
            Item(
                source=SOURCE,
                title=title,
                link=issue_url,
                published=now_utc(),
                summary=content[:300],
                content=content,
                dedup_key=f"{issue_url}#{slug}",
            )
        )
    return items


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", title).strip("-").lower()
    return slug or "article"


def _clean_para(p: str) -> str:
    return strip_html(p)
