"""
Database package
"""

from backend.database.db import (
    add_task, get_tasks, complete_task_by_query, delete_task_by_query,
    add_reminder, get_active_reminders, delete_reminder_by_query, update_reminder_status,
    add_alarm, get_alarms, cancel_alarm_by_query,
    add_to_watchlist, get_watchlist, remove_from_watchlist,
    add_price_alert, get_active_price_alerts, mark_price_alert_triggered,
    set_preference, get_preference, get_all_preferences, clear_all_preferences,
    log_conversation, get_recent_conversation
)

__all__ = [
    "add_task", "get_tasks", "complete_task_by_query", "delete_task_by_query",
    "add_reminder", "get_active_reminders", "delete_reminder_by_query", "update_reminder_status",
    "add_alarm", "get_alarms", "cancel_alarm_by_query",
    "add_to_watchlist", "get_watchlist", "remove_from_watchlist",
    "add_price_alert", "get_active_price_alerts", "mark_price_alert_triggered",
    "set_preference", "get_preference", "get_all_preferences", "clear_all_preferences",
    "log_conversation", "get_recent_conversation"
]
