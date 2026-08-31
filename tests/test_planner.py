"""
test_planner.py — Unit tests for agentic multi-step planning and compound request decomposition.
"""

from backend.agent.planner import plan_request


def test_single_step_planning():
    plan = plan_request("open chrome")
    assert len(plan.steps) == 1
    assert plan.steps[0].tool_name == "open_app"
    assert plan.steps[0].args["app_name"] == "chrome"


def test_multi_step_planning():
    plan = plan_request("open Spotify and play some relaxing music")
    assert len(plan.steps) >= 2
    assert plan.steps[0].tool_name == "open_app"
    assert plan.steps[1].tool_name == "play_media"


def test_compound_task_and_reminder():
    plan = plan_request("search AI news on Google then remind me to study at 8 PM")
    assert len(plan.steps) == 2
    assert plan.steps[0].tool_name == "search_web"
    assert plan.steps[1].tool_name == "create_reminder"


def test_finance_intent_planning():
    plan = plan_request("what is Apple's stock price?")
    assert len(plan.steps) == 1
    assert plan.steps[0].tool_name == "get_stock_price"
