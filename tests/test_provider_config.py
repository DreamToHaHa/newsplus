"""Q3 seam: newsplus follows OpenClaw's model chain (primary + fallbacks)
while keeping provider credentials in its own data/providers.json.

Model order (which provider is tried first, and the quota fallback order)
comes from OpenClaw's config so switching the model there is enough. The API
key is NOT read from OpenClaw (opencode-go stores it in OpenClaw's auth store,
not in the config file); newsplus keeps its own copy in data/providers.json.
"""
import json

from src.daily.run import load_provider_chain


def _write_openclaw(path, *, primary, fallbacks, providers):
    cfg = {
        "agents": {"defaults": {"model": {"primary": primary, "fallbacks": fallbacks}}},
        "models": {"providers": providers},
    }
    path.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")


def _write_providers(path, providers):
    path.write_text(json.dumps({"providers": providers}, ensure_ascii=False), encoding="utf-8")


_OPENCLAW_PROVIDERS = {
    "opencode-go": {"baseUrl": "https://opencode.ai/zen/go/v1", "api": "openai-completions"},
    "volcengine-agent-plan": {
        "baseUrl": "https://ark.cn-beijing.volces.com/api/plan/v3",
        "api": "openai-responses",
    },
}
_KEYS = {
    "opencode-go": {"api_key": "oc_test"},
    "volcengine-agent-plan": {"api_key": "ark_test"},
}


def test_chain_order_from_openclaw_keys_from_providers_file(tmp_path):
    oc = tmp_path / "openclaw.json"
    pf = tmp_path / "providers.json"
    _write_openclaw(
        oc,
        primary="opencode-go/deepseek-v4.1-flash",
        fallbacks=["volcengine-agent-plan/ark-code-latest"],
        providers=_OPENCLAW_PROVIDERS,
    )
    _write_providers(pf, _KEYS)
    chain = load_provider_chain(oc, providers_path=pf)
    assert [c["provider"] for c in chain] == ["opencode-go", "volcengine-agent-plan"]
    assert [c["model"] for c in chain] == ["deepseek-v4.1-flash", "ark-code-latest"]
    assert chain[0]["api"] == "openai-completions"
    assert chain[0]["api_key"] == "oc_test"
    assert chain[1]["api"] == "openai-responses"
    assert chain[1]["api_key"] == "ark_test"


def test_chain_follows_openclaw_model_switch(tmp_path):
    oc = tmp_path / "openclaw.json"
    pf = tmp_path / "providers.json"
    _write_providers(pf, _KEYS)
    _write_openclaw(
        oc, primary="opencode-go/m", fallbacks=[], providers=_OPENCLAW_PROVIDERS
    )
    assert load_provider_chain(oc, providers_path=pf)[0]["provider"] == "opencode-go"
    # User switches primary in OpenClaw — order follows, no code change.
    _write_openclaw(
        oc, primary="volcengine-agent-plan/m", fallbacks=[], providers=_OPENCLAW_PROVIDERS
    )
    assert load_provider_chain(oc, providers_path=pf)[0]["provider"] == "volcengine-agent-plan"


def test_chain_skips_provider_without_key(tmp_path):
    oc = tmp_path / "openclaw.json"
    pf = tmp_path / "providers.json"
    _write_openclaw(
        oc,
        primary="opencode-go/m",
        fallbacks=["volcengine-agent-plan/m2"],
        providers=_OPENCLAW_PROVIDERS,
    )
    # Only opencode-go has a key → volcengine entry is skipped (can't auth).
    _write_providers(pf, {"opencode-go": {"api_key": "oc_test"}})
    chain = load_provider_chain(oc, providers_path=pf)
    assert [c["provider"] for c in chain] == ["opencode-go"]
