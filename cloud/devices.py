"""
devices.py — Cloud device pairing and registry manager for DRAX AI.
Manages unique Windows device identities, temporary pairing codes, active WebSocket connections,
and asynchronous remote command execution futures.
"""

import asyncio
import random
import string
import time
from typing import Dict, Optional, Any, Tuple
from fastapi import WebSocket

from backend.devices.registry import device_registry, PLATFORM_DEFAULT_CAPABILITIES
from backend.core.logger import get_logger

logger = get_logger(__name__)

# Heartbeat timeout threshold in seconds (if no heartbeat in 45s, mark offline)
HEARTBEAT_TIMEOUT = 45.0

# Default capability profiles per platform
DEFAULT_CAPABILITIES = PLATFORM_DEFAULT_CAPABILITIES


def _dev_get(info: Any, key: str, default: Any = None) -> Any:
    if isinstance(info, dict):
        return info.get(key, default)
    if hasattr(info, key):
        return getattr(info, key)
    if key == "name" and hasattr(info, "device_name"):
        return getattr(info, "device_name")
    return default


class DeviceManager:
    """Manages universal multi-device pairing, capabilities, WebSockets, and routing."""

    def __init__(self):
        # Synchronize dictionaries with central registry
        self.devices = device_registry._devices
        self.pairing_codes = device_registry._pairing_codes
        self.device_sockets = device_registry._sockets
        self.pending_requests = device_registry._pending_requests

    def generate_pairing_code(
        self,
        device_id: str = "",
        device_name: str = "Windows PC",
        token: str = "",
        platform: str = "windows",
        capabilities: Optional[list[str]] = None,
    ) -> str:
        """Generate a 4-character alphanumeric pairing code (e.g. DRAX-7K92)."""
        return device_registry.generate_pairing_code(
            device_id=device_id,
            device_name=device_name,
            token=token,
            platform=platform,
            capabilities=capabilities,
        )

    def verify_and_pair(self, pairing_code: str) -> Optional[Dict[str, Any]]:
        """Validate pairing code from web client and register device."""
        return device_registry.verify_and_pair(pairing_code)

    def set_primary_device(self, device_id: str) -> bool:
        """Designate target device as primary device."""
        return device_registry.set_primary_device(device_id)

    def register_device_socket(
        self,
        device_id: str,
        websocket: WebSocket,
        name: str = "Windows PC",
        platform: str = "windows",
        os_version: str = "",
        agent_version: str = "2.0.0",
        capabilities: Optional[list[str]] = None,
        token: str = "",
    ):
        """Register active WebSocket connection for a device with capability advertisement."""
        device_registry.register_device(
            device_id=device_id,
            device_name=name,
            platform=platform,
            os_version=os_version,
            agent_version=agent_version,
            capabilities=capabilities,
            token=token,
        )
        device_registry.register_socket(device_id, websocket)

    def unregister_device_socket(self, device_id: str, websocket: Optional[WebSocket] = None):
        """Handle device socket disconnection safely without removing replaced connections."""
        device_registry.unregister_socket(device_id, websocket=websocket)

    def update_heartbeat(self, device_id: str, telemetry: Optional[Dict[str, Any]] = None):
        """Update last seen timestamp and telemetry for an active device."""
        device_registry.update_heartbeat(device_id, telemetry=telemetry)

    def get_devices(self) -> list[Dict[str, Any]]:
        """Return list of all registered devices with full multi-device model & capabilities."""
        now = time.time()
        device_list = []
        for dev_id, info in self.devices.items():
            is_socket_active = dev_id in self.device_sockets
            ls = _dev_get(info, "last_seen", 0)
            if isinstance(ls, str):
                try:
                    # ISO string
                    from datetime import datetime
                    dt = datetime.fromisoformat(ls.replace("Z", "+00:00"))
                    ls_ts = dt.timestamp()
                except Exception:
                    ls_ts = now
            else:
                ls_ts = ls

            is_recent = (now - ls_ts) < HEARTBEAT_TIMEOUT
            is_online = is_socket_active and is_recent
            status = "online" if is_online else "offline"
            plat = _dev_get(info, "platform", "windows")

            device_list.append({
                "device_id": dev_id,
                "name": _dev_get(info, "name", "Windows PC"),
                "device_name": _dev_get(info, "device_name", "Windows PC"),
                "platform": plat,
                "os_version": _dev_get(info, "os_version", "Windows 11"),
                "agent_version": _dev_get(info, "agent_version", "2.0.0"),
                "capabilities": _dev_get(info, "capabilities", DEFAULT_CAPABILITIES.get(plat, [])),
                "is_primary": bool(_dev_get(info, "is_primary", False)),
                "status": status,
                "online": is_online,
                "last_seen": _dev_get(info, "last_seen", 0),
                "telemetry": _dev_get(info, "telemetry", {}),
            })
        return device_list

    def get_online_device(self, device_id: Optional[str] = None) -> Optional[Tuple[str, WebSocket]]:
        """Return target device ID and active WebSocket if online."""
        now = time.time()
        if device_id and device_id in self.device_sockets:
            return device_id, self.device_sockets[device_id]

        # Return primary online device first if available
        for dev_id, ws in list(self.device_sockets.items()):
            info = self.devices.get(dev_id, {})
            if _dev_get(info, "is_primary"):
                return dev_id, ws

        # Return first available online device
        for dev_id, ws in list(self.device_sockets.items()):
            return dev_id, ws

        return None

    def get_device_for_capability(self, capability: str, preferred_device_id: Optional[str] = None) -> Optional[Tuple[str, WebSocket]]:
        """Find an online device that supports the requested capability."""
        cap = capability.lower().strip()

        # 1. Check preferred device if specified
        if preferred_device_id and preferred_device_id in self.device_sockets:
            info = self.devices.get(preferred_device_id, {})
            caps = [c.lower() for c in _dev_get(info, "capabilities", [])]
            plat = _dev_get(info, "platform", "windows")
            if cap in caps or (plat == "windows" and cap in ["apps", "browser", "media", "volume", "system", "screen", "files", "telemetry"]):
                return preferred_device_id, self.device_sockets[preferred_device_id]

        # 2. Check primary device if online and capable
        for dev_id, ws in list(self.device_sockets.items()):
            info = self.devices.get(dev_id, {})
            if _dev_get(info, "is_primary"):
                caps = [c.lower() for c in _dev_get(info, "capabilities", [])]
                plat = _dev_get(info, "platform", "windows")
                if cap in caps or (plat == "windows" and cap in ["apps", "browser", "media", "volume", "system", "screen", "files", "telemetry"]):
                    return dev_id, ws

        # 3. Check any online device matching capability
        for dev_id, ws in list(self.device_sockets.items()):
            info = self.devices.get(dev_id, {})
            caps = [c.lower() for c in _dev_get(info, "capabilities", [])]
            plat = _dev_get(info, "platform", "windows")
            if cap in caps or (plat == "windows" and cap in ["apps", "browser", "media", "volume", "system", "screen", "files", "telemetry"]):
                return dev_id, ws

        return None

    def create_pending_request(self, request_id: str) -> asyncio.Future:
        """Create a Future to wait for a command result from a Windows Agent."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        fut = loop.create_future()
        self.pending_requests[request_id] = fut
        return fut

    def resolve_pending_request(self, request_id: str, result: str, success: bool = True, error: Optional[Dict[str, Any]] = None):
        """Resolve pending command Future with result from Windows Agent."""
        fut = self.pending_requests.pop(request_id, None)
        if fut and not fut.done():
            fut.set_result({"result": result, "response": result, "success": success, "error": error})


device_manager = DeviceManager()

