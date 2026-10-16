"""S16/S17 seams: build and send the digest email, reading mailpush config."""
import json

from src.daily.email_send import (
    build_html_message,
    load_mailpush_config,
    MAILPUSH_CONFIG_DEFAULT,
)


def _write_config(path, *, smtp=None, recipients=None):
    data = {
        "smtp": smtp or {
            "host": "smtp.example.com",
            "port": 465,
            "user": "sender@example.com",
            "password": "secret",
            "from_name": "Test",
        },
        "recipients": recipients
        or [{"email": "jimy@example.com", "name": "Jimy", "enabled": True}],
    }
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_default_config_path():
    parts = MAILPUSH_CONFIG_DEFAULT.parts
    assert ".openclaw-mailpush" in parts
    assert parts[-1] == "config.json"


def test_load_mailpush_config_reads_smtp_and_recipients(tmp_path):
    cfg_path = tmp_path / "config.json"
    _write_config(cfg_path)
    smtp, recipients = load_mailpush_config(cfg_path)
    assert smtp["user"] == "sender@example.com"
    assert recipients == ["jimy@example.com"]


def test_load_mailpush_config_skips_disabled_recipients(tmp_path):
    cfg_path = tmp_path / "config.json"
    _write_config(
        cfg_path,
        recipients=[
            {"email": "a@example.com", "name": "A", "enabled": True},
            {"email": "b@example.com", "name": "B", "enabled": False},
        ],
    )
    smtp, recipients = load_mailpush_config(cfg_path)
    assert recipients == ["a@example.com"]


def test_load_missing_config_raises_clear_error(tmp_path):
    import pytest

    with pytest.raises(FileNotFoundError):
        load_mailpush_config(tmp_path / "nope.json")


def test_build_html_message_is_mime_html():
    msg = build_html_message(
        subject="AI 源头日报 2026-10-13",
        html="<html><body><p>hi</p></body></html>",
        from_addr="sender@example.com",
        from_name="Test",
        to_addrs=["jimy@example.com"],
    )
    assert str(msg["Subject"]) == "AI 源头日报 2026-10-13"
    assert msg["From"] == "Test <sender@example.com>"
    assert msg["To"] == "jimy@example.com"
    # multipart/alternative carrying a text/html part whose payload decodes
    # back to the original HTML (body is transfer-encoded, not literal).
    html_part = next(p for p in msg.get_payload() if p.get_content_type() == "text/html")
    assert "hi" in html_part.get_payload(decode=True).decode("utf-8")


def test_build_html_message_handles_html_subject():
    # A subject containing angle brackets must not break the header; Header
    # wraps it so the literal '<b>' never appears raw in the header line.
    msg = build_html_message(
        subject="<b>alert</b>",
        html="<p>body</p>",
        from_addr="s@e.com",
        from_name="N",
        to_addrs=["a@b.com"],
    )
    header_line = [ln for ln in msg.as_string().splitlines() if ln.startswith("Subject:")][0]
    assert "<b>alert</b>" not in header_line
