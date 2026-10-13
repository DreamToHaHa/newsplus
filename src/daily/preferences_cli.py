"""Preferences CLI — the interface the OpenClaw agent calls when a user
states a preference in WeChat ("以后不推 XX").

The agent translates the conversation into these structured operations, so
the stored rules stay machine-readable and auditable. USER.md may mirror the
intent; data/preferences.json is the source of truth.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.daily.preferences import Preferences, load_preferences, save_preferences

# Canonical source ids (lowercase, as used across the fetchers).
SOURCE_IDS = {
    "smol.ai": "smol.ai",
    "smolai": "smol.ai",
    "arxiv": "arxiv",
    "huggingface": "huggingface",
    "hugging face": "huggingface",
    "hf": "huggingface",
    "the batch": "thebatch",
    "thebatch": "thebatch",
    "alphaxiv": "alphaxiv",
}


def _normalize_source(value: str) -> str:
    """Map a display name ("The Batch", "hugging face") to the canonical id."""
    return SOURCE_IDS.get(value.strip().lower(), value.strip().lower())


def _mutate(path: Path, attr: str, value: str, adding: bool) -> Preferences:
    """load → check → mutate → save for one list attribute."""
    prefs = load_preferences(path)
    items = getattr(prefs, attr)
    if adding and value not in items:
        items.append(value)
    elif not adding and value in items:
        items.remove(value)
    save_preferences(prefs, path)
    return prefs


def add_keyword(path: Path, keyword: str) -> Preferences:
    return _mutate(path, "blocked_keywords", keyword, adding=True)


def remove_keyword(path: Path, keyword: str) -> Preferences:
    return _mutate(path, "blocked_keywords", keyword, adding=False)


def disable_source(path: Path, source: str) -> Preferences:
    return _mutate(path, "disabled_sources", _normalize_source(source), adding=True)


def enable_source(path: Path, source: str) -> Preferences:
    return _mutate(path, "disabled_sources", _normalize_source(source), adding=False)


_ACTIONS = {
    "add-keyword": ("blocked_keywords", True, False),
    "remove-keyword": ("blocked_keywords", False, False),
    "disable-source": ("disabled_sources", True, True),
    "enable-source": ("disabled_sources", False, True),
}


def main(argv: list[str] | None = None) -> int:
    """CLI entry the OpenClaw agent calls after a WeChat preference.

    Usage:
        python -m src.daily.preferences_cli [--preferences data/preferences.json]
            --action add-keyword|remove-keyword|disable-source|enable-source|list
            [--value <keyword-or-source>]
    """
    parser = argparse.ArgumentParser(description="newsplus preferences")
    parser.add_argument("--preferences", default="data/preferences.json")
    parser.add_argument("--action", required=True, choices=[*_ACTIONS, "list"])
    parser.add_argument("--value", default="")
    args = parser.parse_args(argv)

    path = Path(args.preferences)

    if args.action == "list":
        prefs = load_preferences(path)
        print(f"blocked_keywords: {prefs.blocked_keywords}")
        print(f"disabled_sources: {prefs.disabled_sources}")
        return 0

    attr, adding, is_source = _ACTIONS[args.action]
    if not args.value:
        print(f"ERROR --value required for {args.action}", flush=True)
        return 2

    value = _normalize_source(args.value) if is_source else args.value
    _mutate(path, attr, value, adding)
    print(f"ok: {args.action} {args.value}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
