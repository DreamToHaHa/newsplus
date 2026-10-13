"""T8 seam: per-source failure reporting, alert composition, delivery wiring,
and failure log persistence — none of which block the digest push.
"""
from pathlib import Path

from src.daily.fetch import (
    build_failure_alert,
    log_failures_to_file,
    run_daily_fetch,
)
from src.daily.run import compose_delivery_text
from src.daily.digest import no_update_message
from src.fetchers.smolai import parse_smolai_rss

FIXTURES = Path(__file__).parent / "fixtures"


def test_report_includes_failure_reason(tmp_path):
    def broken(_b: bytes):
        raise ValueError("boom in parser")

    sources = {
        "smol.ai": (lambda: (FIXTURES / "smolai.rss").read_bytes(), parse_smolai_rss),
        "arxiv": (lambda: b"<html/>", broken),
    }
    report = run_daily_fetch(sources=sources, store_path=tmp_path / "items.json")
    assert report.failed_sources == ["arxiv"]
    assert "arxiv" in report.failed_by_source
    assert "boom in parser" in report.failed_by_source["arxiv"]


def test_no_failure_when_all_ok(tmp_path):
    sources = {
        "smol.ai": (lambda: (FIXTURES / "smolai.rss").read_bytes(), parse_smolai_rss),
    }
    report = run_daily_fetch(sources=sources, store_path=tmp_path / "items.json")
    assert report.failed_sources == []
    assert report.failed_by_source == {}


def test_failure_alert_empty_when_clean():
    assert build_failure_alert({}) == ""


def test_failure_alert_lists_source_and_reason():
    alert = build_failure_alert({"arxiv": "connection refused"})
    assert "arxiv" in alert
    assert "connection refused" in alert
    assert "抓取失败" in alert


def _report(failed_by_source: dict[str, str]) -> "object":
    from src.daily.fetch import DailyFetchReport

    return DailyFetchReport(new_count=0, no_update=True, failed_by_source=failed_by_source)


def test_compose_digest_with_alert_appends_alert_last():
    report = _report({"arxiv": "boom"})
    chunks = compose_delivery_text(report=report, digest_text="# 日报\n\n正文内容")
    assert chunks[-1].endswith("boom")
    # Alert is its own chunk, not split mid-content by digest chunking
    assert "抓取失败" in chunks[-1]


def test_compose_no_update_with_alert_keeps_note_then_alert():
    report = _report({"arxiv": "boom"})
    chunks = compose_delivery_text(report=report, no_update_note=no_update_message())
    assert "无新增" in chunks[0]
    assert "arxiv" in chunks[-1]


def test_compose_clean_run_no_alert():
    report = _report({})
    chunks = compose_delivery_text(report=report, digest_text="# 日报")
    assert len(chunks) == 1
    assert "抓取失败" not in chunks[0]


def test_log_failures_to_file_writes_timestamped_rows(tmp_path):
    log_path = tmp_path / "daily-errors.log"
    log_failures_to_file(_report({"arxiv": "boom", "hf": "timeout"}), log_path)
    content = log_path.read_text(encoding="utf-8")
    assert "source=arxiv" in content
    assert "error=boom" in content
    assert "source=hf" in content
    assert "error=timeout" in content


def test_log_failures_clean_run_writes_nothing(tmp_path):
    log_path = tmp_path / "daily-errors.log"
    log_failures_to_file(_report({}), log_path)
    assert not log_path.exists()
