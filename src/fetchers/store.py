"""Persistent store for fetched Items, deduplicating by link (GLOSSARY: 条目).

V1 uses a JSON file on disk: simple, inspectable, good enough for a solo
pipeline. The store is the seam where persistence lives; swapping to SQLite
later only changes this module.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path

from .models import Item

logger = logging.getLogger(__name__)


class JSONStore:
    """Persist Items to a JSON file and deduplicate new writes by link."""

    def __init__(self, path: Path):
        self._path = Path(path)
        self._items: list[Item] = []
        self._seen: set[str] = set()
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            with self._path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            self._items = [Item.from_dict(d) for d in data]
        except (json.JSONDecodeError, OSError, KeyError, ValueError):
            logger.exception("failed to load %s; starting empty", self._path)
            self._items = []
        self._seen = {i.dedup_key for i in self._items}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            [i.to_dict() for i in self._items], ensure_ascii=False, indent=2
        ).encode("utf-8")
        fd, tmp = tempfile.mkstemp(dir=self._path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(payload)
            os.replace(tmp, self._path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def is_seen(self, link: str) -> bool:
        return link in self._seen

    def store(self, items: list[Item]) -> tuple[int, int]:
        """Store new Items. Returns (added, duplicate)."""
        added = 0
        duplicate = 0
        for item in items:
            if item.dedup_key in self._seen:
                duplicate += 1
                continue
            self._seen.add(item.dedup_key)
            self._items.append(item)
            added += 1
        if added:
            self._save()
        return added, duplicate

    def all_items(self) -> list[Item]:
        return list(self._items)
