"""Data model for an Item (GLOSSARY: 条目).

An Item is one discrete piece of content fetched from an information source.
Serialization lives here (to_dict/from_dict) so the field list is declared once.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime


@dataclass
class Item:
    source: str
    title: str
    link: str
    published: datetime
    summary: str
    content: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["published"] = self.published.isoformat()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Item":
        return cls(
            source=d["source"],
            title=d["title"],
            link=d["link"],
            published=datetime.fromisoformat(d["published"]),
            summary=d.get("summary", ""),
            content=d.get("content", ""),
        )
