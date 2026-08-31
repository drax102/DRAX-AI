"""
uwp.py — Windows UWP / Store App Scanner.
"""

import subprocess
from backend.core.logger import get_logger

logger = get_logger(__name__)


def scan_uwp_apps() -> list[dict]:
    """Scan UWP Apps using PowerShell Get-StartApps."""
    results = []
    try:
        cmd = 'powershell -NoProfile -Command "Get-StartApps | ConvertTo-Json"'
        out = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL)
        import json

        data = json.loads(out)
        if isinstance(data, dict):
            data = [data]

        for item in data:
            name = item.get("Name", "")
            appid = item.get("AppID", "")
            if not name or not appid:
                continue

            name_lower = name.lower().strip()
            if any(w in name_lower for w in ["uninstall", "help", "readme"]):
                continue

            target = f"shell:AppsFolder\\{appid}"
            results.append({
                "name": name_lower,
                "display_name": name,
                "aliases": [name_lower],
                "type": "uwp",
                "target": target,
                "source": "uwp",
            })
    except Exception as e:
        logger.warning(f"UWP app scanning failed: {e}")

    return results
