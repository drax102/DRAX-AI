"""
reminder_tools.py — SQLite reminder tools with time parsing and recurring support.
"""

from datetime import datetime, timedelta
import re
from backend.agent.tool_registry import register_tool
from backend.database.db import add_reminder, get_active_reminders, delete_reminder_by_query
from backend.core.logger import get_logger

logger = get_logger(__name__)


def _parse_reminder_time(text: str) -> tuple[str, str]:
    """Extract message and target datetime string from natural text."""
    now = datetime.now()
    clean = text.strip()
    remind_at = now + timedelta(minutes=30)  # Default fallback

    # Check for "in X minutes / hours"
    m_in = re.search(r"in\s+(\d+)\s+(minute|min|hour|hr|day)s?", clean, re.IGNORECASE)
    if m_in:
        val = int(m_in.group(1))
        unit = m_in.group(2).lower()
        if "min" in unit:
            remind_at = now + timedelta(minutes=val)
        elif "hour" in unit or "hr" in unit:
            remind_at = now + timedelta(hours=val)
        elif "day" in unit:
            remind_at = now + timedelta(days=val)
        clean = re.sub(r"in\s+\d+\s+(minute|min|hour|hr|day)s?", "", clean, flags=re.IGNORECASE).strip()

    # Check for "tomorrow at X" / "at X PM/AM"
    m_at = re.search(r"(?:tomorrow\s+)?at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", clean, re.IGNORECASE)
    if m_at:
        hour = int(m_at.group(1))
        minute = int(m_at.group(2) or 0)
        meridiem = (m_at.group(3) or "").lower()
        if meridiem == "pm" and hour < 12:
            hour += 12
        elif meridiem == "am" and hour == 12:
            hour = 0

        target_date = now.date()
        if "tomorrow" in clean.lower() or (hour < now.hour or (hour == now.hour and minute <= now.minute)):
            target_date += timedelta(days=1)

        remind_at = datetime.combine(target_date, datetime.min.time()).replace(hour=hour, minute=minute)
        clean = re.sub(r"(?:tomorrow\s+)?at\s+\d{1,2}(?::\d{2})?\s*(am|pm)?", "", clean, flags=re.IGNORECASE).strip()

    # Clean message
    for prefix in ["remind me to ", "remind me ", "set a reminder to ", "set reminder to "]:
        if clean.lower().startswith(prefix):
            clean = clean[len(prefix):].strip()

    return clean or "Reminder", remind_at.strftime("%Y-%m-%d %H:%M:%S")


@register_tool(
    name="create_reminder",
    description="Create a reminder for a specific time or duration (e.g. 'Remind me to study Python at 8 PM').",
    parameters={
        "message": {"type": "string", "description": "What to remind you about and when"},
        "recurring": {"type": "string", "description": "'none', 'daily', 'weekly'", "default": "none"},
    },
    risk_level="low",
    category="reminders",
)
def create_reminder(message: str, recurring: str = "none") -> str:
    msg, remind_time_str = _parse_reminder_time(message)
    r_id = add_reminder(message=msg, remind_at=remind_time_str, recurring=recurring)
    return f"Reminder created for {remind_time_str}: '{msg}'."


@register_tool(
    name="list_reminders",
    description="List all active scheduled reminders.",
    parameters={},
    risk_level="low",
    category="reminders",
)
def list_reminders() -> str:
    reminders = get_active_reminders()
    if not reminders:
        return "You have no active reminders."

    lines = [f"#{r['id']}: '{r['message']}' at {r['remind_at']}" for r in reminders]
    return "Active reminders:\n" + "\n".join(lines)


@register_tool(
    name="delete_reminder",
    description="Delete a scheduled reminder by ID or keywords.",
    parameters={"query": {"type": "string", "description": "Reminder text or ID to delete"}},
    risk_level="medium",
    category="reminders",
)
def delete_reminder(query: str) -> str:
    clean = query.strip()
    for w in ["delete reminder ", "remove reminder ", "cancel reminder "]:
        if clean.lower().startswith(w):
            clean = clean[len(w):].strip()

    ok = delete_reminder_by_query(clean)
    if ok:
        return f"Deleted reminder '{clean}'."
    return f"No active reminder matched '{clean}'."
