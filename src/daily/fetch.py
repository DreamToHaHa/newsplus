"""Daily fetch: run all sources, report new items and no-update state.

This is the entry point OpenClaw's cron invokes. It runs the whole fetch
layer, persists items (dedup handles "new vs seen"), and reports a summary
the caller uses to decide whether to push a digest or a "no update" note.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from src.fetchers.pipeline import export_items_json
from src.fetchers.run_all import run_all_sources
from src.fetchers.store import JSONStore

logger = logging.getLogger(__name__)


@dataclass
class DailyFetchReport:
    status: str  # "ok" | "error"
    new_count: int
    no_update: bool
    failed_sources: list[str]
    added_by_source: dict[str, int]


def run_daily_fetch(
    *,
    sources: dict,
    store_path: Path,
    digest_path: Path | None = None,
) -> DailyFetchReport:
    """Run all sources, export new items, return a report.

    `sources` is the same {name: (fetcher, parser)} shape as run_all_sources.
    When digest_path is given, the full item set is exported there so the
    summary task can consume it.
    """
    results = run_all_sources(sources=sources, store_path=store_path)

    added_by_source: dict[str, int] = {}
    failed_sources: list[str] = []
    total_added = 0
    for r in results:
        if r.status == "ok":
            added_by_source[r.source] = r.added
            total_added += r.added
        else:
            failed_sources.append(r.source or "unknown")

    if digest_path is not None:
        store = JSONStore(store_path)
        export_items_json(store.all_items(), digest_path)

    return DailyFetchReport(
        status="ok" if not failed_sources else "ok",  # partial failures still "ok" for the report
        new_count=total_added,
        no_update=total_added == 0,
        failed_sources=failed_sources,
        added_by_source=added_by_source,
    )
