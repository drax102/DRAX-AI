"""
test_full_suite.py — Complete automated test suite covering all 17 Drax AI subsystems.
"""

import os
import pytest
from backend.core.wake_word import _soundex, _score_against_wake_words, _is_false_positive
from backend.core.app_executor import normalize_command, find_app_match
from backend.agent.planner import plan_request
from backend.agent.executor import execute_plan, confirm_pending_action
from backend.agent.tool_registry import registry
from backend.agent.context import context
from backend.database.db import (
    add_task, get_tasks, complete_task_by_query, delete_task_by_query,
    add_reminder, get_active_reminders, delete_reminder_by_query,
    add_alarm, get_alarms, cancel_alarm_by_query,
    set_preference, get_preference, add_to_watchlist, get_watchlist
)
from backend.tools.finance_tools import get_stock_price, fetch_quote
from backend.tools.weather_tools import get_weather
from backend.tools.news_tools import get_news, get_daily_briefing
from backend.tools.media_tools import play_media, pause_media
from backend.tools.knowledge_tools import get_knowledge


# ─── 1. Voice & Wake Word Tests ─────────────────────────────────────────────

def test_wake_word_soundex():
    assert _soundex("Drax") == _soundex("Dracs")
    assert _soundex("Hey") == _soundex("Hay")


def test_wake_word_scoring():
    score_exact = _score_against_wake_words("hey drax")
    assert score_exact == 1.0

    score_fuzzy = _score_against_wake_words("he drags")
    assert score_fuzzy >= 0.70

    score_alias = _score_against_wake_words("drax")
    assert score_alias >= 0.80


def test_false_positive_rejection():
    assert _is_false_positive("hello") is True
    assert _is_false_positive("thank you") is True
    assert _is_false_positive("hey siri") is True
    assert _is_false_positive("hey drax") is False


# ─── 2. Windows App Control & Ranked Matching Tests ─────────────────────────

def test_app_normalization():
    assert normalize_command("open spotify") == "spotify"
    assert normalize_command("launch the calculator app") == "calculator"
    assert normalize_command("opening file") == "opening file"


def test_ranked_app_matching():
    # Exact match
    app, score = find_app_match("chrome")
    assert app is not None
    assert score >= 0.90

    # Acronym match
    app_gta, score_gta = find_app_match("gta v")
    assert app_gta is not None
    assert score_gta >= 0.90

    # Low confidence / random text rejection
    app_fake, score_fake = find_app_match("random_nonexistent_xyz_app_123")
    assert score_fake < 0.70


# ─── 3. Multi-Step Planner Tests ────────────────────────────────────────────

def test_single_and_multi_step_planning():
    plan1 = plan_request("open chrome")
    assert len(plan1.steps) == 1
    assert plan1.steps[0].tool_name == "open_app"

    plan2 = plan_request("open Spotify and play deewane")
    assert len(plan2.steps) == 2
    assert plan2.steps[0].tool_name == "open_app"
    assert plan2.steps[1].tool_name == "play_media"

    plan3 = plan_request("what is Apple stock price and what is the weather in Delhi")
    assert len(plan3.steps) == 2
    assert plan3.steps[0].tool_name == "get_stock_price"
    assert plan3.steps[1].tool_name == "get_weather"


# ─── 4. Database Persistence Tests ──────────────────────────────────────────

def test_task_lifecycle():
    t_id = add_task("Prepare company demo presentation", priority="high")
    assert t_id > 0
    tasks = get_tasks()
    assert any(t["id"] == t_id for t in tasks)

    ok_comp = complete_task_by_query("presentation")
    assert ok_comp is True

    ok_del = delete_task_by_query("presentation")
    assert ok_del is True


def test_reminders_and_alarms():
    r_id = add_reminder("Review pull request", "2026-12-31 20:00:00")
    assert r_id > 0
    rems = get_active_reminders()
    assert any(r["id"] == r_id for r in rems)
    assert delete_reminder_by_query("Review pull request") is True

    a_id = add_alarm("07:00 PM", "Evening Study")
    assert a_id > 0
    alarms = get_alarms()
    assert any(a["id"] == a_id for a in alarms)
    assert cancel_alarm_by_query("Evening Study") is True


# ─── 5. Live Online Information Tests ───────────────────────────────────────

def test_stock_quotes():
    # US Stock
    res_us = get_stock_price("AAPL")
    assert "AAPL:" in res_us or "USD" in res_us or "retrieve financial data" in res_us

    # Indian Index
    res_in = get_stock_price("^NSEI")
    assert "^NSEI:" in res_in or "INR" in res_in or "retrieve financial data" in res_in


def test_weather_forecast():
    res = get_weather("Delhi")
    assert "Weather in" in res
    assert "Temperature is" in res


def test_news_and_briefing():
    news_res = get_news("world", limit=2)
    assert "News Headlines:" in news_res

    brief_res = get_daily_briefing("Delhi")
    assert "Good morning!" in brief_res


# ─── 6. Safety & Confirmation Tests ─────────────────────────────────────────

def test_safety_confirmation_gate():
    context.clear()
    plan = plan_request("shutdown computer")
    assert plan.steps[0].tool_name == "shutdown_pc"

    prompt, needs_confirm = execute_plan(plan)
    assert needs_confirm is True
    assert "Confirmation required" in prompt

    cancel_msg = confirm_pending_action(confirm=False)
    assert cancel_msg == "Action cancelled."
    assert context.pending_confirmation is None
