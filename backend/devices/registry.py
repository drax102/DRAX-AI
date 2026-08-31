"""
backend/devices/registry.py — Universal cloud device registry & session manager.
Supports multiple simultaneous devices, capability profiles, persistent SQLite sync,
lightweight heartbeats, pairing codes, and command idempotency tracking.
"""

import asyncio
import random
import string
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any

from backend.devices.models import Device, CommandRecord
from backend.database.db import (
    upsert_device_db, get_device_db, get_all_devices_db,
    set_primary_device_db, update_device_status_db,
    save_command_db, get_command_db, update_command_db
)
from backend.core.logger import get_logger

logger = get_logger(__name__)

# Heartbeat timeout in seconds (after which device is considered offline if socket is quiet)
HEARTBEAT_TIMEOUT_SECONDS = 45.0

# Standard capability defaults for supported platforms
PLATFORM_DEFAULT_CAPABILITIES: Dict[str, List[str]] = {
    "windows": ["apps", "browser", "media", "volume", "screen", "files", "system", "telemetry", "notifications"],
    "macos": ["apps", "browser", "media", "volume", "screen", "files", "system", "telemetry", "notifications"],
    "linux": ["apps", "browser", "media", "volume", "screen", "files", "system", "telemetry", "notifications"],
    "android": ["calls", "sms", "notifications", "location", "camera", "media", "apps"],
    "web": ["web", "dashboard", "chat"],
}


