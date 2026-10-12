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


def summarize(
    *,
    items: list[Item],
    run_date: str,
    base_url: str,
    api_key: str,
    model: str = "deepseek-v4.1-flash",
    timeout: int = 120,
) -> str:
    """Call the Volcano model to produce the digest text.

    Uses the openai-responses protocol against the volcengine-agent-plan
    endpoint. Raises on HTTP or protocol errors so the caller can surface them.
    """
    prompt = build_summary_prompt(items, run_date)
    if not prompt:
        return ""

    url = f"{base_url}/chat/completions" if not base_url.endswith("/chat/completions") else base_url
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": _SUMMARY_SYSTEM},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 8192,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    logger.info("calling summary model %s at %s", model, base_url)
    resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError(f"unexpected model response shape: {data}") from exc
