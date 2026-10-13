"""S14 seam: preferences CLI — add/remove keyword and source rules (agent-facing)."""
from src.daily.preferences_cli import add_keyword, remove_keyword, disable_source, enable_source


def test_add_keyword_roundtrip(tmp_path):
    path = tmp_path / "preferences.json"
    add_keyword(path, "强化学习")
    add_keyword(path, "LLM")
    from src.daily.preferences import load_preferences

    prefs = load_preferences(path)
    assert prefs.blocked_keywords == ["强化学习", "LLM"]


def test_add_keyword_dedupes(tmp_path):
    path = tmp_path / "preferences.json"
    add_keyword(path, "agents")
    add_keyword(path, "agents")
    from src.daily.preferences import load_preferences

    assert load_preferences(path).blocked_keywords == ["agents"]


def test_remove_keyword(tmp_path):
    path = tmp_path / "preferences.json"
    add_keyword(path, "agents")
    remove_keyword(path, "agents")
    from src.daily.preferences import load_preferences

    assert load_preferences(path).blocked_keywords == []


def test_remove_absent_keyword_is_noop(tmp_path):
    path = tmp_path / "preferences.json"
    remove_keyword(path, "nope")
    from src.daily.preferences import load_preferences

    assert load_preferences(path).blocked_keywords == []


def test_disable_and_enable_source(tmp_path):
    path = tmp_path / "preferences.json"
    disable_source(path, "thebatch")
    disable_source(path, "arxiv")
    from src.daily.preferences import load_preferences

    assert load_preferences(path).disabled_sources == ["thebatch", "arxiv"]
    enable_source(path, "thebatch")
    assert load_preferences(path).disabled_sources == ["arxiv"]


def test_disable_source_normalizes_display_name(tmp_path):
    # "The Batch" / "the batch" should map to canonical id "thebatch"
    path = tmp_path / "preferences.json"
    disable_source(path, "The Batch")
    disable_source(path, "hugging face")
    from src.daily.preferences import load_preferences

    prefs = load_preferences(path)
    assert "thebatch" in prefs.disabled_sources
    assert "huggingface" in prefs.disabled_sources


def test_cli_add_keyword_and_list(tmp_path, capsys):
    from src.daily.preferences_cli import main

    path = tmp_path / "preferences.json"
    assert main(["--preferences", str(path), "--action", "add-keyword", "--value", "agents"]) == 0
    assert main(["--preferences", str(path), "--action", "list"]) == 0
    out = capsys.readouterr().out
    assert "agents" in out


def test_cli_requires_value_for_mutating_actions(tmp_path, capsys):
    from src.daily.preferences_cli import main

    path = tmp_path / "preferences.json"
    assert main(["--preferences", str(path), "--action", "add-keyword"]) == 2
    out = capsys.readouterr().out
    assert "--value required" in out


def test_cli_disable_and_list_source(tmp_path, capsys):
    from src.daily.preferences_cli import main

    path = tmp_path / "preferences.json"
    main(["--preferences", str(path), "--action", "disable-source", "--value", "thebatch"])
    main(["--preferences", str(path), "--action", "list"])
    out = capsys.readouterr().out
    assert "thebatch" in out
