"""Run the whole fetch layer: every configured source, isolating failures.

Each source run is independent: a failure in one never blocks the others.
The results list is what the daily job (T6) consumes to build the digest and
its failure alert (T8).
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from .models import Item
from .pipeline import RunResult, fetch_and_store
from .store import JSONStore

logger = logging.getLogger(__name__)

SourceSpec = dict[str, tuple[Callable[[], bytes], Callable[[bytes], list[Item]]]]


def run_all_sources(
    *,
    sources: SourceSpec,
    store_path: Path,
) -> list[RunResult]:
    """Fetch+parse+store every source. Returns one RunResult per source."""
    store = JSONStore(store_path)
    results: list[RunResult] = []
    for name, (fetcher, parser) in sources.items():
        logger.info("running source %s", name)
        try:
            result = fetch_and_store(fetcher=fetcher, parser=parser, store=store, source=name)
        except Exception as exc:  # noqa: BLE001 - last-resort isolation
            logger.exception("unexpected failure in source %s", name)
            result = RunResult(status="error", source=name, added=0, duplicate=0, error=str(exc))
        results.append(result)
    return results
