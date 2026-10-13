"""S12 seam: Preferences model — keyword blocklist + source switches, JSON persistence."""
import json

from src.daily.preferences import Preferences, load_preferences, save_preferences


def test_default_preferences_empty():
    p = Preferences()
    assert p.blocked_keywords == []
    assert p.disabled_sources == []


def test_roundtrip_via_save_and_load(tmp_path):
    path = tmp_path / "preferences.json"
    p = Preferences(blocked_keywords=["强化学习"], disabled_sources=["thebatch"])
    save_preferences(p, path)
    loaded = load_preferences(path)
    assert loaded.blocked_keywords == ["强化学习"]
    assert loaded.disabled_sources == ["thebatch"]


def test_load_missing_file_returns_empty(tmp_path):
    loaded = load_preferences(tmp_path / "nope.json")
    assert loaded.blocked_keywords == []
    assert loaded.disabled_sources == []


def test_save_writes_stable_json_shape(tmp_path):
    path = tmp_path / "preferences.json"
    save_preferences(Preferences(blocked_keywords=["LLM"], disabled_sources=["arxiv"]), path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["blocked_keywords"] == ["LLM"]
    assert data["disabled_sources"] == ["arxiv"]


def test_load_corrupted_file_returns_empty(tmp_path):
    path = tmp_path / "preferences.json"
    path.write_text("{ not valid json", encoding="utf-8")
    loaded = load_preferences(path)
    assert loaded.blocked_keywords == []
    assert loaded.disabled_sources == []


def test_load_wrong_shape_returns_string_list(tmp_path):
    path = tmp_path / "preferences.json"
    path.write_text('{"blocked_keywords": "foo", "disabled_sources": 42}', encoding="utf-8")
    loaded = load_preferences(path)
    # Wrong-shape values degrade to empty lists, never per-char lists
    assert loaded.blocked_keywords == []
    assert loaded.disabled_sources == []
