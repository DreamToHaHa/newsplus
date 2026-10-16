"""Build the HTML body of the daily digest email.

The email format is the primary delivery channel (ADR-0004 precedent: chat
channels carry length/quotas). HTML lets each source render as its own
section with clickable links and readable summaries — no chunking needed.
"""
from __future__ import annotations

import html as html_lib
from collections import OrderedDict

from src.fetchers.models import Item


def _esc(text: str) -> str:
    return html_lib.escape(text or "")


def build_html_digest(
    items: list[Item],
    *,
    run_date: str,
    title: str,
    overview: str | None = None,
    commentary: dict[str, str] | None = None,
) -> str:
    """Return a self-contained HTML document for the daily digest.

    Layout (email-first, no chat length limits):
      - optional overview block at the top (model's 2-3 sentence summary)
      - items grouped by source; the source name is a bold section header
      - each item is a card: title / Chinese commentary (or item summary) /
        clickable link, each on its own line.

    An empty item list renders a "no new items" note.
    """
    commentary = commentary or {}
    sections: list[str] = []

    if overview and "http" not in overview.lower():
        # Render each line of the overview as its own paragraph so the model's
        # per-point output reads as separate lines. An overview containing a
        # URL means the model went off-script (listed items); drop it rather
        # than let garbage into the mail.
        overview_lines = [ln.strip() for ln in overview.splitlines() if ln.strip()]
        if not overview_lines:
            overview_lines = [overview.strip()]
        points = "".join(f"<p style=\"margin:4px 0;\">{_esc(ln)}</p>" for ln in overview_lines)
        sections.append(
            f'<div style="background:#f8f9fa;border-left:4px solid #1a73e8;'
            f'padding:12px 14px;border-radius:4px;margin-bottom:16px;color:#333;">'
            f"<strong>今日要点</strong>{points}</div>"
        )

    by_source: OrderedDict[str, list[Item]] = OrderedDict()
    for item in items:
        by_source.setdefault(item.source, []).append(item)
    if not by_source:
        sections.append("<p>📭 今日 AI 源头无新增内容，平台运行正常。</p>")

    for source, source_items in by_source.items():
        blocks = []
        for it in source_items:
            note = commentary.get(it.title) or it.summary or it.content[:400] or "（无摘要）"
            blocks.append(
                '<div style="margin:12px 0;padding:10px 12px;'
                'border:1px solid #eee;border-radius:6px;">'
                f'<div style="font-size:13px;color:#1a73e8;font-weight:700;">'
                f"■ {_esc(source)}</div>"
                f'<div style="font-size:15px;font-weight:600;margin:6px 0 4px 0;">'
                f"{_esc(it.title)}</div>"
                f'<div style="font-size:13px;color:#444;margin:2px 0;">{_esc(note)}</div>'
                f'<div style="font-size:13px;margin:2px 0 0 0;">'
                f'<a href="{_esc(it.link)}" style="color:#1a73e8;">{_esc(it.link)}</a></div>'
                "</div>"
            )
        sections.append(
            f'<div style="margin-top:20px;font-size:16px;font-weight:700;'
            f'color:#222;border-bottom:2px solid #1a73e8;padding-bottom:4px;">'
            f"# {_esc(source)}（{len(source_items)}）</div>{''.join(blocks)}"
        )

    body = "\n".join(sections)
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>{_esc(title)} · {_esc(run_date)}</title></head>
<body style="font-family:-apple-system,'Segoe UI',Arial,sans-serif;max-width:720px;margin:0 auto;padding:16px;color:#222;">
<h1 style="font-size:22px;">{_esc(title)} · {_esc(run_date)}</h1>
{body}
<hr style="border:none;border-top:1px solid #eee;margin-top:24px;">
<p style="color:#999;font-size:12px;">由 newsplus 自动生成 · {_esc(run_date)}</p>
</body></html>"""
