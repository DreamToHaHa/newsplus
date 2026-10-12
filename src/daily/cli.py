"""Daily CLI entry point, invoked by OpenClaw's cron (T6).

Usage:
    python -m src.daily.cli [--store data/items.json] [--digest data/digest.json]

Runs the fetch layer, exports the full item set, and prints a status line to
stdout. OpenClaw's command payload captures stdout and routes it (via a
standing order / automation) to the WeChat channel.

stdout contract:
    NEW <count> — new items were found; the summary step should read the digest
    NONE — no new items; push the no-update note
    ERROR <detail> — the run failed
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from src.daily.fetch import run_daily_fetch
from src.fetchers.sources import ALL_SOURCES


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="newsplus daily fetch")
    parser.add_argument("--store", default="data/items.json", help="item store path")
    parser.add_argument("--digest", default="data/digest.json", help="digest export path")
    parser.add_argument("-v", "--verbose", action="store_true", help="enable logging")
    args = parser.parse_args(argv)

    if args.verbose:
        logging.basicConfig(level=logging.INFO)

    store_path = Path(args.store)
    digest_path = Path(args.digest)

    try:
        report = run_daily_fetch(
            sources=ALL_SOURCES,
            store_path=store_path,
            digest_path=digest_path,
        )
    except Exception as exc:
        print(f"ERROR {exc}", flush=True)
        return 1

    if report.failed_sources:
        print(f"ERROR sources failed: {', '.join(report.failed_sources)}", flush=True)
        return 2

    if report.no_update:
        print("NONE", flush=True)
    else:
        print(f"NEW {report.new_count}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
