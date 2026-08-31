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

from backend.core.logger import get_logger

logger = get_logger(__name__)

# Heartbeat timeout threshold in seconds (if no heartbeat in 45s, mark offline)
HEARTBEAT_TIMEOUT = 45.0


# Default capability profiles per platform
DEFAULT_CAPABILITIES: Dict[str, list[str]] = {
    "windows": ["apps", "browser", "media", "volume", "screen", "files", "system", "notifications", "telemetry"],
    "android": ["calls", "sms", "notifications", "location", "camera", "media", "apps"],
    "macos": ["apps", "browser", "media", "volume", "screen", "files", "system", "notifications", "telemetry"],
    "linux": ["apps", "browser", "media", "volume", "screen", "files", "system", "notifications", "telemetry"],
    "web": ["web", "dashboard", "chat"],
}


class DeviceManager:
    """Manages universal multi-device pairing, capabilities, WebSockets, and routing."""

    def __init__(self):
        # device_id -> { "device_id": str, "name": str, "token": str, "platform": str,
        #                 "os_version": str, "agent_version": str, "capabilities": list,
        #                 "is_primary": bool, "paired_at": float, "last_seen": float,
        #                 "status": "online"|"offline", "telemetry": dict, "connection_id": str }
        self.devices: Dict[str, Dict[str, Any]] = {}
        # pairing_code -> { "device_id": str, "device_name": str, "token": str, "platform": str, "expires_at": float }
        self.pairing_codes: Dict[str, Dict[str, Any]] = {}
        # device_id -> WebSocket
        self.device_sockets: Dict[str, WebSocket] = {}
        # request_id -> asyncio.Future
        self.pending_requests: Dict[str, asyncio.Future] = {}

    def generate_pairing_code(
        self,
        device_id: str = "",
        device_name: str = "Windows PC",
        token: str = "",
        platform: str = "windows",
        capabilities: Optional[list[str]] = None,
    ) -> str:
        """Generate a 4-character alphanumeric pairing code (e.g. DRAX-7K92)."""
        chars = string.ascii_uppercase + "23456789"
        code_suffix = "".join(random.choices(chars, k=4))
        code = f"DRAX-{code_suffix}"
        plat_clean = platform.lower().strip()

        self.pairing_codes[code] = {
            "device_id": device_id or f"drax_{plat_clean}_{code_suffix.lower()}",
            "device_name": device_name,
            "token": token,
            "platform": plat_clean,
            "capabilities": capabilities or DEFAULT_CAPABILITIES.get(plat_clean, ["apps", "media", "system"]),
            "expires_at": time.time() + 600,  # 10 minutes validity
        }
        logger.info(f"Generated pairing code '{code}' for device '{device_name}' ({plat_clean})")
        return code

    def verify_and_pair(self, pairing_code: str) -> Optional[Dict[str, Any]]:
        """Validate pairing code from web client and register device."""
        code = pairing_code.strip().upper()
        record = self.pairing_codes.get(code)
        if not record:
            return None

        if time.time() > record["expires_at"]:
            del self.pairing_codes[code]
            return None

        device_id = record["device_id"]
        is_online = device_id in self.device_sockets
        plat = record.get("platform", "windows").lower()
        caps = record.get("capabilities") or DEFAULT_CAPABILITIES.get(plat, ["apps", "media", "system"])
        is_first = len(self.devices) == 0

        self.devices[device_id] = {
            "device_id": device_id,
            "name": record["device_name"],
            "token": record["token"],
            "platform": plat,
            "os_version": "Windows 11" if plat == "windows" else plat.capitalize(),
            "agent_version": "2.0.0",
            "capabilities": caps,
            "is_primary": is_first,
            "paired_at": time.time(),
            "last_seen": time.time(),
            "status": "online" if is_online else "offline",
            "telemetry": {},
            "connection_id": None,
        }
        del self.pairing_codes[code]
        logger.info(f"Successfully paired device '{record['device_name']}' ({device_id}) with capabilities: {caps}")
        return self.devices[device_id]

    def set_primary_device(self, device_id: str) -> bool:
        """Designate target device as primary device."""
        if device_id not in self.devices:
            return False
        for dev in self.devices.values():
            dev["is_primary"] = (dev["device_id"] == device_id)
        logger.info(f"Device '{device_id}' is now designated as PRIMARY device.")
        return True

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
        self.device_sockets[device_id] = websocket
        now = time.time()
        plat = platform.lower().strip()
        caps = capabilities or DEFAULT_CAPABILITIES.get(plat, ["apps", "media", "system"])
        is_first = len(self.devices) == 0

        if device_id in self.devices:
            self.devices[device_id]["status"] = "online"
            self.devices[device_id]["last_seen"] = now
            if name and name != "Windows PC":
                self.devices[device_id]["name"] = name
            if os_version:
                self.devices[device_id]["os_version"] = os_version
            if caps:
                self.devices[device_id]["capabilities"] = caps
            self.devices[device_id]["agent_version"] = agent_version or "2.0.0"
        else:
            # Auto-register connecting workstation / agent
            self.devices[device_id] = {
                "device_id": device_id,
                "name": name,
                "token": token,
                "platform": plat,
                "os_version": os_version or ("Windows 11" if plat == "windows" else plat.capitalize()),
                "agent_version": agent_version or "2.0.0",
                "capabilities": caps,
                "is_primary": is_first,
                "paired_at": now,
                "last_seen": now,
                "status": "online",
                "telemetry": {},
                "connection_id": f"conn_{int(now*1000)}",
            }

        logger.info(f"Device '{device_id}' ({name} - {plat}) connected via WebSocket. Capabilities: {caps}")

    def unregister_device_socket(self, device_id: str, websocket: Optional[WebSocket] = None):
        """Handle device socket disconnection safely without removing replaced connections."""
        current_socket = self.device_sockets.get(device_id)
        if websocket is None or current_socket is websocket:
            self.device_sockets.pop(device_id, None)
            if device_id in self.devices:
                self.devices[device_id]["status"] = "offline"
                self.devices[device_id]["last_seen"] = time.time()
            logger.info(f"Device '{device_id}' disconnected from WebSocket.")
        else:
            logger.info(f"Stale disconnect ignored for device '{device_id}' (socket already replaced).")

    def update_heartbeat(self, device_id: str, telemetry: Optional[Dict[str, Any]] = None):
        """Update last seen timestamp and telemetry for an active device."""
        now = time.time()
        if device_id in self.devices:
            self.devices[device_id]["status"] = "online"
            self.devices[device_id]["last_seen"] = now
            if telemetry:
                self.devices[device_id]["telemetry"] = telemetry

    def get_devices(self) -> list[Dict[str, Any]]:
        """Return list of all registered devices with full multi-device model & capabilities."""
        now = time.time()
        device_list = []
        for dev_id, info in self.devices.items():
            is_socket_active = dev_id in self.device_sockets
            is_recent = (now - info.get("last_seen", 0)) < HEARTBEAT_TIMEOUT
            is_online = is_socket_active and is_recent
            status = "online" if is_online else "offline"

            device_list.append({
                "device_id": dev_id,
                "name": info.get("name", "Windows PC"),
                "platform": info.get("platform", "windows"),
                "os_version": info.get("os_version", "Windows 11"),
                "agent_version": info.get("agent_version", "2.0.0"),
                "capabilities": info.get("capabilities", DEFAULT_CAPABILITIES.get(info.get("platform", "windows"), [])),
                "is_primary": info.get("is_primary", False),
                "status": status,
                "online": is_online,
                "last_seen": info.get("last_seen", 0),
                "telemetry": info.get("telemetry", {}),
            })
        return device_list

    def get_online_device(self, device_id: Optional[str] = None) -> Optional[Tuple[str, WebSocket]]:
        """Return target device ID and active WebSocket if online."""
        now = time.time()
        if device_id and device_id in self.device_sockets:
            info = self.devices.get(device_id, {})
            if (now - info.get("last_seen", 0)) < HEARTBEAT_TIMEOUT:
                return device_id, self.device_sockets[device_id]
            else:
                return None

        # Return primary online device first if available
        for dev_id, ws in list(self.device_sockets.items()):
            info = self.devices.get(dev_id, {})
            if info.get("is_primary") and (now - info.get("last_seen", 0)) < HEARTBEAT_TIMEOUT:
                return dev_id, ws

        # Return first available online device
        for dev_id, ws in list(self.device_sockets.items()):
            info = self.devices.get(dev_id, {})
            if (now - info.get("last_seen", 0)) < HEARTBEAT_TIMEOUT:
                return dev_id, ws

        return None

    def get_device_for_capability(self, capability: str, preferred_device_id: Optional[str] = None) -> Optional[Tuple[str, WebSocket]]:
        """Find an online device that supports the requested capability."""
        now = time.time()
        cap = capability.lower().strip()

        # 1. Check preferred device if specified
        if preferred_device_id and preferred_device_id in self.device_sockets:
            info = self.devices.get(preferred_device_id, {})
            if (now - info.get("last_seen", 0)) < HEARTBEAT_TIMEOUT:
                caps = [c.lower() for c in info.get("capabilities", [])]
                if cap in caps:
                    return preferred_device_id, self.device_sockets[preferred_device_id]

        # 2. Check primary device if online and capable
        for dev_id, ws in list(self.device_sockets.items()):
            info = self.devices.get(dev_id, {})
            if info.get("is_primary") and (now - info.get("last_seen", 0)) < HEARTBEAT_TIMEOUT:
                caps = [c.lower() for c in info.get("capabilities", [])]
                if cap in caps:
                    return dev_id, ws

        # 3. Check any online device matching capability
        for dev_id, ws in list(self.device_sockets.items()):
            info = self.devices.get(dev_id, {})
            if (now - info.get("last_seen", 0)) < HEARTBEAT_TIMEOUT:
                caps = [c.lower() for c in info.get("capabilities", [])]
                if cap in caps:
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

