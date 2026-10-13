"""Daily fetch: run all sources, report new items and no-update state.

This is the fetch layer entry. It runs the whole fetch layer, persists items
(dedup handles "new vs seen"), and reports a summary the caller uses to decide
whether to push a digest or a "no update" note.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from src.fetchers.pipeline import export_items_json
from src.fetchers.run_all import run_all_sources
from src.fetchers.store import JSONStore

logger = logging.getLogger(__name__)


@dataclass
class DailyFetchReport:
    new_count: int
    no_update: bool
    failed_by_source: dict[str, str] = field(default_factory=dict)  # source -> error detail
    added_by_source: dict[str, int] = field(default_factory=dict)

    @property
    def failed_sources(self) -> list[str]:
        """Names of sources that failed — derived, never stored separately."""
        return list(self.failed_by_source)


def run_daily_fetch(
    *,
    sources: dict,
    store_path: Path,
    digest_path: Path | None = None,
) -> DailyFetchReport:
    """Run all sources, export new items, return a report.

    `sources` is the same {name: (fetcher, parser)} shape as run_all_sources.
    When digest_path is given, the full item set is exported there so the
    summary task can consume it. A per-source failure never fails the run;
    it is carried in failed_by_source for the caller to surface.
    """
    results = run_all_sources(sources=sources, store_path=store_path)

    added_by_source: dict[str, int] = {}
    failed_by_source: dict[str, str] = {}
    total_added = 0
    for r in results:
        if r.status == "ok":
            added_by_source[r.source] = r.added
            total_added += r.added
        else:
            name = r.source or "unknown"
            failed_by_source[name] = r.error or "unknown error"
            logger.error("source %s failed: %s", name, failed_by_source[name])

    if digest_path is not None:
        store = JSONStore(store_path)
        export_items_json(store.all_items(), digest_path)

    return DailyFetchReport(
        new_count=total_added,
        no_update=total_added == 0,
        failed_by_source=failed_by_source,
        added_by_source=added_by_source,
    )


def build_failure_alert(failed_by_source: dict[str, str]) -> str:
    """Compose the failure-alert block appended to the digest (T8).

    Empty input returns "" so a clean run produces no noise.
    """
    if not failed_by_source:
        return ""
    lines = ["⚠️ 以下信息源抓取失败（本次未推送其内容）："]
    for source, err in failed_by_source.items():
        lines.append(f"- {source}: {err}")
    return "\n".join(lines)


def log_failures_to_file(report: DailyFetchReport, log_path: Path) -> None:
    """Persist per-source failure details (source, error, timestamp) to a file.

    Satisfies T8's "失败详情写入本地日志" criterion: failures must be
    recoverable after the run, not only visible in the pushed alert.
    """
    if not report.failed_by_source:
        return
    log_path.parent.mkdir(parents=True, exist_ok=True)
    from datetime import datetime, timezone

    ts = datetime.now(timezone.utc).isoformat()
    with log_path.open("a", encoding="utf-8") as fh:
        for source, err in report.failed_by_source.items():
            fh.write(f"{ts} source={source} error={err}\n")
