"""Daily pipeline entry: fetch → summarize → print digest for WeChat delivery.

This is the single command OpenClaw's cron automation runs. Its stdout is
captured by the agent and delivered to the WeChat channel. A per-source
failure never blocks the digest — a failure alert rides along after it, and
failure details are persisted to a local log file.

stdout contract (one line, machine-checkable):
    NEW <count>|<digest text (chunked)>
    NONE|今日无新增… [optional failure alert]
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from src.daily.digest import no_update_message
from src.daily.fetch import (
    DailyFetchReport,
    build_failure_alert,
    log_failures_to_file,
    run_daily_fetch,
)
from src.daily.summarize import chunk_for_wechat, summarize
from src.fetchers.models import Item
from src.fetchers.sources import ALL_SOURCES

logger = logging.getLogger(__name__)

MAX_ITEMS_PER_SOURCE = 15


def _load_provider(openclaw_json: Path) -> dict:
    """Read the Volcano provider config from OpenClaw's config file."""
    cfg = json.loads(openclaw_json.read_text(encoding="utf-8"))
    prov = cfg["models"]["providers"]["volcengine-agent-plan"]
    return {
        "base_url": prov["baseUrl"],
        "api_key": prov["apiKey"],
        "model": "deepseek-v4.1-flash",
    }


def _recent_new_items(store_path: Path) -> list[Item]:
    """Items added in the last 36h — the ones the daily digest covers.

    The store keeps everything ever fetched; the digest should cover items
    fetched since the last run. We approximate by published/added recency,
    capped per source so a busy source (e.g. arXiv) can't flood the digest.
    """
    from datetime import datetime, timedelta, timezone

    from src.fetchers.store import JSONStore

    store = JSONStore(store_path)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=36)
    recent = [i for i in store.all_items() if i.published >= cutoff]
    by_source: dict[str, list[Item]] = {}
    for item in recent:
        by_source.setdefault(item.source, []).append(item)
    capped: list[Item] = []
    for source_items in by_source.values():
        source_items.sort(key=lambda i: i.published, reverse=True)
        capped.extend(source_items[:MAX_ITEMS_PER_SOURCE])
    return capped


def compose_delivery_text(
    *,
    report: DailyFetchReport,
    digest_text: str | None = None,
    no_update_note: str | None = None,
) -> list[str]:
    """Build the WeChat-chunked message body, alert appended last.

    `digest_text` (a generated digest) and `no_update_note` are mutually
    exclusive; exactly one is expected. The failure alert, when present, is
    appended as its own chunk so it is never split mid-content by chunking.
    """
    if digest_text is not None:
        chunks = chunk_for_wechat(digest_text)
    else:
        chunks = chunk_for_wechat(no_update_note or "")

    alert = build_failure_alert(report.failed_by_source)
    if alert:
        chunks.extend(chunk_for_wechat(f"\n\n{alert}"))
    return chunks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="newsplus daily pipeline")
    parser.add_argument("--store", default="data/items.json")
    parser.add_argument("--digest", default="data/digest.json")
    parser.add_argument("--failure-log", default="data/daily-errors.log")
    parser.add_argument("--openclaw-json", default="/home/<user>/.openclaw/openclaw.json")
    parser.add_argument("--run-date", default=None, help="YYYY-MM-DD (defaults to today)")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    if args.verbose:
        logging.basicConfig(level=logging.INFO)

    from datetime import datetime

    run_date = args.run_date or datetime.now().strftime("%Y-%m-%d")
    store_path = Path(args.store)

    report = run_daily_fetch(sources=ALL_SOURCES, store_path=store_path, digest_path=Path(args.digest))
    log_failures_to_file(report, Path(args.failure_log))

    # A source failure never blocks the digest: the alert rides along after it.
    if report.no_update:
        chunks = compose_delivery_text(report=report, no_update_note=no_update_message())
        print("NONE", flush=True)
        for chunk in chunks:
            print(chunk, flush=True)
        return 0

    # Summarize the new items via the Volcano model.
    try:
        provider = _load_provider(Path(args.openclaw_json))
        items = _recent_new_items(store_path)
        text = summarize(items=items, run_date=run_date, **provider)
    except Exception as exc:
        logger.exception("summarize failed")
        print(f"ERROR summarize failed: {exc}", flush=True)
        return 3

    chunks = compose_delivery_text(report=report, digest_text=text)
    print(f"NEW {report.new_count}", flush=True)
    for chunk in chunks:
        print(chunk, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
