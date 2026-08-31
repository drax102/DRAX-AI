"""
cloud_tools.py — Registry loader for platform-independent, Cloud-Safe Tools.
Only loads tools that execute safely on Linux, Render, AWS, and Cloud environments without OS desktop dependencies.
"""

from backend.agent.tool_registry import registry
from backend.tools import (
    task_tools,
    reminder_tools,
    alarm_tools,
    finance_tools,
    news_tools,
    weather_tools,
    knowledge_tools,
)

__all__ = [
    "registry",
    "task_tools",
    "reminder_tools",
    "alarm_tools",
    "finance_tools",
    "news_tools",
    "weather_tools",
    "knowledge_tools",
]
