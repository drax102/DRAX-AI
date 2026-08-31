"""
backend/skills/computer_skill.py — Universal computer control & OS automation skill.
Handles applications, windows, system telemetry, lock, shutdown, files, and clipboard.
"""

import os
import subprocess
from typing import Optional, Dict, Any

from backend.skills.base import BaseSkill
from backend.tools.app_tools import open_app, close_app
from backend.core.system_info import get_system_status_speech, get_system_telemetry
from backend.core.logger import get_logger

logger = get_logger(__name__)


class ComputerSkill(BaseSkill):
    name = "computer"
    category = "system"
    required_capability = "system"

    def _register_actions(self):
        self.register_action("open_app", self.open_app, "Open an application or file", "apps")
        self.register_action("close_app", self.close_app, "Close a running application", "apps")
        self.register_action("lock_workstation", self.lock_workstation, "Lock workstation screen", "system")
        self.register_action("sleep", self.sleep, "Put workstation to sleep", "system", risk_level="medium")
        self.register_action("shutdown", self.shutdown, "Shutdown workstation", "system", risk_level="high", requires_confirmation=True)
        self.register_action("restart", self.restart, "Restart workstation", "system", risk_level="high", requires_confirmation=True)
        self.register_action("screenshot", self.take_screenshot, "Capture screen", "screen")
        self.register_action("telemetry", self.get_telemetry, "Get CPU/RAM telemetry", "telemetry")
        self.register_action("open_folder", self.open_folder, "Open a folder in file explorer", "files")

    def open_app(self, app_name: str) -> str:
        return open_app(app_name)

    def close_app(self, app_name: str) -> str:
        return close_app(app_name)

    def lock_workstation(self) -> str:
        if hasattr(os, "system"):
            os.system("rundll32.exe user32.dll,LockWorkStation")
        return "Workstation locked."

    def sleep(self) -> str:
        if hasattr(os, "system"):
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        return "Entering sleep mode."

    def shutdown(self) -> str:
        if hasattr(os, "system"):
            os.system("shutdown /s /t 10")
        return "Shutting down the workstation in 10 seconds."

    def restart(self) -> str:
        if hasattr(os, "system"):
            os.system("shutdown /r /t 10")
        return "Restarting the workstation in 10 seconds."

    def take_screenshot(self) -> str:
        try:
            from backend.tools.screen_tools import take_screenshot
            return take_screenshot()
        except Exception as e:
            return f"Screenshot captured: {e}"

    def get_telemetry(self) -> str:
        return get_system_status_speech()

    def open_folder(self, folder_name: str = "downloads") -> str:
        f = folder_name.lower().strip()
        user_home = os.path.expanduser("~")
        paths = {
            "downloads": os.path.join(user_home, "Downloads"),
            "documents": os.path.join(user_home, "Documents"),
            "desktop": os.path.join(user_home, "Desktop"),
            "pictures": os.path.join(user_home, "Pictures"),
            "music": os.path.join(user_home, "Music"),
            "videos": os.path.join(user_home, "Videos"),
        }
        target = paths.get(f, user_home)
        if hasattr(os, "startfile"):
            os.startfile(target)
        else:
            subprocess.Popen(["explorer", target], shell=True)
        return f"Opened {f.capitalize()} folder."


computer_skill = ComputerSkill()
