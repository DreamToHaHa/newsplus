"""Digest assembly: turn new Items into the text sent to the summary model.

The digest input groups items by source so the model can summarize per
section. The model adds Chinese commentary; this module only structures the
input and the "no update" note.
"""
from __future__ import annotations

from collections import OrderedDict

from src.fetchers.models import Item


def no_update_message() -> str:
    """The note pushed when a run found no new items (GLOSSARY: 无新增)."""
    return "📭 今日 AI 源头无新增内容，平台运行正常。"


def build_digest_input(items: list[Item]) -> str:
    """Group items by source into the prompt input for the summary model.

    Empty input returns empty string (caller decides on no_update).
    """
    by_source: OrderedDict[str, list[Item]] = OrderedDict()
    for item in items:
        by_source.setdefault(item.source, []).append(item)

    sections: list[str] = []
    for source, source_items in by_source.items():
        lines = [f"# {source}"]
        for it in source_items:
            lines.append(f"- **{it.title}**")
            lines.append(f"  链接: {it.link}")
            if it.content:
                lines.append(f"  正文: {it.content}")
        sections.append("\n".join(lines))

    return "\n\n".join(sections)
