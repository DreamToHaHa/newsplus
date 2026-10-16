"""Summarize new Items into a WeChat-ready digest via the Volcano model.

The script path keeps the pipeline deterministic and testable: it builds a
prompt from new items, calls the configured Volcano model (openai-responses
protocol), and returns the digest text. Chunking handles WeChat's per-message
length limit.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import requests

from src.fetchers.models import Item

logger = logging.getLogger(__name__)

WECHAT_CHUNK_LIMIT = 3800  # conservative under WeChat's ~4000 char limit

# System prompt for the summary model.
_SUMMARY_SYSTEM = (
    "你是一个 AI 行业资讯编辑。将给定条目整理成微信日报：按信息源分节，"
    "每条包含英文标题、中文一句话点评、原文链接。正文较长的条目保留要点即可。"
    "只输出日报正文，不要额外说明。"
)


def build_summary_prompt(items: list[Item], run_date: str) -> str:
    """Build the user prompt for the summary model from new items."""
    if not items:
        return ""
    from src.daily.digest import build_digest_input

    sections = build_digest_input(items)
    return (
        f"日期：{run_date}\n"
        f"以下是今日各信息源的新增条目：\n\n{sections}\n\n"
        "请生成日报，按源分节。"
    )


def parse_commentary_lines(text: str) -> dict[str, str]:
    """Parse "标题::点评" lines into {title: commentary}.

    Malformed lines (no separator) are skipped so a stray model line can't
    corrupt the mapping.
    """
    result: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if "::" not in line:
            continue
        title, _, comment = line.partition("::")
        title = title.strip()
        comment = comment.strip()
        if title and comment:
            result[title] = comment
    return result


def generate_overview(
    *,
    items: list[Item],
    run_date: str,
    chain: list[dict],
    timeout: int = 120,
) -> str:
    """Ask the model for a 2-3 sentence overview of today's items.

    The item titles (with source) are included so the model can actually
    reason about what happened today, not just count items.
    """
    titles = "\n".join(f"- {it.title}" for it in items)
    prompt = (
        f"今天是 {run_date}。以下是今日 AI 相关资讯标题：\n{titles}\n\n"
        "只写一段不超过 60 字的中文总结，说明今天的整体趋势。"
        "禁止列出任何标题、禁止出现任何链接、禁止复述条目、不要编号。"
    )
    return call_model_chain(chain, prompt, timeout=timeout)


def generate_per_item_commentary(
    *,
    items: list[Item],
    run_date: str,
    chain: list[dict],
    timeout: int = 120,
) -> dict[str, str]:
    """Ask the model for one Chinese one-line commentary per item.

    Expects the model to reply as "标题::点评" lines, one per item, using the
    item's exact title. Returns {title: commentary}; missing items are simply
    absent (caller falls back to the item summary).
    """
    lines = []
    for it in items:
        lines.append(f"- {it.title}  （来源 {it.source}）")
    prompt = (
        f"日期：{run_date}\n"
        f"请为以下每条 AI 资讯写一句中文点评。严格每行输出一个条目，格式："
        f"「原始标题::中文点评」。不要编号、不要 markdown、不要链接、不要额外说明。"
        f"标题必须与给定标题完全一致。\n\n{chr(10).join(lines)}"
    )
    raw = call_model_chain(chain, prompt, timeout=timeout)
    return parse_commentary_lines(raw)


def chunk_for_wechat(text: str) -> list[str]:
    """Split text into WeChat-sized chunks, preferring paragraph boundaries.

    Returns a list of strings; each is at most WECHAT_CHUNK_LIMIT chars.
    """
    if len(text) <= WECHAT_CHUNK_LIMIT:
        return [text]

    chunks: list[str] = []
    paragraphs = text.split("\n\n")
    current = ""
    for para in paragraphs:
        candidate = f"{current}\n\n{para}".strip() if current else para
        if len(candidate) <= WECHAT_CHUNK_LIMIT:
            current = candidate
        else:
            if current:
                chunks.append(current)
            # A single paragraph longer than the limit gets hard-split.
            current = ""
            while len(para) > WECHAT_CHUNK_LIMIT:
                chunks.append(para[:WECHAT_CHUNK_LIMIT])
                para = para[WECHAT_CHUNK_LIMIT:]
            current = para
    if current:
        chunks.append(current)
    return chunks


def build_request(cfg: dict, prompt: str) -> tuple[str, dict, dict]:
    """Build (url, headers, payload) for a provider, routed by its api protocol.

    `openai-completions` → POST {base}/chat/completions  {model, messages}
    `openai-responses`   → POST {base}/responses         {model, input}
    """
    api = cfg.get("api", "openai-completions")
    base = cfg["base_url"].rstrip("/")
    headers = {
        "Authorization": f"Bearer {cfg['api_key']}",
        "Content-Type": "application/json",
    }
    # Per-provider extra headers (e.g. opencode-go needs x-opencode-session).
    # "$SESSION" is filled with a stable session id when the caller provides one.
    for key, val in (cfg.get("headers") or {}).items():
        if val == "$SESSION":
            val = cfg.get("session_id") or "newsplus"
        headers[key] = val
    if api == "openai-responses":
        url = f"{base}/responses"
        payload = {
            "model": cfg["model"],
            "instructions": _SUMMARY_SYSTEM,
            "input": prompt,
            "max_output_tokens": 8192,
        }
    else:  # openai-completions (also the default)
        url = f"{base}/chat/completions"
        payload = {
            "model": cfg["model"],
            "messages": [
                {"role": "system", "content": _SUMMARY_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 8192,
        }
    return url, headers, payload


def _extract_text(data: dict) -> str:
    """Pull the assistant text out of either protocol's response body."""
    # openai-completions shape
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        pass
    # openai-responses shape: output[].content[].text
    try:
        parts = []
        for out in data["output"]:
            for c in out.get("content", []):
                if c.get("type") in ("output_text", "text") and c.get("text"):
                    parts.append(c["text"])
        if parts:
            return "".join(parts)
    except (KeyError, IndexError, TypeError):
        pass
    raise ValueError(f"unexpected model response shape: {data}")


def call_model(cfg: dict, prompt: str, timeout: int = 120) -> str:
    """Call a provider (single chain entry) and return its text content."""
    url, headers, payload = build_request(cfg, prompt)
    logger.info("calling %s model %s at %s", cfg.get("api"), cfg.get("model"), url)
    resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return _extract_text(resp.json())


def call_model_chain(chain: list[dict], prompt: str, timeout: int = 120) -> str:
    """Try each provider in the chain in order; return the first success.

    A provider error (including a quota-exhausted response) falls through to
    the next entry. Raises the last error only when all fail.
    """
    last_exc: Exception | None = None
    for cfg in chain:
        try:
            return call_model(cfg, prompt, timeout=timeout)
        except Exception as exc:  # noqa: BLE001 - try the next provider
            logger.warning(
                "provider %s/%s failed (%s); trying next",
                cfg.get("provider"), cfg.get("model"), exc,
            )
            last_exc = exc
    raise last_exc if last_exc else RuntimeError("empty provider chain")




def summarize(
    *,
    items: list[Item],
    run_date: str,
    chain: list[dict],
    timeout: int = 120,
) -> str:
    """Produce a single continuous digest text (legacy stdout/WeChat mode)."""
    prompt = build_summary_prompt(items, run_date)
    if not prompt:
        return ""
    return call_model_chain(chain, prompt, timeout=timeout)
