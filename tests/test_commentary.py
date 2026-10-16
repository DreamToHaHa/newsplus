"""Commentary seams: overview + per-item Chinese commentary parsing."""
from src.daily.summarize import parse_commentary_lines


def test_parse_commentary_lines_standard():
    text = "标题A::这是点评A\n标题B::这是点评B"
    result = parse_commentary_lines(text)
    assert result == {
        "标题A": "这是点评A",
        "标题B": "这是点评B",
    }


def test_parse_commentary_lines_skips_malformed():
    text = "标题A::点评A\nno separator here\n标题B::点评B"
    result = parse_commentary_lines(text)
    assert result == {
        "标题A": "点评A",
        "标题B": "点评B",
    }


def test_parse_commentary_lines_handles_empty():
    assert parse_commentary_lines("") == {}


def test_parse_commentary_lines_trims_whitespace():
    text = "  标题A  ::  点评A  \n"
    result = parse_commentary_lines(text)
    assert result == {"标题A": "点评A"}
