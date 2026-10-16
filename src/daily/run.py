"""Daily pipeline entry: fetch → summarize → deliver the digest.

Delivery mode is chosen by --mode:
  email  (default) — build an HTML digest email and send it via SMTP using the
          mailpush config (~/.openclaw-mailpush/config.json). Email is the
          primary channel (chat channels carry length/quotas, ADR-0004).
  stdout — print the digest text to stdout for the legacy WeChat --announce
          path.

A per-source failure never blocks the digest — a failure alert rides along
after it, and failure details are persisted to a local log file.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from src.daily.digest import no_update_message
from src.daily.email_digest import build_html_digest
from src.daily.email_send import MAILPUSH_CONFIG_DEFAULT, send_digest_email
from src.daily.fetch import (
    DailyFetchReport,
    build_failure_alert,
    log_failures_to_file,
    run_daily_fetch,
)
from src.daily.filter import filter_items_for_push
from src.daily.preferences import load_preferences
from src.daily.summarize import (
    chunk_for_wechat,
    generate_overview,
    generate_per_item_commentary,
    summarize,
)
from src.fetchers.models import Item
from src.fetchers.sources import ALL_SOURCES

logger = logging.getLogger(__name__)

MAX_ITEMS_PER_SOURCE = 15


def load_provider_chain(
    openclaw_json: Path,
    providers_path: Path = Path("data/providers.json"),
) -> list[dict]:
    """Read OpenClaw's model chain (primary + fallbacks) as provider configs.

    The order (which provider wins, and the quota-fallback order) comes from
    OpenClaw's config, so switching the model in OpenClaw switches what
    newsplus uses — no code change. Endpoint + protocol come from OpenClaw's
    provider block too. The API key comes from newsplus's own
    data/providers.json (opencode-go keeps its key in OpenClaw's auth store,
    not the config file). A provider with no key is skipped (can't auth).
    """
    cfg = json.loads(openclaw_json.read_text(encoding="utf-8"))
    model_cfg = cfg.get("agents", {}).get("defaults", {}).get("model", {})
    refs = []
    if model_cfg.get("primary"):
        refs.append(model_cfg["primary"])
    refs.extend(model_cfg.get("fallbacks", []))

    providers = cfg.get("models", {}).get("providers", {})
    keys = {}
    if Path(providers_path).exists():
        keys = json.loads(Path(providers_path).read_text(encoding="utf-8")).get(
            "providers", {}
        )

    chain: list[dict] = []
    for ref in refs:
        provider, _, model = ref.partition("/")
        prov = providers.get(provider)
        if not prov:
            logger.warning("provider %r not configured; skipping %r", provider, ref)
            continue
        api_key = keys.get(provider, {}).get("api_key", "")
        if not api_key:
            logger.warning("no api_key for provider %r; skipping %r", provider, ref)
            continue
        entry = {
            "provider": provider,
            "model": model,
            "base_url": prov["baseUrl"],
            "api": prov.get("api", "openai-completions"),
            "api_key": api_key,
        }
        # Per-provider extra headers / session id from newsplus's own file
        # (e.g. opencode-go's x-opencode-session).
        extra = keys.get(provider, {})
        if extra.get("headers"):
            entry["headers"] = extra["headers"]
        if extra.get("session_id"):
            entry["session_id"] = extra["session_id"]
        chain.append(entry)
    return chain


def _recent_new_items(store_path: Path) -> list[Item]:
    """Items added in the last 36h — the ones the daily digest covers.

    The store keeps everything ever fetched; the digest should cover items
    fetched since the last run. We approximate by published/added recency,
    capped per source so a busy source (e.g. arXiv) can't flood the digest.
    """
    from datetime import datetime, timedelta, timezone

    from src.fetchers.store import JSONStore

    store = JSONStore(store_path)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=36)
    recent = [i for i in store.all_items() if i.published >= cutoff]
    by_source: dict[str, list[Item]] = {}
    for item in recent:
        by_source.setdefault(item.source, []).append(item)
    capped: list[Item] = []
    for source_items in by_source.values():
        source_items.sort(key=lambda i: i.published, reverse=True)
        capped.extend(source_items[:MAX_ITEMS_PER_SOURCE])
    return capped


def compose_delivery_text(
    *,
    report: DailyFetchReport,
    digest_text: str | None = None,
    no_update_note: str | None = None,
) -> list[str]:
    """Build the WeChat-chunked message body, alert appended last.

    `digest_text` (a generated digest) and `no_update_note` are mutually
    exclusive; exactly one is expected. The failure alert, when present, is
    appended as its own chunk so it is never split mid-content by chunking.
    """
    if digest_text is not None:
        chunks = chunk_for_wechat(digest_text)
    else:
        chunks = chunk_for_wechat(no_update_note or "")

    alert = build_failure_alert(report.failed_by_source)
    if alert:
        chunks.extend(chunk_for_wechat(f"\n\n{alert}"))
    return chunks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="newsplus daily pipeline")
    parser.add_argument("--store", default="data/items.json")
    parser.add_argument("--digest", default="data/digest.json")
    parser.add_argument("--failure-log", default="data/daily-errors.log")
    parser.add_argument("--preferences", default="data/preferences.json")
    parser.add_argument(
        "--openclaw-json",
        default=str(Path(os.path.expanduser("~")) / ".openclaw" / "openclaw.json"),
    )
    parser.add_argument("--mailpush-config", default=str(MAILPUSH_CONFIG_DEFAULT))
    parser.add_argument("--mode", choices=["email", "stdout"], default="email")
    parser.add_argument("--run-date", default=None, help="YYYY-MM-DD (defaults to today)")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    if args.verbose:
        logging.basicConfig(level=logging.INFO)

    from datetime import datetime

    run_date = args.run_date or datetime.now().strftime("%Y-%m-%d")
    store_path = Path(args.store)
    report = run_daily_fetch(sources=ALL_SOURCES, store_path=store_path, digest_path=Path(args.digest))
    log_failures_to_file(report, Path(args.failure_log))

    # Apply user preferences (GLOSSARY: 过滤) before summarizing — fetch stays
    # full; only the push view is filtered. A prefs load/filter failure is its
    # own error, not a summarize failure.
    try:
        prefs = load_preferences(Path(args.preferences))
        items = _recent_new_items(store_path)
        kept, filtered = filter_items_for_push(items, prefs)
    except Exception as exc:
        logger.exception("preferences/filter failed")
        print(f"ERROR preferences failed: {exc}", flush=True)
        return 3

    if filtered:
        logger.info("filtered %d items by preferences", len(filtered))

    # Build the digest subject line.
    subject = f"AI 源头日报 {run_date}"

    if report.no_update or not kept:
        return _deliver(
            mode=args.mode,
            subject=subject,
            title="今日无新增",
            html_body=build_html_digest([], run_date=run_date, title="今日无新增"),
            failure_alert=build_failure_alert(report.failed_by_source),
            no_update=True,
            mailpush_config=Path(args.mailpush_config),
        )

    # Generate content via OpenClaw's model chain (primary + fallbacks), so a
    # quota-exhausted provider falls through to the next automatically.
    try:
        chain = load_provider_chain(Path(args.openclaw_json))
        if args.mode == "email":
            # Email-first: a short overview + one Chinese commentary per item.
            overview = generate_overview(items=kept, run_date=run_date, chain=chain)
            commentary = generate_per_item_commentary(
                items=kept, run_date=run_date, chain=chain
            )
            html_body = build_html_digest(
                kept,
                run_date=run_date,
                title="AI 源头日报",
                overview=overview,
                commentary=commentary,
            )
        else:
            # Legacy stdout/WeChat: one continuous digest text.
            html_body = summarize(items=kept, run_date=run_date, chain=chain)
    except Exception as exc:
        logger.exception("summarize failed")
        print(f"ERROR summarize failed: {exc}", flush=True)
        return 3

    return _deliver(
        mode=args.mode,
        subject=subject,
        title="AI 源头日报",
        html_body=html_body,
        failure_alert=build_failure_alert(report.failed_by_source),
        no_update=False,
        mailpush_config=Path(args.mailpush_config),
    )


def _deliver(
    *,
    mode: str,
    subject: str,
    title: str,
    html_body: str,
    failure_alert: str,
    no_update: bool,
    mailpush_config: Path,
) -> int:
    """Deliver the digest via the chosen mode (email or stdout)."""
    if mode == "stdout":
        # Legacy WeChat --announce contract: machine line + text.
        if no_update:
            print("NONE", flush=True)
            print(no_update_message(), flush=True)
        else:
            print(f"NEW 0", flush=True)
            print(title, flush=True)
        if failure_alert:
            print("", flush=True)
            print(failure_alert, flush=True)
        return 0

    # Email mode: append failure alert into the HTML body when present.
    full_html = html_body
    if failure_alert:
        full_html = html_body.replace(
            "</body>", f"<hr><p style=\"color:#b00020\">{_esc(failure_alert)}</p></body>"
        )
    return send_digest_email(
        subject=subject,
        html=full_html,
        config_path=mailpush_config,
    )


def _esc(text: str) -> str:
    import html as _html

    return _html.escape(text or "")


if __name__ == "__main__":
    sys.exit(main())
