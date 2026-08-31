"""
autostart.py — Windows Registry startup manager for DRAX AI.
Enables or disables starting Drax AI automatically on Windows boot.
"""

import os
import sys
import winreg
from backend.core.logger import get_logger

logger = get_logger(__name__)

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "DraxAI"


def is_autostart_enabled() -> bool:
    """Check if Drax AI is registered to run on Windows startup."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, APP_NAME)
            return True
    except FileNotFoundError:
        return False
    except Exception as e:
        logger.warning(f"Failed to query startup registry: {e}")
        return False


def set_autostart(enabled: bool) -> bool:
    """Enable or disable Windows autostart for Drax AI."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                if hasattr(sys, "_MEIPASS") or getattr(sys, "frozen", False):
                    cmd = f'"{sys.executable}"'
                else:
                    # Point to pythonw in current venv running desktop_app.py
                    venv_pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
                    if not os.path.exists(venv_pythonw):
                        venv_pythonw = sys.executable
                    app_py = os.path.abspath("desktop_app.py")
                    cmd = f'"{venv_pythonw}" "{app_py}"'

                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
                logger.info(f"Registered Windows startup command: {cmd}")
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                    logger.info("Removed Drax AI from Windows startup.")
                except FileNotFoundError:
                    pass
            return True
    except Exception as e:
        logger.error(f"Failed to set autostart registry state ({enabled}): {e}")
        return False
