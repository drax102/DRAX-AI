"""
system_tools.py — Windows system control tools with safety confirmation enforcement.
"""

import os
from backend.agent.tool_registry import register_tool
from backend.core.system_info import get_system_status_speech, get_system_telemetry
from backend.core.logger import get_logger

logger = get_logger(__name__)


@register_tool(
    name="get_telemetry",
    description="Get real-time CPU, RAM, OS, and system telemetry stats.",
    parameters={},
    risk_level="low",
    category="system",
)
def get_telemetry() -> str:
    return get_system_status_speech()


@register_tool(
    name="lock_pc",
    description="Lock the Windows workstation.",
    parameters={},
    risk_level="low",
    category="system",
)
def lock_pc() -> str:
    os.system("rundll32.exe user32.dll,LockWorkStation")
    return "Workstation locked."


@register_tool(
    name="sleep_pc",
    description="Put the computer into sleep mode.",
    parameters={},
    risk_level="medium",
    requires_confirmation=False,
    category="system",
)
def sleep_pc() -> str:
    os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
    return "Entering sleep mode."


@register_tool(
    name="shutdown_pc",
    description="Shut down the computer (Requires user confirmation).",
    parameters={},
    risk_level="high",
    requires_confirmation=True,
    category="system",
)
def shutdown_pc() -> str:
    os.system("shutdown /s /t 10")
    return "Shutting down the computer in 10 seconds."


@register_tool(
    name="restart_pc",
    description="Restart the computer (Requires user confirmation).",
    parameters={},
    risk_level="high",
    requires_confirmation=True,
    category="system",
)
def restart_pc() -> str:
    os.system("shutdown /r /t 10")
    return "Restarting the computer in 10 seconds."


@register_tool(
    name="open_system_settings",
    description="Open Windows Settings or Control Panel.",
    parameters={"page": {"type": "string", "description": "Specific settings page: display, sound, network, bluetooth, apps", "default": ""}},
    risk_level="low",
    category="system",
)
def open_system_settings(page: str = "") -> str:
    page_clean = page.lower().strip()
    uris = {
        "display": "ms-settings:display",
        "sound": "ms-settings:sound",
        "bluetooth": "ms-settings:bluetooth",
        "network": "ms-settings:network",
        "apps": "ms-settings:appsfeatures",
        "updates": "ms-settings:windowsupdate",
    }
    uri = uris.get(page_clean, "ms-settings:")
    os.startfile(uri)
    return f"Opened Windows {page.capitalize() or 'General'} Settings."
