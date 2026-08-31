"""
test_db_features.py — Unit tests for SQLite tasks, reminders, alarms, and memory persistence.
"""

from backend.database.db import (
    add_task, get_tasks, complete_task_by_query, delete_task_by_query,
    add_reminder, get_active_reminders, delete_reminder_by_query,
    add_alarm, get_alarms, cancel_alarm_by_query,
    set_preference, get_preference
)


def test_task_crud():
    t_id = add_task("Finish resume draft", priority="high")
    assert t_id > 0
    tasks = get_tasks()
    assert any(t["id"] == t_id for t in tasks)

    # Complete task
    ok = complete_task_by_query("resume draft")
    assert ok is True

    # Delete task
    del_ok = delete_task_by_query("resume draft")
    assert del_ok is True


def test_reminder_crud():
    r_id = add_reminder("Call mom", "2026-12-31 20:00:00")
    assert r_id > 0
    reminders = get_active_reminders()
    assert any(r["id"] == r_id for r in reminders)

    ok = delete_reminder_by_query("Call mom")
    assert ok is True


def test_alarm_crud():
    a_id = add_alarm("06:30 AM", "Morning workout")
    assert a_id > 0
    alarms = get_alarms()
    assert any(a["id"] == a_id for a in alarms)

    ok = cancel_alarm_by_query("Morning workout")
    assert ok is True


def test_memory_preferences():
    set_preference("favorite_team", "Manchester City")
    val = get_preference("favorite_team")
    assert val == "Manchester City"
