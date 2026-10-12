"""Multi-source orchestration: run_all fetches every source, isolating failures."""
from pathlib import Path

from src.fetchers.pipeline import RunResult
from src.fetchers.run_all import run_all_sources
from src.fetchers.smolai import parse_smolai_rss
from src.fetchers.arxiv import parse_arxiv_list
from src.fetchers.hf_papers import parse_hf_papers
from src.fetchers.thebatch import parse_thebatch_issue
from src.fetchers.alphaxiv import parse_alphaxiv

FIXTURES = Path(__file__).parent / "fixtures"


def _all_parsers():
    """Real parsers + fixture-based fetchers, so the test needs no network."""
    fetchers = {
        "smol.ai": (lambda: (FIXTURES / "smolai.rss").read_bytes(), parse_smolai_rss),
        "arxiv": (lambda: (FIXTURES / "arxiv_csai.html").read_bytes(), parse_arxiv_list),
        "huggingface": (lambda: (FIXTURES / "hf_papers.html").read_bytes(), parse_hf_papers),
        "thebatch": (lambda: (FIXTURES / "thebatch_issue.html").read_bytes(), parse_thebatch_issue),
        "alphaxiv": (lambda: (FIXTURES / "alphaxiv.html").read_bytes(), parse_alphaxiv),
    }
    return fetchers


def test_run_all_reports_each_source(tmp_path):
    results = run_all_sources(
        sources=_all_parsers(),
        store_path=tmp_path / "items.json",
    )
    assert isinstance(results, list)
    assert len(results) == 5
    by_source = {r.source: r for r in results}
    assert set(by_source) == {"smol.ai", "arxiv", "huggingface", "thebatch", "alphaxiv"}
    assert all(r.status == "ok" for r in results)
    assert sum(r.added for r in results) > 700


def test_run_all_isolates_failing_source(tmp_path):
    def broken(_b: bytes):
        raise ValueError("boom")

    sources = _all_parsers()
    sources["arxiv"] = (lambda: b"<html/>", broken)
    results = run_all_sources(sources=sources, store_path=tmp_path / "items.json")
    by_source = {r.source: r for r in results}
    assert by_source["arxiv"].status == "error"
    assert "boom" in by_source["arxiv"].error
    # The other four still succeed
    assert by_source["smol.ai"].status == "ok"
    assert by_source["thebatch"].status == "ok"
    assert sum(r.status == "ok" for r in results) == 4
