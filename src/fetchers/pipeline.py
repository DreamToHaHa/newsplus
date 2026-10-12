"""Orchestration for a single source: fetch → parse → store (GLOSSARY: 抓取).

The pipeline is the seam where a source's fetcher (bytes) and parser
(bytes → Items) are injected, so adding a new source never changes this
module. A run produces a RunResult the daily job can surface.
"""
from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .models import Item
from .store import JSONStore

logger = logging.getLogger(__name__)


@dataclass
class RunResult:
    """Outcome of one source run in the daily pipeline."""

    status: str  # "ok" | "error"
    source: str | None
    added: int
    duplicate: int
    error: str | None = None


def fetch_and_store(
    *,
    fetcher: Callable[[], bytes],
    parser: Callable[[bytes], list[Item]],
    store: JSONStore,
    source: str | None = None,
) -> RunResult:
    """Fetch raw bytes, parse to Items, store new ones.

    `source` names the run when supplied (run_all passes it); otherwise the
    first parsed Item's source is used. A failure always reports the given
    source name.
    """
    try:
        data = fetcher()
        items = parser(data)
    except Exception as exc:
        logger.exception("source run failed")
        return RunResult(status="error", source=source, added=0, duplicate=0, error=str(exc))

    try:
        added, duplicate = store.store(items)
    except Exception as exc:
        logger.exception("store write failed")
        return RunResult(status="error", source=source, added=0, duplicate=0, error=str(exc))

    resolved = source if source is not None else (items[0].source if items else None)
    logger.info("run ok source=%s added=%d duplicate=%d", resolved, added, duplicate)
    return RunResult(status="ok", source=resolved, added=added, duplicate=duplicate)


def export_items_json(items: list[Item], path: Path) -> None:
    """Export Items to a JSON file consumable by the downstream summary task."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps([i.to_dict() for i in items], ensure_ascii=False, indent=2)
    with path.open("w", encoding="utf-8") as fh:
        fh.write(payload)
