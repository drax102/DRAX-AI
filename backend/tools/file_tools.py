"""
file_tools.py — Windows file search, opener, and directory navigation tools.
"""

import os
from backend.agent.tool_registry import register_tool
from backend.core.logger import get_logger

logger = get_logger(__name__)

SPECIAL_FOLDERS = {
    "downloads": os.path.expanduser("~/Downloads"),
    "documents": os.path.expanduser("~/Documents"),
    "desktop": os.path.expanduser("~/Desktop"),
    "pictures": os.path.expanduser("~/Pictures"),
    "music": os.path.expanduser("~/Music"),
    "videos": os.path.expanduser("~/Videos"),
}


@register_tool(
    name="open_folder",
    description="Open a system folder like Downloads, Documents, Desktop, Pictures in File Explorer.",
    parameters={"folder_name": {"type": "string", "description": "Folder name (downloads, documents, desktop, pictures)"}},
    risk_level="low",
    category="files",
)
def open_folder(folder_name: str) -> str:
    key = folder_name.lower().strip()
    for w in ["open", "folder", "my"]:
        key = key.replace(w, "").strip()

    target_dir = SPECIAL_FOLDERS.get(key, os.path.expanduser(f"~/{key.capitalize()}"))
    if os.path.exists(target_dir):
        os.startfile(target_dir)
        return f"Opened {key.capitalize()} folder."
    return f"Folder '{folder_name}' not found."


@register_tool(
    name="find_file",
    description="Search common user directories (Downloads, Documents, Desktop) for a file by name.",
    parameters={"filename": {"type": "string", "description": "File name or keyword (e.g. resume, report.pdf)"}},
    risk_level="low",
    category="files",
)
def find_file(filename: str) -> str:
    clean = filename.lower().strip()
    for w in ["find", "search for", "locate", "my", "file"]:
        clean = clean.replace(w, "").strip()

    search_dirs = [
        os.path.expanduser("~/Desktop"),
        os.path.expanduser("~/Downloads"),
        os.path.expanduser("~/Documents"),
    ]

    matches = []
    for sdir in search_dirs:
        if not os.path.exists(sdir):
            continue
        for root_dir, _, files in os.walk(sdir):
            for f in files:
                if clean in f.lower():
                    matches.append(os.path.join(root_dir, f))
                    if len(matches) >= 5:
                        break
            if len(matches) >= 5:
                break

    if not matches:
        return f"Could not find any files matching '{filename}' in Downloads, Documents, or Desktop."

    # Open first match if single, or list matches
    if len(matches) == 1:
        os.startfile(matches[0])
        return f"Found and opened: {os.path.basename(matches[0])}"

    return f"Found {len(matches)} matching files:\n" + "\n".join([f"• {os.path.basename(m)}" for m in matches])
