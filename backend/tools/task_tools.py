"""
task_tools.py — SQLite task management tools.
"""

from typing import Optional
from backend.agent.tool_registry import register_tool
from backend.database.db import add_task, get_tasks, complete_task_by_query, delete_task_by_query
from backend.core.logger import get_logger

logger = get_logger(__name__)


@register_tool(
    name="create_task",
    description="Create a new task with optional due date and priority (e.g. 'Add task to finish resume').",
    parameters={
        "title": {"type": "string", "description": "Title/description of the task"},
        "due_date": {"type": "string", "description": "Optional due date or time", "default": None},
        "priority": {"type": "string", "description": "Priority: low, medium, high", "default": "medium"},
    },
    risk_level="low",
    category="tasks",
)
def create_task(title: str, due_date: Optional[str] = None, priority: str = "medium") -> str:
    clean_title = title.strip()
    for prefix in ["add a task to ", "add task to ", "create a task to ", "create task to ", "remind me to "]:
        if clean_title.lower().startswith(prefix):
            clean_title = clean_title[len(prefix):].strip()

    task_id = add_task(title=clean_title, due_date=due_date, priority=priority)
    return f"Created task #{task_id}: '{clean_title}'."


@register_tool(
    name="list_tasks",
    description="List active or completed tasks.",
    parameters={"status": {"type": "string", "description": "'pending' or 'completed' or all", "default": "pending"}},
    risk_level="low",
    category="tasks",
)
def list_tasks(status: str = "pending") -> str:
    tasks = get_tasks(status=status if status in ["pending", "completed"] else None)
    if not tasks:
        return "You have no tasks in your list."

    lines = [f"#{t['id']}: {t['title']} [{t['status'].upper()}]" for t in tasks[:10]]
    return "Your tasks:\n" + "\n".join(lines)


@register_tool(
    name="complete_task",
    description="Mark a task as completed by title or task ID.",
    parameters={"query": {"type": "string", "description": "Task ID number or search keywords"}},
    risk_level="low",
    category="tasks",
)
def complete_task(query: str) -> str:
    clean = query.strip()
    for w in ["mark task ", "complete task ", "finish task ", "done with task "]:
        if clean.lower().startswith(w):
            clean = clean[len(w):].strip()

    ok = complete_task_by_query(clean)
    if ok:
        return f"Marked task '{clean}' as completed."
    return f"No pending task matched '{clean}'."


@register_tool(
    name="delete_task",
    description="Delete a task from the database by ID or title.",
    parameters={"query": {"type": "string", "description": "Task ID number or keywords"}},
    risk_level="medium",
    category="tasks",
)
def delete_task(query: str) -> str:
    clean = query.strip()
    for w in ["delete task ", "remove task "]:
        if clean.lower().startswith(w):
            clean = clean[len(w):].strip()

    ok = delete_task_by_query(clean)
    if ok:
        return f"Deleted task '{clean}'."
    return f"No task matched '{clean}' to delete."
