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


class DeviceManager:
    """Manages paired Windows agents, active WebSocket connections, and command routing."""

    def __init__(self):
        # device_id -> { "device_id": str, "name": str, "token": str, "platform": str,
        #                 "agent_version": str, "paired_at": float, "last_seen": float,
        #                 "status": "online"|"offline", "telemetry": dict }
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
        platform: str = "Windows",
    ) -> str:
        """Generate a 4-character alphanumeric pairing code (e.g. DRAX-7K92)."""
        chars = string.ascii_uppercase + "23456789"
        code_suffix = "".join(random.choices(chars, k=4))
        code = f"DRAX-{code_suffix}"

        self.pairing_codes[code] = {
            "device_id": device_id or f"drax_pc_{code_suffix.lower()}",
            "device_name": device_name,
            "token": token,
            "platform": platform,
            "expires_at": time.time() + 600,  # 10 minutes validity
        }
        logger.info(f"Generated pairing code '{code}' for device '{device_name}' ({device_id})")
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
        self.devices[device_id] = {
            "device_id": device_id,
            "name": record["device_name"],
            "token": record["token"],
            "platform": record.get("platform", "Windows"),
            "agent_version": "2.0.0",
            "paired_at": time.time(),
            "last_seen": time.time(),
            "status": "online" if is_online else "offline",
            "telemetry": {},
        }
        del self.pairing_codes[code]
        logger.info(f"Successfully paired device '{record['device_name']}' ({device_id})")
        return self.devices[device_id]

    def register_device_socket(
        self,
        device_id: str,
        websocket: WebSocket,
        name: str = "Windows PC",
        platform: str = "Windows",
        token: str = "",
    ):
        """Register active WebSocket connection for a device."""
        self.device_sockets[device_id] = websocket
        now = time.time()

        if device_id in self.devices:
            self.devices[device_id]["status"] = "online"
            self.devices[device_id]["last_seen"] = now
            if name and name != "Windows PC":
                self.devices[device_id]["name"] = name
        else:
            # Auto-register connecting workstation
            self.devices[device_id] = {
                "device_id": device_id,
                "name": name,
                "token": token,
                "platform": platform,
                "agent_version": "2.0.0",
                "paired_at": now,
                "last_seen": now,
                "status": "online",
                "telemetry": {},
            }

        logger.info(f"Device '{device_id}' ({name}) connected via WebSocket.")

    def unregister_device_socket(self, device_id: str):
        """Handle device socket disconnection."""
        if device_id in self.device_sockets:
            del self.device_sockets[device_id]
        if device_id in self.devices:
            self.devices[device_id]["status"] = "offline"
            self.devices[device_id]["last_seen"] = time.time()
        logger.info(f"Device '{device_id}' disconnected from WebSocket.")

    def update_heartbeat(self, device_id: str, telemetry: Optional[Dict[str, Any]] = None):
        """Update last seen timestamp and telemetry for an active device."""
        now = time.time()
        if device_id in self.devices:
            self.devices[device_id]["status"] = "online"
            self.devices[device_id]["last_seen"] = now
            if telemetry:
                self.devices[device_id]["telemetry"] = telemetry

    def get_devices(self) -> list[Dict[str, Any]]:
        """Return list of all registered devices with current live status."""
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
                "platform": info.get("platform", "Windows"),
                "status": status,
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
                # Stale connection
                return None

        # Return first available online device
        for dev_id, ws in list(self.device_sockets.items()):
            info = self.devices.get(dev_id, {})
            if (now - info.get("last_seen", 0)) < HEARTBEAT_TIMEOUT:
                return dev_id, ws

        return None

    def create_pending_request(self, request_id: str) -> asyncio.Future:
        """Create a Future to wait for a command result from a Windows Agent."""
        try:
            loop = asyncio.get_running_loop()
            fut = loop.create_future()
        except RuntimeError:
            fut = asyncio.Future()
        self.pending_requests[request_id] = fut
        return fut

    def resolve_pending_request(self, request_id: str, result: str, success: bool = True):
        """Resolve pending command Future with result from Windows Agent."""
        fut = self.pending_requests.pop(request_id, None)
        if fut and not fut.done():
            fut.set_result({"result": result, "success": success})


device_manager = DeviceManager()

