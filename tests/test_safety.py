"""
test_safety.py — Unit tests for tool security, risk classification, and confirmation gates.
"""

from backend.agent.planner import plan_request
from backend.agent.executor import execute_plan, confirm_pending_action
from backend.agent.tool_registry import registry
from backend.agent.context import context


def test_dangerous_commands_require_confirmation():
    tool = registry.get("shutdown_pc")
    assert tool is not None
    assert tool.risk_level == "high"
    assert tool.requires_confirmation is True

    tool_restart = registry.get("restart_pc")
    assert tool_restart is not None
    assert tool_restart.requires_confirmation is True


def test_confirmation_execution_flow():
    context.clear()
    plan = plan_request("shutdown computer")
    assert len(plan.steps) == 1
    assert plan.steps[0].tool_name == "shutdown_pc"

    prompt, needs_confirm = execute_plan(plan)
    assert needs_confirm is True
    assert "Confirmation required" in prompt
    assert context.pending_confirmation is not None

    # Cancel action
    cancelled_msg = confirm_pending_action(confirm=False)
    assert cancelled_msg == "Action cancelled."
    assert context.pending_confirmation is None
