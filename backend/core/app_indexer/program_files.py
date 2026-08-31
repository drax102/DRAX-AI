"""
program_files.py — Deep scanner for all .exe applications across Program Files, LocalAppData, and drives.
"""

import os
from backend.core.logger import get_logger

logger = get_logger(__name__)

EXCLUDE_KEYWORDS = [
    "uninstall", "unins000", "uninst", "helper", "crashpad", "update", "updater",
    "installer", "setup", "vcredist", "dxsetup", "node_modules", ".git", "venv",
    "__pycache__", "temp", "cache", "touchpad", "driver", "agent_service",
    "cef_isolate", "elevated", "broker", "notification", "service", "daemon"
]


def scan_program_directories() -> list[dict]:
    """Scan all Program Files, LocalAppData, and drive app folders for executables."""
    results = []
    seen_targets = set()

    scan_roots = [
        r"C:\Program Files",
        r"C:\Program Files (x86)",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs"),
        os.path.expandvars(r"%APPDATA%"),
        r"D:\Games",
        r"D:\Program Files",
        r"D:\Programs",
    ]

    for root_folder in scan_roots:
        if not os.path.exists(root_folder):
            continue

        try:
            for root, dirs, files in os.walk(root_folder):
                dirs[:] = [d for d in dirs if d.lower() not in ["node_modules", ".git", "venv", "__pycache__", "temp", "cache", "site-packages", "lib"]]

                for file in files:
                    if file.lower().endswith(".exe"):
                        exe_name = file[:-4].strip()
                        exe_lower = exe_name.lower()

                        if any(w in exe_lower for w in EXCLUDE_KEYWORDS):
                            continue

                        full_path = os.path.join(root, file)
                        if full_path in seen_targets:
                            continue
                        seen_targets.add(full_path)

                        parent_folder = os.path.basename(root)
                        display = parent_folder if parent_folder.lower() not in ["bin", "application", "app", "cmd", "x64", "x86"] else exe_name
                        display = display.replace("-", " ").replace("_", " ").title()

                        aliases = [exe_lower, display.lower()]
                        
                        # Extra game and tool aliases
                        parent_lower = parent_folder.lower()
                        if "grand theft auto v" in parent_lower or "gta v" in parent_lower or "gta 5" in parent_lower or "gta5" in exe_lower or "playgtav" in exe_lower:
                            aliases.extend(["gta v", "gta 5", "gtav", "gta", "grand theft auto v", "grand theft auto 5", "playgtav", "gta5"])
                        elif "grand theft auto iv" in parent_lower or "gta iv" in parent_lower or "gta 4" in parent_lower or "gtaiv" in exe_lower:
                            aliases.extend(["gta iv", "gta 4", "gtaiv", "grand theft auto iv", "grand theft auto 4"])
                        elif "san andreas" in parent_lower or "gta_sa" in exe_lower:
                            aliases.extend(["gta sa", "gta san andreas", "grand theft auto san andreas"])

                        results.append({
                            "name": exe_lower,
                            "display_name": display,
                            "aliases": list(set(aliases)),
                            "type": "executable",
                            "target": full_path,
                            "source": "program_files",
                        })
        except Exception as e:
            logger.warning(f"Error scanning {root_folder}: {e}")

    logger.info(f"Program directories scan discovered {len(results)} executables.")
    return results
