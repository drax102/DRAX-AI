"""
memory.py — Long-term SQLite user preference and memory management.
Supports 'What do you remember about me?', 'Remember that my favorite city is Mumbai', 'Forget that', 'Clear memory'.
"""

from typing import Dict, Any
from backend.database.db import set_preference, get_preference, get_all_preferences, clear_all_preferences
from backend.core.logger import get_logger

logger = get_logger(__name__)


def remember(key: str, value: Any):
    """Store a key-value fact into long-term memory."""
    set_preference(key, value)
    logger.info(f"Memory saved: {key} = {value}")


def recall(key: str, default: Any = None) -> Any:
    """Recall a fact from long-term memory."""
    return get_preference(key, default)


def list_memories() -> str:
    """Return human-readable summary of stored preferences and facts."""
    prefs = get_all_preferences()
    if not prefs:
        return "I do not have any stored personal preferences about you yet."

    lines = [f"• {k.replace('_', ' ').title()}: {v}" for k, v in prefs.items()]
    return "Here is what I remember about you:\n" + "\n".join(lines)


def forget_memory(key: str) -> str:
    """Forget a specific preference."""
    prefs = get_all_preferences()
    clean_k = key.lower().strip().replace(" ", "_")
    for k in prefs.keys():
        if clean_k in k:
            set_preference(k, None)
            return f"I have forgotten your {k.replace('_', ' ')}."
    return f"I don't recall anything about '{key}'."


def clear_memory() -> str:
    """Clear all long-term memories."""
    clear_all_preferences()
    return "All stored personal preferences and memory have been cleared."
