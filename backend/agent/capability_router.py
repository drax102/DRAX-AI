"""
backend/agent/capability_router.py — Capability-based routing orchestrator.
Maps user intents and action steps to required device capabilities, finds matching online devices,
or executes server-side cloud services.
"""

from typing import Dict, Any, Optional, Tuple, List
from cloud.devices import device_manager
from backend.core.logger import get_logger

logger = get_logger(__name__)

# Capability Mapping for all DRAX AI tools & actions
TOOL_CAPABILITY_MAP: Dict[str, str] = {
    # Applications
    "open_app": "apps",
    "close_app": "apps",
    # Browser
    "open_url": "browser",
    "browser_navigate": "browser",
    "browser_click": "browser",
    "browser_type": "browser",
    "browser_scroll": "browser",
    "browser_open_tab": "browser",
    "browser_close_tab": "browser",
    "browser_hover": "browser",
    "browser_back": "browser",
    "browser_forward": "browser",
    # Media & Volume
    "play_media": "media",
    "pause_media": "media",
    "next_track": "media",
    "previous_track": "media",
    "volume_control": "volume",
    # Screen
    "take_screenshot": "screen",
    "screen_read": "screen",
    # Files
    "find_file": "files",
    "open_folder": "files",
    # System & Telemetry
    "lock_pc": "system",
    "sleep_pc": "system",
    "shutdown_pc": "system",
    "restart_pc": "system",
    "open_system_settings": "system",
    "get_telemetry": "telemetry",
    # Communication (Mobile capabilities)
    "make_call": "calls",
    "send_sms": "sms",
    # Cloud Tools
    "get_weather": "cloud",
    "get_stock_price": "cloud",
    "track_stock": "cloud",
    "list_watchlist": "cloud",
    "get_news": "cloud",
    "get_knowledge": "cloud",
    "search_web": "cloud",
    "create_task": "cloud",
    "list_tasks": "cloud",
    "complete_task": "cloud",
    "delete_task": "cloud",
    "create_reminder": "cloud",
    "list_reminders": "cloud",
    "delete_reminder": "cloud",
    "create_alarm": "cloud",
    "list_alarms": "cloud",
    "cancel_alarm": "cloud",
    "get_daily_briefing": "cloud",
}

# Standard human-readable messages for capabilities without registered hardware
UNSUPPORTED_CAPABILITY_MESSAGES: Dict[str, str] = {
    "calls": "No connected device currently supports voice calls. Pair an Android or cellular device to make voice calls.",
    "sms": "No connected device currently supports SMS messaging. Pair a cellular device to send text messages.",
    "camera": "No connected device with camera capture capability is currently online.",
    "location": "No connected device with GPS location services is currently online.",
}


class RoutingDecision:
    """Represents the resolution of an execution step to a target device or cloud."""

    def __init__(
        self,
        tool_name: str,
        required_capability: str,
        is_cloud: bool,
        device_id: Optional[str] = None,
        websocket: Optional[Any] = None,
        unsupported_message: Optional[str] = None,
    ):
        self.tool_name = tool_name
        self.required_capability = required_capability
        self.is_cloud = is_cloud
        self.device_id = device_id
        self.websocket = websocket
        self.unsupported_message = unsupported_message

    @property
    def is_available(self) -> bool:
        return self.is_cloud or (self.websocket is not None)


class CapabilityRouter:
    """Orchestrates capability-based device matching and cloud fallbacks."""

    @staticmethod
    def get_required_capability(tool_name: str) -> str:
        return TOOL_CAPABILITY_MAP.get(tool_name, "cloud")

    @classmethod
    def route_step(cls, tool_name: str, preferred_device_id: Optional[str] = None) -> RoutingDecision:
        cap = cls.get_required_capability(tool_name)

        # Pure Cloud Execution
        if cap == "cloud":
            return RoutingDecision(
                tool_name=tool_name,
                required_capability="cloud",
                is_cloud=True,
            )

        # Find capable online device
        target = device_manager.get_device_for_capability(cap, preferred_device_id=preferred_device_id)

        # Fallback check for general device if specific sub-capability like 'volume' matches 'windows'
        if not target and cap in ["volume", "telemetry", "screen", "files", "browser"]:
            target = device_manager.get_online_device(preferred_device_id)

        if target:
            dev_id, ws = target
            return RoutingDecision(
                tool_name=tool_name,
                required_capability=cap,
                is_cloud=False,
                device_id=dev_id,
                websocket=ws,
            )

        # If capability requires specific device not connected
        if cap in ["apps", "media", "system", "volume", "screen", "files", "browser", "telemetry"]:
            unsupported_msg = "No Windows Agent is connected. Open Drax AI on your PC and pair this device."
        else:
            unsupported_msg = UNSUPPORTED_CAPABILITY_MESSAGES.get(
                cap,
                f"No online device currently exposes the '{cap}' capability to execute '{tool_name}'. Please connect your device."
            )

        return RoutingDecision(
            tool_name=tool_name,
            required_capability=cap,
            is_cloud=False,
            device_id=None,
            websocket=None,
            unsupported_message=unsupported_msg,
        )


capability_router = CapabilityRouter()
