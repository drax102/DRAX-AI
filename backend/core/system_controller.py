"""
system_controller.py — Safe system control actions (telemetry, volume, system power).
"""

import os
import subprocess
from backend.core.config import settings
from backend.core.logger import get_logger
from backend.core.system_info import get_system_telemetry, get_system_status_speech, change_volume

logger = get_logger(__name__)


def handle_system_command(command: str) -> str | tuple[str, str]:
    """
    Handle system level commands.
    Returns response string OR tuple (response_string, "NEEDS_CONFIRMATION:<action>") for dangerous actions.
    """
    cmd = command.lower().strip()

    # Telemetry
    if any(k in cmd for k in ["status", "system status", "telemetry", "cpu", "ram", "memory"]):
        return get_system_status_speech()

    # Volume
    if "volume" in cmd or "mute" in cmd:
        if "up" in cmd or "increase" in cmd or "raise" in cmd:
            return change_volume("up")
        elif "down" in cmd or "decrease" in cmd or "lower" in cmd:
            return change_volume("down")
        elif "mute" in cmd or "unmute" in cmd:
            return change_volume("mute")
        else:
            return change_volume("up")

    # Dangerous commands — require confirmation
    confirm_required = settings.get("assistant", "confirm_dangerous_commands", True)

    if "shutdown" in cmd or "power off" in cmd or "turn off computer" in cmd:
        if confirm_required:
            return ("Are you sure you want to shut down your computer?", "CONFIRM_SHUTDOWN")
        else:
            return execute_shutdown()

    if "restart" in cmd or "reboot" in cmd:
        if confirm_required:
            return ("Are you sure you want to restart your computer?", "CONFIRM_RESTART")
        else:
            return execute_restart()

    if "lock" in cmd or "lock computer" in cmd or "lock screen" in cmd:
        return execute_lock()

    return "System command not recognized."


def execute_shutdown() -> str:
    logger.warning("Executing system shutdown")
    os.system("shutdown /s /t 10")
    return "Shutting down the system in 10 seconds."


def execute_restart() -> str:
    logger.warning("Executing system restart")
    os.system("shutdown /r /t 10")
    return "Restarting the system in 10 seconds."


def execute_lock() -> str:
    logger.info("Executing system lock")
    os.system("rundll32.exe user32.dll,LockWorkStation")
    return "Locking the workstation."
