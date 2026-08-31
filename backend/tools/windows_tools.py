"""
windows_tools.py — Registry loader for Windows-Local Desktop Tools.
Only loaded on Windows desktop workstations to control local applications, hardware media keys, processes, and system operations.
"""

from backend.agent.tool_registry import registry
from backend.tools import (
    app_tools,
    media_tools,
    screen_tools,
    system_tools,
    file_tools,
    browser_tools,
)

__all__ = [
    "registry",
    "app_tools",
    "media_tools",
    "screen_tools",
    "system_tools",
    "file_tools",
    "browser_tools",
]
