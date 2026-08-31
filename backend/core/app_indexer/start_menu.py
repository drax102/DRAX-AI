"""
start_menu.py — Start Menu shortcut scanner for Windows.
"""

import os

try:
    import pythoncom
    import win32com.client
    HAS_WIN32COM = True
except ImportError:
    HAS_WIN32COM = False

from backend.core.logger import get_logger

logger = get_logger(__name__)


def resolve_shortcut(path: str) -> str:
    """Resolve .lnk shortcut path to actual target path."""
    if not HAS_WIN32COM or not path.lower().endswith(".lnk"):
        return path
    try:
        pythoncom.CoInitialize()
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortcut(path)
        target = shortcut.Targetpath
        return target if target else path
    except Exception:
        return path
    finally:
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass


def scan_start_menu() -> list[dict]:
    """Scan Start Menu folders for shortcuts."""
    results = []
    folders = [
        os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
        os.path.expandvars(r"%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs"),
    ]

    for folder in folders:
        if not os.path.exists(folder):
            continue
        for root_dir, _, files in os.walk(folder):
            for file in files:
                if file.lower().endswith(".lnk"):
                    name_raw = file[:-4]
                    name_lower = name_raw.lower().strip()
                    if any(w in name_lower for w in ["uninstall", "help", "readme", "documentation"]):
                        continue

                    full_path = os.path.join(root_dir, file)
                    target = resolve_shortcut(full_path)

                    target_final = target if (target and os.path.exists(target)) else full_path

                    results.append({
                        "name": name_lower,
                        "display_name": name_raw,
                        "aliases": [name_lower],
                        "type": "shortcut" if full_path.endswith(".lnk") else "executable",
                        "target": target_final,
                        "source": "start_menu",
                    })

    return results
