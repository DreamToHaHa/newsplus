"""User preferences (GLOSSARY: 用户决策) — structured filtering rules.

Preferences are the authoritative, machine-readable record of what the user
does and doesn't want pushed. They are stored as a JSON file
(data/preferences.json) that both the agent (via the preferences CLI) and the
daily pipeline read. USER.md may mirror them for the agent's own context, but
this file is the source of truth the filter applies.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


def _string_list(value) -> list[str]:
    """Coerce a loaded JSON value to a list of strings, dropping junk.

    Guards against a well-formed JSON file carrying the wrong shape (e.g.
    "keywords": "foo") degrading into a per-character list.
    """
    if isinstance(value, list):
        return [str(v) for v in value if isinstance(v, (str, int, float))]
    return []


@dataclass
class Preferences:
    blocked_keywords: list[str] = field(default_factory=list)  # subject blocklist
    disabled_sources: list[str] = field(default_factory=list)  # e.g. "thebatch"

    def matches_keyword(self, text: str) -> bool:
        """True when `text` contains any blocked keyword (case-insensitive)."""
        lowered = text.lower()
        return any(k.lower() in lowered for k in self.blocked_keywords)


def load_preferences(path: Path) -> Preferences:
    """Load preferences from a JSON file. Missing/corrupt file → empty defaults."""
    path = Path(path)
    if not path.exists():
        return Preferences()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return Preferences(
            blocked_keywords=_string_list(data.get("blocked_keywords")),
            disabled_sources=_string_list(data.get("disabled_sources")),
        )
    except (json.JSONDecodeError, OSError, AttributeError, TypeError):
        logger.exception("failed to load preferences from %s; using empty", path)
        return Preferences()


def save_preferences(prefs: Preferences, path: Path) -> None:
    """Persist preferences to a JSON file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(asdict(prefs), ensure_ascii=False, indent=2), encoding="utf-8"
    )
