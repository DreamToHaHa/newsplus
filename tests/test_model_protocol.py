"""Protocol adapter: one call_model handles both OpenClaw api protocols, and
per-provider extra headers (opencode-go needs x-opencode-session)."""
from src.daily.summarize import build_request


def test_completions_protocol_builds_chat_completions():
    cfg = {
        "api": "openai-completions",
        "base_url": "https://opencode.ai/zen/go/v1",
        "api_key": "oc",
        "model": "m1",
    }
    url, headers, payload = build_request(cfg, "hello")
    assert url == "https://opencode.ai/zen/go/v1/chat/completions"
    assert headers["Authorization"] == "Bearer oc"
    assert payload["model"] == "m1"
    assert payload["messages"][-1] == {"role": "user", "content": "hello"}


def test_responses_protocol_builds_responses_endpoint():
    cfg = {
        "api": "openai-responses",
        "base_url": "https://ark.cn-beijing.volces.com/api/plan/v3",
        "api_key": "ark",
        "model": "m2",
    }
    url, headers, payload = build_request(cfg, "hello")
    assert url == "https://ark.cn-beijing.volces.com/api/plan/v3/responses"
    assert headers["Authorization"] == "Bearer ark"
    assert payload["model"] == "m2"
    assert "input" in payload
    assert "messages" not in payload


def test_extra_headers_merged_into_request():
    cfg = {
        "api": "openai-completions",
        "base_url": "https://opencode.ai/zen/go/v1",
        "api_key": "oc",
        "model": "m1",
        "headers": {"x-opencode-session": "newsplus-abc"},
    }
    url, headers, payload = build_request(cfg, "hello")
    assert headers["x-opencode-session"] == "newsplus-abc"
    assert headers["Authorization"] == "Bearer oc"


def test_session_header_autoinjected_when_configured():
    # When a provider sets a session header name, build_request fills a stable
    # value so callers don't have to.
    cfg = {
        "api": "openai-completions",
        "base_url": "https://opencode.ai/zen/go/v1",
        "api_key": "oc",
        "model": "m1",
        "headers": {"x-opencode-session": "$SESSION"},
        "session_id": "newsplus-sess-1",
    }
    _url, headers, _payload = build_request(cfg, "hello")
    assert headers["x-opencode-session"] == "newsplus-sess-1"
