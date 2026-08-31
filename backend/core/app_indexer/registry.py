"""
registry.py — Windows Registry App Paths scanner.
"""

import os

try:
    import winreg
    HAS_WINREG = True
except ImportError:
    HAS_WINREG = False

from backend.core.logger import get_logger

logger = get_logger(__name__)


def scan_registry_app_paths() -> list[dict]:
    """Scan HKLM and HKCU App Paths keys in Windows Registry."""
    if not HAS_WINREG:
        return []

    results = []
    reg_paths = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths"),
    ]

    for hkey, subkey_path in reg_paths:
        try:
            key = winreg.OpenKey(hkey, subkey_path)
            subkeys_count, _, _ = winreg.QueryInfoKey(key)
            for i in range(subkeys_count):
                try:
                    app_exe = winreg.EnumKey(key, i)
                    app_key = winreg.OpenKey(key, app_exe)
                    try:
                        path, _ = winreg.QueryValueEx(app_key, "")
                        if path and os.path.exists(path):
                            name_raw = app_exe.replace(".exe", "").replace(".EXE", "")
                            name_lower = name_raw.lower().strip()
                            results.append({
                                "name": name_lower,
                                "display_name": name_raw.capitalize(),
                                "aliases": [name_lower, app_exe.lower()],
                                "type": "executable",
                                "target": path,
                                "source": "registry",
                            })
                    finally:
                        winreg.CloseKey(app_key)
                except Exception:
                    continue
            winreg.CloseKey(key)
        except Exception:
            continue

    return results
