"""
test_intent_routing.py — Unit tests for intent routing engine.
"""

from backend.core.intent_router import route_command, _safe_eval_math


def test_greetings_and_identity():
    assert "Drax" in route_command("who are you")
    assert "Hello" in route_command("hello")


def test_time_and_date():
    assert "time is" in route_command("what time is it")
    assert "Today is" in route_command("what is the date")


def test_safe_math_eval():
    assert "10" in _safe_eval_math("what is 5 + 5")
    assert "25" in _safe_eval_math("calculate 5 * 5")
    assert "undefined" in _safe_eval_math("what is 10 / 0")
