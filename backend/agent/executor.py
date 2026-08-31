"""
executor.py — Safe multi-step tool execution engine with confirmation boundary enforcement.
"""

from typing import Tuple
from backend.agent.context import context
from backend.agent.planner import ExecutionPlan, ActionStep
from backend.agent.tool_registry import registry
from backend.core.logger import get_logger

logger = get_logger(__name__)


def execute_plan(plan: ExecutionPlan) -> Tuple[str, bool]:
    """
    Execute all steps in an ExecutionPlan sequentially.
    Returns (response_text, is_confirmation_required).
    """
    if plan.is_empty:
        return "I'm not sure how to handle that request.", False

    results = []

    for step in plan.steps:
        tool = registry.get(step.tool_name)
        if not tool:
            logger.warning(f"Tool '{step.tool_name}' not found in registry")
            results.append(f"Tool '{step.tool_name}' is not available.")
            continue

        # Check confirmation boundary
        if tool.requires_confirmation:
            context.pending_confirmation = {"tool": tool.name, "args": step.args}
            prompt = f"⚠️ Confirmation required: Are you sure you want to execute {tool.name.replace('_', ' ')}?"
            logger.info(f"Execution paused for confirmation: {tool.name}")
            return prompt, True

        # Execute tool
        try:
            res = tool.execute(**step.args)
            if res:
                results.append(str(res))

            # Update context
            category = getattr(tool, "category", "general")
            entity = step.args.get("symbol") or step.args.get("app_name") or step.args.get("query")
            context.update_turn(intent=step.tool_name, domain=category, entity=entity, result=str(res))

        except Exception as e:
            logger.error(f"Failed step {step.tool_name}: {e}")
            results.append(f"Error during {step.tool_name}: {str(e)}")

    combined_response = "\n\n".join(results) if results else "Done."
    return combined_response, False


def confirm_pending_action(confirm: bool) -> str:
    """Execute or reject the currently pending action."""
    pending = context.pending_confirmation
    if not pending:
        return "There are no pending actions requiring confirmation."

    context.pending_confirmation = None
    if not confirm:
        return "Action cancelled."

    tool = registry.get(pending["tool"])
    if tool:
        res = tool.execute(**pending.get("args", {}))
        return str(res)
    return "Action could not be executed."
