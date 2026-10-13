"""Apply user preferences (GLOSSARY: 过滤) to the digest item list.

Filtering happens at push time only: the fetch layer always stores full data
(ADR-0003). This module returns the kept and filtered subsets without
mutating the input, so nothing is ever lost.
"""
from __future__ import annotations

from src.daily.preferences import Preferences
from src.fetchers.models import Item


def filter_items_for_push(items: list[Item], prefs: Preferences) -> tuple[list[Item], list[Item]]:
    """Partition items into (kept, filtered) by the given preferences.

    An item is filtered when its source is disabled, or when its title or
    content contains a blacklisted keyword.
    """
    kept: list[Item] = []
    filtered: list[Item] = []
    for item in items:
        # Source ids are lowercase canonical (e.g. "thebatch"); the preferences
        # CLI normalizes display names ("The Batch") to that form on write, so
        # a direct compare here is correct.
        if item.source in prefs.disabled_sources:
            filtered.append(item)
            continue
        haystack = f"{item.title}\n{item.content}"
        if prefs.matches_keyword(haystack):
            filtered.append(item)
            continue
        kept.append(item)
    return kept, filtered
