"""
backend/devices — Universal Multi-Device Registry and Capability Routing System.
"""

from backend.devices.models import Device, CommandRecord
from backend.devices.registry import DeviceRegistry, device_registry, PLATFORM_DEFAULT_CAPABILITIES
from backend.devices.router import CapabilityRouter, find_device_for_capability, INTENT_CAPABILITY_MAP

__all__ = [
    "Device",
    "CommandRecord",
    "DeviceRegistry",
    "device_registry",
    "PLATFORM_DEFAULT_CAPABILITIES",
    "CapabilityRouter",
    "find_device_for_capability",
    "INTENT_CAPABILITY_MAP",
]
