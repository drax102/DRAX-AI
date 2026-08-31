"""
backend/devices/router.py — Capability-based routing orchestrator.
Selects target devices based on required capability, explicit preference, and primary device designation.
"""

from typing import Optional, Tuple, Dict, Any, List
from backend.devices.models import Device
from backend.devices.registry import device_registry
from backend.core.logger import get_logger

logger = get_logger(__name__)

# Capability mappings from intent / action names to capability identifiers
INTENT_CAPABILITY_MAP: Dict[str, str] = {
    # Applications
    "open_app": "apps",
    "close_app": "apps",
    "apps.open": "apps",
    "apps.close": "apps",
    # Browser
    "open_url": "browser",
    "browser_navigate": "browser",
    "browser_click": "browser",
    "browser_type": "browser",
    "browser_scroll": "browser",
    "browser.open": "browser",
    # Media & Volume
    "play_media": "media",
    "pause_media": "media",
    "next_track": "media",
    "previous_track": "media",
    "media.play": "media",
    "media.pause": "media",
    "media.next": "media",
    "media.previous": "media",
    "volume_control": "volume",
    "volume.up": "volume",
    "volume.down": "volume",
    "volume.mute": "volume",
    # Screen & Vision
    "take_screenshot": "screen",
    "screen_read": "screen",
    "screen.capture": "screen",
    # Files
    "find_file": "files",
    "open_folder": "files",
    "files.open": "files",
    # System & Telemetry
    "lock_pc": "system",
    "sleep_pc": "system",
    "shutdown_pc": "system",
    "restart_pc": "system",
    "system.lock": "system",
    "system.sleep": "system",
    "system.shutdown": "system",
    "system.restart": "system",
    "get_telemetry": "telemetry",
    "telemetry.get": "telemetry",
    # Communication
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


def find_device_for_capability(
    capability: str,
    preferred_device_id: Optional[str] = None,
) -> Optional[Tuple[Device, Any]]:
    """
    Find a connected and online device capable of performing the requested capability.
    
    Selection Priority:
    1. Explicitly requested device (preferred_device_id) if online & capable.
    2. Primary device (is_primary = True) if online & capable.
    3. Any online device supporting the requested capability.
    4. Otherwise return None ("no capable device").
    """
    cap = capability.lower().strip()
    online_devices = device_registry.get_online_devices()

    if not online_devices:
        return None

    def _caps(d):
        raw = d.get("capabilities", []) if isinstance(d, dict) else getattr(d, "capabilities", [])
        return [c.lower() for c in raw]

    def _id(d):
        return d.get("device_id") if isinstance(d, dict) else getattr(d, "device_id", "")

    def _plat(d):
        return d.get("platform", "windows") if isinstance(d, dict) else getattr(d, "platform", "windows")

    def _is_primary(d):
        return d.get("is_primary", False) if isinstance(d, dict) else getattr(d, "is_primary", False)

    # 1. Explicitly requested device
    if preferred_device_id:
        for dev in online_devices:
            dev_id = _id(dev)
            if dev_id == preferred_device_id:
                caps = _caps(dev)
                plat = _plat(dev)
                if cap in caps or (plat == "windows" and cap in ["apps", "browser", "media", "volume", "system", "screen", "files", "telemetry"]):
                    ws = device_registry.get_socket(dev_id)
                    if ws:
                        return dev, ws

    # 2. Primary device
    for dev in online_devices:
        if _is_primary(dev):
            dev_id = _id(dev)
            caps = _caps(dev)
            plat = _plat(dev)
            if cap in caps or (plat == "windows" and cap in ["apps", "browser", "media", "volume", "system", "screen", "files", "telemetry"]):
                ws = device_registry.get_socket(dev_id)
                if ws:
                    return dev, ws

    # 3. Any online device supporting capability
    for dev in online_devices:
        dev_id = _id(dev)
        caps = _caps(dev)
        plat = _plat(dev)
        if cap in caps or (plat == "windows" and cap in ["apps", "browser", "media", "volume", "system", "screen", "files", "telemetry"]):
            ws = device_registry.get_socket(dev_id)
            if ws:
                return dev, ws

    return None


class CapabilityRouter:
    """Capability Router orchestrator."""

    @staticmethod
    def get_capability_for_tool(tool_name: str) -> str:
        return INTENT_CAPABILITY_MAP.get(tool_name, "cloud")

    @classmethod
    def resolve_tool_execution(
        cls,
        tool_name: str,
        preferred_device_id: Optional[str] = None,
    ) -> Tuple[str, bool, Optional[Device], Optional[Any]]:
        """
        Resolve a tool name to required capability, cloud status, and target device socket.
        Returns: (capability, is_cloud, target_device, websocket)
        """
        cap = cls.get_capability_for_tool(tool_name)
        if cap == "cloud":
            return cap, True, None, None

        res = find_device_for_capability(cap, preferred_device_id=preferred_device_id)
        if res:
            dev, ws = res
            return cap, False, dev, ws

        return cap, False, None, None
