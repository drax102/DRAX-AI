"""
db.py — SQLite database manager for DRAX AI.
Manages tasks, reminders, alarms, watchlists, price alerts, preferences, and conversation history.
"""

import json
import os
import sqlite3
import threading
from datetime import datetime
from typing import Any, List, Dict, Optional

from backend.core.config import settings
from backend.core.logger import get_logger

logger = get_logger(__name__)

_DB_PATH = settings.resolve_path("data/drax.db")
_db_lock = threading.Lock()


def get_connection() -> sqlite3.Connection:
    """Get SQLite database connection with row factory."""
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database schema with versioning and required tables."""
    with _db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()

            # Tasks table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                due_date TEXT DEFAULT NULL,
                priority TEXT DEFAULT 'medium',
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # Reminders table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT NOT NULL,
                remind_at TEXT NOT NULL,
                recurring TEXT DEFAULT 'none',
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # Alarms table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS alarms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time_str TEXT NOT NULL,
                label TEXT DEFAULT 'Alarm',
                is_active INTEGER DEFAULT 1,
                days_of_week TEXT DEFAULT 'all',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # Stock watchlist
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT UNIQUE NOT NULL,
                name TEXT DEFAULT '',
                asset_type TEXT DEFAULT 'stock',
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # Price alerts table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                target_price REAL NOT NULL,
                condition TEXT NOT NULL, -- 'above' or 'below'
                is_triggered INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # Preferences table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # Conversation history
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            conn.commit()
            logger.info(f"Database initialized successfully at {_DB_PATH}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
        finally:
            conn.close()


# ─── Task Operations ────────────────────────────────────────────────────────

def add_task(title: str, description: str = "", due_date: Optional[str] = None, priority: str = "medium") -> int:
    with _db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO tasks (title, description, due_date, priority, status) VALUES (?, ?, ?, ?, 'pending')",
                (title, description, due_date, priority),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()


def get_tasks(status: Optional[str] = None) -> List[Dict[str, Any]]:
    with _db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            if status:
                cursor.execute("SELECT * FROM tasks WHERE status = ? ORDER BY id DESC", (status,))
            else:
                cursor.execute("SELECT * FROM tasks ORDER BY id DESC")
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()


def complete_task_by_query(query: str) -> bool:
    with _db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE tasks SET status = 'completed', updated_at = CURRENT_TIMESTAMP WHERE (title LIKE ? OR id = ?) AND status = 'pending'",
                (f"%{query}%", query if query.isdigit() else -1),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()


def delete_task_by_query(query: str) -> bool:
    with _db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM tasks WHERE title LIKE ? OR id = ?",
                (f"%{query}%", query if query.isdigit() else -1),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()


def delete_task_by_id(task_id: int) -> bool:
    with _db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()


def complete_task_by_id(task_id: int) -> bool:
    with _db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE tasks SET status = 'completed', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (task_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()



# ─── Reminder Operations ────────────────────────────────────────────────────

def add_reminder(message: str, remind_at: str, recurring: str = "none") -> int:
    with _db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO reminders (message, remind_at, recurring, status) VALUES (?, ?, ?, 'active')",
                (message, remind_at, recurring),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()


def get_active_reminders() -> List[Dict[str, Any]]:
    with _db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM reminders WHERE status = 'active' ORDER BY remind_at ASC")
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()


def delete_reminder_by_query(query: str) -> bool:
    with _db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM reminders WHERE message LIKE ? OR id = ?",
                (f"%{query}%", query if query.isdigit() else -1),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()


def delete_reminder_by_id(reminder_id: int) -> bool:
    with _db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()


def update_reminder_status(reminder_id: int, status: str):
    with _db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE reminders SET status = ? WHERE id = ?", (status, reminder_id))
            conn.commit()
        finally:
            conn.close()


# ─── Alarm Operations ───────────────────────────────────────────────────────

def add_alarm(time_str: str, label: str = "Alarm") -> int:
    with _db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO alarms (time_str, label, is_active) VALUES (?, ?, 1)",
                (time_str, label),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()


def get_alarms() -> List[Dict[str, Any]]:
    with _db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM alarms ORDER BY time_str ASC")
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()


def cancel_alarm_by_query(query: str) -> bool:
    with _db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM alarms WHERE time_str LIKE ? OR label LIKE ? OR id = ?",
                (f"%{query}%", f"%{query}%", query if query.isdigit() else -1),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()


def delete_alarm_by_id(alarm_id: int) -> bool:
    with _db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM alarms WHERE id = ?", (alarm_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()



# ─── Watchlist & Price Alerts ───────────────────────────────────────────────

def add_to_watchlist(symbol: str, name: str = "", asset_type: str = "stock") -> bool:
    with _db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO watchlist (symbol, name, asset_type) VALUES (?, ?, ?)",
                (symbol.upper().strip(), name, asset_type),
            )
            conn.commit()
            return True
        finally:
            conn.close()


def get_watchlist() -> List[Dict[str, Any]]:
    with _db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM watchlist ORDER BY symbol ASC")
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()


def remove_from_watchlist(symbol: str) -> bool:
    with _db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM watchlist WHERE symbol = ?", (symbol.upper().strip(),))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()


def add_price_alert(symbol: str, target_price: float, condition: str) -> int:
    with _db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO price_alerts (symbol, target_price, condition, is_triggered) VALUES (?, ?, ?, 0)",
                (symbol.upper().strip(), target_price, condition.lower()),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()


def get_active_price_alerts() -> List[Dict[str, Any]]:
    with _db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM price_alerts WHERE is_triggered = 0")
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()


def mark_price_alert_triggered(alert_id: int):
    with _db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE price_alerts SET is_triggered = 1 WHERE id = ?", (alert_id,))
            conn.commit()
        finally:
            conn.close()


# ─── Long-Term Memory / Preferences ─────────────────────────────────────────

def set_preference(key: str, value: Any):
    with _db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO preferences (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                (key, json.dumps(value)),
            )
            conn.commit()
        finally:
            conn.close()


def get_preference(key: str, default: Any = None) -> Any:
    with _db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM preferences WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                return json.loads(row["value"])
            return default
        finally:
            conn.close()


def get_all_preferences() -> Dict[str, Any]:
    with _db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM preferences")
            return {row["key"]: json.loads(row["value"]) for row in cursor.fetchall()}
        finally:
            conn.close()


def clear_all_preferences():
    with _db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM preferences")
            conn.commit()
        finally:
            conn.close()


# ─── Conversation History ───────────────────────────────────────────────────

def log_conversation(role: str, content: str, metadata: Optional[Dict] = None):
    with _db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO conversation_history (role, content, metadata) VALUES (?, ?, ?)",
                (role, content, json.dumps(metadata or {})),
            )
            conn.commit()
        finally:
            conn.close()


def get_recent_conversation(limit: int = 10) -> List[Dict[str, Any]]:
    with _db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM conversation_history ORDER BY id DESC LIMIT ?", (limit,))
            rows = [dict(row) for row in cursor.fetchall()]
            rows.reverse()
            return rows
        finally:
            conn.close()


# Initialize database on module load
init_db()
