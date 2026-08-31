"""
desktop_app.py — Production entry point for DRAX AI (Always-On Windows Assistant).
"""

import ctypes
import os
import sys

# Ensure project root is on sys.path
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMessageBox

from backend.core.config import settings
from backend.core.logger import setup_logging
from ui.main_window import DraxWindow

_MUTEX_HANDLE = None


def _acquire_single_instance_lock():
    """Ensure only one instance of Drax AI runs concurrently on this workstation."""
    global _MUTEX_HANDLE
    mutex_name = "Local\\DraxAI_SingleInstance_Mutex_v2"
    kernel32 = ctypes.windll.kernel32
    _MUTEX_HANDLE = kernel32.CreateMutexW(None, False, mutex_name)
    ERROR_ALREADY_EXISTS = 183
    if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        return False
    return True


def main():
    setup_logging()

    # Enable High DPI scaling on Windows
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("DRAX AI")
    app.setOrganizationName("Drax")

    # Prevent duplicate background processes
    if not _acquire_single_instance_lock():
        print("DRAX AI is already running in the background. Check your System Tray or say 'Hey Drax'.")
        sys.exit(0)

    # Keep app running in System Tray 24/7 even when window is hidden/closed
    app.setQuitOnLastWindowClosed(False)

    window = DraxWindow()

    hide_on_start = settings.get("ui", "hide_to_tray_on_start", False)
    if not hide_on_start:
        window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
