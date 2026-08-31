"""
backend/skills/productivity_skill.py — Unified productivity, tasks, reminders, alarms, and daily briefings skill.
"""

from typing import Optional, Dict, Any, List
from backend.skills.base import BaseSkill
from backend.database.db import (
    get_tasks, add_task, delete_task_by_id, complete_task_by_id,
    get_active_reminders, add_reminder, delete_reminder_by_id,
    get_alarms, add_alarm, delete_alarm_by_id
)
from backend.tools.weather_tools import get_weather
from backend.tools.news_tools import get_news
from backend.tools.finance_tools import get_stock_price
from backend.core.logger import get_logger

logger = get_logger(__name__)


class ProductivitySkill(BaseSkill):
    name = "productivity"
    category = "productivity"
    required_capability = "cloud"

    def _register_actions(self):
        self.register_action("add_task", self.add_task, "Add a new task", "cloud")
        self.register_action("list_tasks", self.list_tasks, "List all active tasks", "cloud")
        self.register_action("complete_task", self.complete_task, "Mark a task completed", "cloud")
        self.register_action("add_reminder", self.add_reminder, "Set a timed reminder", "cloud")
        self.register_action("list_reminders", self.list_reminders, "List active reminders", "cloud")
        self.register_action("add_alarm", self.add_alarm, "Schedule an alarm", "cloud")
        self.register_action("list_alarms", self.list_alarms, "List alarms", "cloud")
        self.register_action("morning_briefing", self.get_morning_briefing, "Generate comprehensive daily brief", "cloud")

    def add_task(self, title: str, priority: str = "medium") -> str:
        tid = add_task(title=title, priority=priority)
        return f"Task added: '{title}' (ID: {tid})."

    def list_tasks(self) -> str:
        tasks = get_tasks()
        if not tasks:
            return "You have no active tasks."
        lines = [f"{t['id']}. {t['title']} [{t.get('priority', 'medium').upper()}]" for t in tasks]
        return "Your Active Tasks:\n" + "\n".join(lines)

    def complete_task(self, query: str) -> str:
        tasks = get_tasks()
        q = query.lower().strip()
        matched = [t for t in tasks if q in t["title"].lower() or q == str(t["id"])]
        if not matched:
            return f"No task matching '{query}' found."
        target = matched[0]
        complete_task_by_id(target["id"])
        return f"Task marked completed: '{target['title']}'."

    def add_reminder(self, message: str, remind_at: str) -> str:
        rid = add_reminder(message=message, remind_at=remind_at)
        return f"Reminder set: '{message}' for {remind_at}."

    def list_reminders(self) -> str:
        reminders = get_active_reminders()
        if not reminders:
            return "No active reminders."
        lines = [f"• {r['message']} at {r['remind_at']}" for r in reminders]
        return "Your Reminders:\n" + "\n".join(lines)

    def add_alarm(self, time_str: str, label: str = "Alarm") -> str:
        aid = add_alarm(time_str=time_str, label=label)
        return f"Alarm set for {time_str} ({label})."

    def list_alarms(self) -> str:
        alarms = get_alarms()
        if not alarms:
            return "No active alarms."
        lines = [f"• {a['time_str']} ({a.get('label', 'Alarm')})" for a in alarms]
        return "Scheduled Alarms:\n" + "\n".join(lines)

    def get_morning_briefing(self) -> str:
        tasks = get_tasks()
        reminders = get_active_reminders()
        weather = get_weather("Delhi")
        stock = get_stock_price("NVDA")
        news = get_news("ai")

        brief = ["🌅 Good morning! Here is your DRAX AI Daily Briefing:\n"]
        brief.append(f"🌤️ {weather}\n")
        brief.append(f"📈 {stock}\n")
        if tasks:
            brief.append(f"📋 You have {len(tasks)} pending task(s). Top task: '{tasks[0]['title']}'.\n")
        else:
            brief.append("📋 No pending tasks today.\n")
        if reminders:
            brief.append(f"⏰ Next reminder: '{reminders[0]['message']}' at {reminders[0]['remind_at']}.\n")
        brief.append(f"📰 AI & Tech Highlight:\n{news}")

        return "\n".join(brief)


productivity_skill = ProductivitySkill()
