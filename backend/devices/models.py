"""
backend/devices/models.py — Data models for universal multi-device registry & command tracking.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone


@dataclass
class Device:
    """Represents a registered workstation, desktop agent, or peripheral device."""
    device_id: str
    device_name: str = "Windows PC"
    platform: str = "windows"
    os_version: str = "Windows 11"
    agent_version: str = "2.0.0"
    status: str = "offline"  # "online", "offline"
    capabilities: List[str] = field(default_factory=lambda: [
        "apps", "browser", "media", "volume", "screen", "files", "system", "telemetry", "notifications"
    ])
    last_seen: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    is_primary: bool = False
    connection_id: str = ""
    token: str = ""
    telemetry: Dict[str, Any] = field(default_factory=dict)

    def __getitem__(self, key: str) -> Any:
        if key == "name":
            return self.device_name
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(key)

    def __setitem__(self, key: str, value: Any):
        if key == "name":
            self.device_name = value
        else:
            setattr(self, key, value)

    def get(self, key: str, default: Any = None) -> Any:
        if key == "name":
            return self.device_name
        if hasattr(self, key):
            return getattr(self, key)
        return default

    def to_dict(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "device_name": self.device_name,
            "name": self.device_name,
            "token": self.token,
            "platform": self.platform,
            "os_version": self.os_version,
            "agent_version": self.agent_version,
            "status": self.status,
            "online": self.status == "online",
            "capabilities": list(self.capabilities),
            "last_seen": self.last_seen,
            "is_primary": self.is_primary,
            "connection_id": self.connection_id,
            "telemetry": self.telemetry,
        }


@dataclass
class CommandRecord:
    """Represents an idempotent command execution lifecycle record."""
    command_id: str
    command: str
    intent: str = ""
    device_id: Optional[str] = None
    status: str = "queued"  # "queued", "executing", "success", "failed", "cancelled"
    result: str = ""
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
