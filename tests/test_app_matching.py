"""
test_app_matching.py — Unit tests for app indexer and matching.
"""

from backend.core.app_executor import normalize_command, find_app_match


def test_normalize_command():
    assert normalize_command("open spotify") == "spotify"
    assert normalize_command("launch the calculator app") == "calculator"
    assert normalize_command("start chrome") == "chrome"
    # Word boundary safety test: "opening" should NOT strip "open"
    assert normalize_command("opening file") == "opening file"


def test_app_match_builtin():
    app, score = find_app_match("notepad")
    assert app is not None
    assert score >= 0.75
    assert app["name"] in ["notepad", "text editor"]
