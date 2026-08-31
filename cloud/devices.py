"""
devices.py — Cloud device pairing and registry manager for DRAX AI.
Manages unique Windows device identities, temporary pairing codes, and active WebSocket connections.
"""

import random
import string
import time
from typing import Dict, Optional, Any
from fastapi import WebSocket

from backend.core.logger import get_logger

logger = get_logger(__name__)


class DeviceManager:
    """Manages paired Windows agents and active WebSocket connections."""

    def __init__(self):
        # device_id -> { "name": str, "token": str, "paired_at": float, "last_seen": float, "status": "online"|"offline" }
        self.devices: Dict[str, Dict[str, Any]] = {}
        # pairing_code -> { "device_id": str, "device_name": str, "token": str, "expires_at": float }
        self.pairing_codes: Dict[str, Dict[str, Any]] = {}
        # device_id -> WebSocket
        self.device_sockets: Dict[str, WebSocket] = {}
        # client_id -> WebSocket
        self.client_sockets: Dict[str, WebSocket] = {}

    def generate_pairing_code(self, device_id: str, device_name: str, token: str) -> str:
        """Generate a 4-character alphanumeric pairing code (e.g. DRAX-7K92)."""
        chars = string.ascii_uppercase + "23456789"
        code_suffix = "".join(random.choices(chars, k=4))
        code = f"DRAX-{code_suffix}"

        self.pairing_codes[code] = {
            "device_id": device_id,
            "device_name": device_name,
            "token": token,
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
        self.devices[device_id] = {
            "device_id": device_id,
            "name": record["device_name"],
            "token": record["token"],
            "paired_at": time.time(),
            "last_seen": time.time(),
            "status": "online" if device_id in self.device_sockets else "offline",
        }
        del self.pairing_codes[code]
        logger.info(f"Successfully paired device '{record['device_name']}' ({device_id})")
        return self.devices[device_id]

    def register_device_socket(self, device_id: str, websocket: WebSocket):
        self.device_sockets[device_id] = websocket
        if device_id in self.devices:
            self.devices[device_id]["status"] = "online"
            self.devices[device_id]["last_seen"] = time.time()
        logger.info(f"Device '{device_id}' connected via WebSocket.")

    def unregister_device_socket(self, device_id: str):
        if device_id in self.device_sockets:
            del self.device_sockets[device_id]
        if device_id in self.devices:
            self.devices[device_id]["status"] = "offline"
            self.devices[device_id]["last_seen"] = time.time()
        logger.info(f"Device '{device_id}' disconnected.")

    def get_devices(self) -> list[Dict[str, Any]]:
        device_list = []
        for dev_id, info in self.devices.items():
            is_online = dev_id in self.device_sockets
            device_list.append({
                "device_id": dev_id,
                "name": info.get("name", "Windows PC"),
                "status": "online" if is_online else "offline",
                "last_seen": info.get("last_seen", 0),
            })
        return device_list

    def get_online_device(self, device_id: Optional[str] = None) -> Optional[tuple[str, WebSocket]]:
        """Return target device ID and active WebSocket."""
        if device_id and device_id in self.device_sockets:
            return device_id, self.device_sockets[device_id]
        # Return first available online device
        if self.device_sockets:
            first_id = next(iter(self.device_sockets))
            return first_id, self.device_sockets[first_id]
        return None


device_manager = DeviceManager()