class DeviceRegistry:
    """Central Device Registry managing active workstations, WebSockets, and capability states."""

    def __init__(self):
        # device_id -> Device instance
        self._devices: Dict[str, Device] = {}
        # device_id -> WebSocket
        self._sockets: Dict[str, Any] = {}
        # pairing_code -> dict
        self._pairing_codes: Dict[str, Dict[str, Any]] = {}
        # request_id -> asyncio.Future
        self._pending_requests: Dict[str, asyncio.Future] = {}
        # command_id -> CommandRecord (in-memory fast idempotency cache)
        self._commands_cache: Dict[str, CommandRecord] = {}

        self._load_from_db()

    def _load_from_db(self):
        """Pre-populate registry from persistent database."""
        try:
            db_devs = get_all_devices_db()
            for d in db_devs:
                dev = Device(
                    device_id=d["device_id"],
                    device_name=d.get("device_name", "Windows PC"),
                    platform=d.get("platform", "windows"),
                    os_version=d.get("os_version", ""),
                    agent_version=d.get("agent_version", "2.0.0"),
                    status="offline",  # Sockets must reconnect on process startup
                    capabilities=d.get("capabilities", PLATFORM_DEFAULT_CAPABILITIES.get(d.get("platform", "windows"), [])),
                    last_seen=d.get("last_seen", ""),
                    is_primary=bool(d.get("is_primary", False)),
                    connection_id=d.get("connection_id", ""),
                    token=d.get("token", ""),
                )
                self._devices[dev.device_id] = dev
        except Exception as e:
            logger.warning(f"Could not load devices from database at startup: {e}")

    # ── Device Registration & Lifecycle ───────────────────────────────────────

    def register_device(
        self,
        device_id: str,
        device_name: str = "Windows PC",
        platform: str = "windows",
        os_version: str = "Windows 11",
        agent_version: str = "2.0.0",
        capabilities: Optional[List[str]] = None,
        token: str = "",
        connection_id: str = "",
        status: str = "online",
    ) -> Device:
        """Register or update an agent device in memory and SQLite database."""
        plat = platform.lower().strip()
        caps = capabilities if capabilities is not None else PLATFORM_DEFAULT_CAPABILITIES.get(plat, ["apps", "media", "system"])
        now_iso = datetime.now(timezone.utc).isoformat()
        is_first = (len(self._devices) == 0) or not any(
            (d.get("is_primary") if isinstance(d, dict) else d.is_primary) for d in self._devices.values()
        )

        existing = self._devices.get(device_id)
        is_primary = (existing.get("is_primary") if isinstance(existing, dict) else existing.is_primary) if existing else is_first

        device = Device(
            device_id=device_id,
            device_name=device_name or "Windows PC",
            platform=plat,
            os_version=os_version or ("Windows 11" if plat == "windows" else plat.capitalize()),
            agent_version=agent_version or "2.0.0",
            status=status,
            capabilities=caps,
            last_seen=now_iso,
            is_primary=is_primary,
            connection_id=connection_id or f"conn_{int(time.time()*1000)}",
            token=token,
        )
        self._devices[device_id] = device

        # Persist to database
        try:
            upsert_device_db(
                device_id=device.device_id,
                device_name=device.device_name,
                platform=device.platform,
                os_version=device.os_version,
                agent_version=device.agent_version,
                status=status,
                capabilities=device.capabilities,
                last_seen=device.last_seen,
                is_primary=device.is_primary,
                connection_id=device.connection_id,
                token=device.token,
            )
        except Exception as e:
            logger.error(f"Failed to persist device '{device_id}' to DB: {e}")

        logger.info(f"Registered device '{device_id}' ({device_name} - {plat}). Primary: {is_primary}. Capabilities: {caps}")
        return device

    def update_heartbeat(self, device_id: str, timestamp: Optional[str] = None, telemetry: Optional[Dict[str, Any]] = None):
        """Update last seen timestamp and optional telemetry for an active device."""
        now_iso = timestamp or datetime.now(timezone.utc).isoformat()
        if device_id in self._devices:
            dev = self._devices[device_id]
            if isinstance(dev, dict):
                dev["status"] = "online"
                dev["last_seen"] = now_iso
                if telemetry:
                    dev["telemetry"] = telemetry
            else:
                dev.status = "online"
                dev.last_seen = now_iso
                if telemetry:
                    dev.telemetry = telemetry
            try:
                update_device_status_db(device_id, "online", last_seen=now_iso)
            except Exception as e:
                logger.warning(f"Failed to update heartbeat in DB for '{device_id}': {e}")

    def mark_offline(self, device_id: str):
        """Mark device offline on WebSocket disconnect."""
        now_iso = datetime.now(timezone.utc).isoformat()
        if device_id in self._devices:
            dev = self._devices[device_id]
            if isinstance(dev, dict):
                dev["status"] = "offline"
                dev["last_seen"] = now_iso
            else:
                dev.status = "offline"
                dev.last_seen = now_iso
            try:
                update_device_status_db(device_id, "offline", last_seen=now_iso)
            except Exception as e:
                logger.warning(f"Failed to mark device '{device_id}' offline in DB: {e}")
        logger.info(f"Device '{device_id}' marked offline.")

    def set_primary_device(self, device_id: str) -> bool:
        """Designate target device as primary device (only one device is primary)."""
        if device_id not in self._devices:
            # Check DB
            db_dev = get_device_db(device_id)
            if not db_dev:
                return False

        for dev in self._devices.values():
            if isinstance(dev, dict):
                dev["is_primary"] = (dev.get("device_id") == device_id)
            else:
                dev.is_primary = (dev.device_id == device_id)

        try:
            set_primary_device_db(device_id)
        except Exception as e:
            logger.error(f"Failed to set primary device in DB: {e}")

        logger.info(f"Device '{device_id}' designated as PRIMARY device.")
        return True

    def get_device(self, device_id: str) -> Optional[Any]:
        """Fetch device by ID."""
        if device_id in self._devices:
            return self._devices[device_id]
        db_dev = get_device_db(device_id)
        if db_dev:
            dev = Device(
                device_id=db_dev["device_id"],
                device_name=db_dev.get("device_name", "Windows PC"),
                platform=db_dev.get("platform", "windows"),
                os_version=db_dev.get("os_version", ""),
                agent_version=db_dev.get("agent_version", "2.0.0"),
                status=db_dev.get("status", "offline"),
                capabilities=db_dev.get("capabilities", []),
                last_seen=db_dev.get("last_seen", ""),
                is_primary=bool(db_dev.get("is_primary", False)),
                connection_id=db_dev.get("connection_id", ""),
                token=db_dev.get("token", ""),
            )
            self._devices[dev.device_id] = dev
            return dev
        return None

    def get_all_devices(self) -> List[Any]:
        """Return list of all registered devices."""
        return list(self._devices.values())

    def get_online_devices(self) -> List[Any]:
        """Return list of all currently active & online devices with connected sockets."""
        online_list = []
        for dev_id, dev in self._devices.items():
            st = dev.get("status") if isinstance(dev, dict) else dev.status
            if dev_id in self._sockets and st == "online":
                online_list.append(dev)
        return online_list

    def get_primary_device(self) -> Optional[Any]:
        """Return primary device if designated and online."""
        for dev in self._devices.values():
            is_prim = dev.get("is_primary") if isinstance(dev, dict) else dev.is_primary
            dev_id = dev.get("device_id") if isinstance(dev, dict) else dev.device_id
            st = dev.get("status") if isinstance(dev, dict) else dev.status
            if is_prim and dev_id in self._sockets and st == "online":
                return dev
        return None

    # ── WebSocket Connection Management ───────────────────────────────────────

    def register_socket(self, device_id: str, websocket: Any):
        """Record active WebSocket connection for a device."""
        self._sockets[device_id] = websocket

    def unregister_socket(self, device_id: str, websocket: Optional[Any] = None):
        """Remove WebSocket connection safely."""
        current = self._sockets.get(device_id)
        if websocket is None or current is websocket:
            self._sockets.pop(device_id, None)
            self.mark_offline(device_id)

    def get_socket(self, device_id: str) -> Optional[Any]:
        """Get active WebSocket for a device if connected."""
        return self._sockets.get(device_id)

    # ── Pairing Codes ─────────────────────────────────────────────────────────

    def generate_pairing_code(
        self,
        device_id: str = "",
        device_name: str = "Windows PC",
        token: str = "",
        platform: str = "windows",
        capabilities: Optional[List[str]] = None,
    ) -> str:
        """Generate a temporary 4-character pairing code (e.g. DRAX-7K92)."""
        chars = string.ascii_uppercase + "23456789"
        code_suffix = "".join(random.choices(chars, k=4))
        code = f"DRAX-{code_suffix}"
        plat_clean = platform.lower().strip()

        self._pairing_codes[code] = {
            "device_id": device_id or f"drax_{plat_clean}_{code_suffix.lower()}",
            "device_name": device_name,
            "token": token,
            "platform": plat_clean,
            "capabilities": capabilities or PLATFORM_DEFAULT_CAPABILITIES.get(plat_clean, ["apps", "media", "system"]),
            "expires_at": time.time() + 600,
        }
        logger.info(f"Generated pairing code '{code}' for '{device_name}' ({plat_clean})")
        return code

    def verify_and_pair(self, pairing_code: str) -> Optional[Dict[str, Any]]:
        """Validate pairing code from web client and register device."""
        code = pairing_code.strip().upper()
        record = self._pairing_codes.get(code)
        if not record:
            return None

        if time.time() > record["expires_at"]:
            del self._pairing_codes[code]
            return None

        device_id = record["device_id"]
        is_online = device_id in self._sockets
        dev = self.register_device(
            device_id=device_id,
            device_name=record["device_name"],
            platform=record["platform"],
            capabilities=record["capabilities"],
            token=record["token"],
            status="online" if is_online else "offline",
        )
        del self._pairing_codes[code]
        return dev.to_dict()

    # ── Command Tracking & Idempotency ────────────────────────────────────────

    def get_command(self, command_id: str) -> Optional[CommandRecord]:
        """Fetch command record from memory cache or database."""
        if command_id in self._commands_cache:
            return self._commands_cache[command_id]
        db_cmd = get_command_db(command_id)
        if db_cmd:
            rec = CommandRecord(
                command_id=db_cmd["command_id"],
                command=db_cmd["command"],
                intent=db_cmd.get("intent", ""),
                device_id=db_cmd.get("device_id"),
                status=db_cmd.get("status", "queued"),
                result=db_cmd.get("result", ""),
                error=db_cmd.get("error"),
                created_at=db_cmd.get("created_at", ""),
                updated_at=db_cmd.get("updated_at", ""),
            )
            self._commands_cache[command_id] = rec
            return rec
        return None

    def record_command(
        self,
        command_id: str,
        command: str,
        intent: str = "",
        device_id: Optional[str] = None,
        status: str = "queued",
        result: str = "",
        error: Optional[str] = None,
    ) -> CommandRecord:
        """Create or update a command record for idempotency tracking."""
        now_iso = datetime.now(timezone.utc).isoformat()
        rec = CommandRecord(
            command_id=command_id,
            command=command,
            intent=intent,
            device_id=device_id,
            status=status,
            result=result,
            error=error,
            created_at=now_iso,
            updated_at=now_iso,
        )
        self._commands_cache[command_id] = rec
        try:
            save_command_db(command_id, command, intent, device_id, status, result, error)
        except Exception as e:
            logger.error(f"Failed to record command in DB: {e}")
        return rec

    def update_command_status(
        self,
        command_id: str,
        status: str,
        result: str = "",
        error: Optional[str] = None,
    ) -> bool:
        """Update lifecycle status of an existing command record."""
        now_iso = datetime.now(timezone.utc).isoformat()
        if command_id in self._commands_cache:
            rec = self._commands_cache[command_id]
            rec.status = status
            if result:
                rec.result = result
            if error is not None:
                rec.error = error
            rec.updated_at = now_iso

        try:
            return update_command_db(command_id, status, result, error)
        except Exception as e:
            logger.error(f"Failed to update command in DB: {e}")
            return False

    # ── Command Request Futures (Async Correlation) ───────────────────────────

    def create_pending_request(self, request_id: str) -> asyncio.Future:
        """Create a Future to await an asynchronous command result from a device."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        fut = loop.create_future()
        self._pending_requests[request_id] = fut
        return fut

    def resolve_pending_request(
        self,
        request_id: str,
        result: str,
        success: bool = True,
        error: Optional[Any] = None,
    ):
        """Resolve a pending request Future with incoming device result."""
        fut = self._pending_requests.pop(request_id, None)
        if fut and not fut.done():
            fut.set_result({
                "result": result,
                "response": result,
                "success": success,
                "error": error,
            })


# Global singleton instance
device_registry = DeviceRegistry()
