"""
backend/tools/__init__.py — Automatically imports and registers all tool modules.
"""

from backend.agent.tool_registry import registry
from backend.tools import (
    app_tools,
    browser_tools,
    task_tools,
    reminder_tools,
    alarm_tools,
    finance_tools,
    news_tools,
    weather_tools,
    media_tools,
    screen_tools,
    file_tools,
    system_tools,
    knowledge_tools,
)

__all__ = ["registry"]
