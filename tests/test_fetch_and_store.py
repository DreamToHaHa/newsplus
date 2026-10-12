"""S3 seam: fetch_and_store orchestrates fetch → parse → store, reports stats.

Both fetcher and parser are injected functions: the seam is the pipeline
itself, and adding a new source (T5) means supplying its own fetcher/parser
without touching this module.
"""
import json
from pathlib import Path

from src.fetchers.pipeline import export_items_json, fetch_and_store
from src.fetchers.smolai import parse_smolai_rss
from src.fetchers.store import JSONStore

FIXTURE = Path(__file__).parent / "fixtures" / "smolai.rss"


def test_fetch_and_store_reports_added(tmp_path):
    store = JSONStore(tmp_path / "items.json")
    result = fetch_and_store(
        fetcher=lambda: FIXTURE.read_bytes(),
        parser=parse_smolai_rss,
        store=store,
    )
    assert result.status == "ok"
    assert result.added == 716
    assert result.duplicate == 0
    assert result.source == "smol.ai"


def test_fetch_and_store_deduplicates_on_second_run(tmp_path):
    store = JSONStore(tmp_path / "items.json")
    fetch_and_store(
        fetcher=lambda: FIXTURE.read_bytes(),
        parser=parse_smolai_rss,
        store=store,
    )
    result2 = fetch_and_store(
        fetcher=lambda: FIXTURE.read_bytes(),
        parser=parse_smolai_rss,
        store=store,
    )
    assert result2.added == 0
    assert result2.duplicate == 716


def test_fetch_and_store_handles_fetch_failure(tmp_path):
    def broken_fetcher() -> bytes:
        raise OSError("network down")

    store = JSONStore(tmp_path / "items.json")
    result = fetch_and_store(
        fetcher=broken_fetcher,
        parser=parse_smolai_rss,
        store=store,
    )
    assert result.status == "error"
    assert result.error == "network down"


def test_fetch_and_store_handles_parse_failure(tmp_path):
    def bad_parser(_data: bytes):
        raise ValueError("cannot parse this feed")

    store = JSONStore(tmp_path / "items.json")
    result = fetch_and_store(
        fetcher=lambda: b"whatever",
        parser=bad_parser,
        store=store,
    )
    assert result.status == "error"
    assert "cannot parse this feed" in result.error


def test_export_items_json_produces_consumable_file(tmp_path):
    store = JSONStore(tmp_path / "items.json")
    fetch_and_store(
        fetcher=lambda: FIXTURE.read_bytes(),
        parser=parse_smolai_rss,
        store=store,
    )
    out = tmp_path / "digest.json"
    export_items_json(store.all_items(), out)
    with out.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    assert len(data) == 716
    assert data[0]["title"] == "not much happened today"
    assert data[0]["link"] == "https://news.smol.ai/issues/26-09-09-not-much/"
    assert "published" in data[0]
