"""
alarm_tools.py — SQLite alarm creation, cancellation, and query tools.
"""

import re
from backend.agent.tool_registry import register_tool
from backend.database.db import add_alarm, get_alarms, cancel_alarm_by_query
from backend.core.logger import get_logger

logger = get_logger(__name__)


def _parse_alarm_time(text: str) -> tuple[str, str]:
    """Parse time string from 'set alarm for 7:30 AM', '7:00 p.m. tomorrow', or 'wake me up at 6'."""
    clean = text.lower().replace("p.m.", "pm").replace("a.m.", "am").replace("p.m", "pm").replace("a.m", "am")
    label = "Alarm"

    # Extract meridiem hints
    is_pm = "pm" in clean or "evening" in clean or "night" in clean or "afternoon" in clean
    is_am = "am" in clean or "morning" in clean

    m = re.search(r"(?:for|at)?\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", clean)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2) or 0)
        found_meridiem = m.group(3)

        if found_meridiem:
            meridiem = found_meridiem.upper()
        elif is_pm:
            meridiem = "PM"
        elif is_am:
            meridiem = "AM"
        else:
            meridiem = "AM" if hour in [5, 6, 7, 8, 9, 10, 11] else "PM"

        time_str = f"{hour:02d}:{minute:02d} {meridiem}"
        return time_str, label

    return "07:00 AM", label


@register_tool(
    name="create_alarm",
    description="Set an alarm for a specific time (e.g. 'Set alarm for 7 AM', 'Wake me up at 6:30', 'Alarm at 7 PM').",
    parameters={
        "time_expr": {"type": "string", "description": "Target alarm time (e.g. '7 AM', '6:30 PM', '7:00 pm tomorrow')"},
        "label": {"type": "string", "description": "Alarm label/tag", "default": "Alarm"},
    },
    risk_level="low",
    category="alarms",
)
def create_alarm(time_expr: str, label: str = "Alarm") -> str:
    time_str, _ = _parse_alarm_time(time_expr)
    a_id = add_alarm(time_str=time_str, label=label)
    return f"Alarm #{a_id} set for {time_str} ({label})."


@register_tool(
    name="list_alarms",
    description="List all scheduled alarms.",
    parameters={},
    risk_level="low",
    category="alarms",
)
def list_alarms() -> str:
    alarms = get_alarms()
    if not alarms:
        return "You have no active alarms."

    lines = [f"#{a['id']}: {a['time_str']} - {a['label']}" for a in alarms]
    return "Your alarms:\n" + "\n".join(lines)


@register_tool(
    name="cancel_alarm",
    description="Cancel or delete an alarm by time or ID.",
    parameters={"query": {"type": "string", "description": "Time string or ID of alarm to cancel"}},
    risk_level="low",
    category="alarms",
)
def cancel_alarm(query: str) -> str:
    clean = query.strip()
    for w in ["cancel alarm ", "delete alarm ", "turn off alarm "]:
        if clean.lower().startswith(w):
            clean = clean[len(w):].strip()

    ok = cancel_alarm_by_query(clean)
    if ok:
        return f"Cancelled alarm for '{clean}'."
    return f"No alarm matched '{clean}'."
