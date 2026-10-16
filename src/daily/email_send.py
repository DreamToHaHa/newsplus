"""Build and send the digest email via SMTP, reusing mailpush config.

The mailpush tool (setup by the OpenClaw session) owns the SMTP credentials
and recipient list in ~/.openclaw-mailpush/config.json. This module reads that
same file so there is a single source of truth for SMTP + recipients — the
agent manages recipients through mailpush's conversation commands, and the
daily pipeline just consumes the config to send the HTML digest.
"""
from __future__ import annotations

import json
import logging
import smtplib
import ssl
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path

logger = logging.getLogger(__name__)

MAILPUSH_CONFIG_DEFAULT = Path("/home/<user>/.openclaw-mailpush/config.json")


def load_mailpush_config(config_path: Path) -> tuple[dict, list[str]]:
    """Read SMTP settings and enabled recipient emails from mailpush config.

    Returns (smtp_dict, recipient_email_list).
    """
    config_path = Path(config_path)
    data = json.loads(config_path.read_text(encoding="utf-8"))
    smtp = data["smtp"]
    recipients = [
        r["email"]
        for r in data.get("recipients", [])
        if r.get("enabled", True)
    ]
    return smtp, recipients


def build_html_message(
    *,
    subject: str,
    html: str,
    from_addr: str,
    from_name: str,
    to_addrs: list[str],
) -> MIMEMultipart:
    """Build a multipart/alternative message with an HTML part.

    A plain-text fallback is derived so mail clients without HTML render a
    readable version. Subject is wrapped to avoid header-injection via '<'.
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = formataddr((str(Header(from_name, "utf-8")), from_addr))
    msg["To"] = ", ".join(to_addrs)

    plain = _simple_text_from_html(html)
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    return msg


def _simple_text_from_html(html: str) -> str:
    """Strip tags to a rough plain-text fallback (best-effort)."""
    import re

    text = re.sub(r"<style.*?</style>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def send_digest_email(
    *,
    subject: str,
    html: str,
    config_path: Path = MAILPUSH_CONFIG_DEFAULT,
    timeout: int = 30,
) -> int:
    """Send the digest to all enabled recipients via SMTP.

    Returns 0 on success, non-zero on failure (and logs the cause). Raises
    FileNotFoundError when mailpush config is absent.
    """
    smtp, to_addrs = load_mailpush_config(config_path)
    if not to_addrs:
        logger.error("no enabled recipients in %s", config_path)
        print("ERROR no enabled recipients configured", flush=True)
        return 1

    msg = build_html_message(
        subject=subject,
        html=html,
        from_addr=smtp["user"],
        from_name=smtp.get("from_name", "OpenClaw"),
        to_addrs=to_addrs,
    )

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(
            smtp["host"], int(smtp["port"]), timeout=timeout, context=context
        ) as server:
            server.login(smtp["user"], smtp["password"])
            server.sendmail(smtp["user"], to_addrs, msg.as_string())
    except smtplib.SMTPAuthenticationError:
        logger.exception("SMTP auth failed")
        print("ERROR SMTP 认证失败", flush=True)
        return 1
    except smtplib.SMTPRecipientsRefused as exc:
        logger.exception("recipients refused")
        print(f"ERROR 收件人被拒: {exc}", flush=True)
        return 1
    except Exception as exc:
        logger.exception("SMTP send failed")
        print(f"ERROR SMTP 发送失败: {exc}", flush=True)
        return 1

    logger.info("sent digest to %d recipient(s)", len(to_addrs))
    return 0
