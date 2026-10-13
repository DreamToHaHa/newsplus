"""S8 seam: daily fetch CLI — run all sources, report new items + no-update state."""
from pathlib import Path

from src.daily.fetch import run_daily_fetch
from src.fetchers.sources import ALL_SOURCES

FIXTURES = Path(__file__).parent / "fixtures"


def _fixture_sources():
    """Fixture-based sources (no network) for deterministic tests."""
    from src.fetchers.smolai import parse_smolai_rss

    return {
        "smol.ai": (lambda: (FIXTURES / "smolai.rss").read_bytes(), parse_smolai_rss),
    }


def test_daily_fetch_reports_new_items(tmp_path):
    report = run_daily_fetch(sources=_fixture_sources(), store_path=tmp_path / "items.json")
    assert report.no_update is False
    assert report.new_count == 716
    assert report.failed_sources == []


def test_daily_fetch_second_run_reports_no_update(tmp_path):
    sources = _fixture_sources()
    store_path = tmp_path / "items.json"
    run_daily_fetch(sources=sources, store_path=store_path)
    report2 = run_daily_fetch(sources=sources, store_path=store_path)
    assert report2.no_update is True
    assert report2.new_count == 0


def test_daily_fetch_isolates_failed_source(tmp_path):
    def broken(_b: bytes):
        raise ValueError("boom")

    sources = {
        "smol.ai": (lambda: (FIXTURES / "smolai.rss").read_bytes(), __import__("src.fetchers.smolai", fromlist=["parse_smolai_rss"]).parse_smolai_rss),
        "arxiv": (lambda: b"<html/>", broken),
    }
    report = run_daily_fetch(sources=sources, store_path=tmp_path / "items.json")
    assert report.no_update is False
    assert report.failed_sources == ["arxiv"]
    assert report.new_count == 716
