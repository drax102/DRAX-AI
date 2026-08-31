"""
app_tools.py — Application lifecycle management tools.
Supports launch, safe termination (close_app), index rebuilding, and running process queries.
"""

import os
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

from backend.agent.tool_registry import register_tool
from backend.core.app_executor import open_app as executor_open_app, find_app_match
from backend.core.app_indexer import scan_and_rebuild_index, get_app_index
from backend.core.logger import get_logger

logger = get_logger(__name__)


@register_tool(
    name="open_app",
    description="Launch an application by name (e.g., Chrome, Spotify, VS Code, Notepad, File Explorer).",
    parameters={"app_name": {"type": "string", "description": "Name or alias of application to open"}},
    risk_level="low",
    category="applications",
)
def open_app(app_name: str) -> str:
    if not app_name or not app_name.strip():
        return "Please specify the name of the application to open."
    return executor_open_app(app_name.strip())


@register_tool(
    name="close_app",
    description="Safely close/terminate a running application by name (e.g., close Chrome, close Spotify).",
    parameters={"app_name": {"type": "string", "description": "Name of application to close"}},
    risk_level="medium",
    requires_confirmation=False,
    category="applications",
)
def close_app(app_name: str) -> str:
    if not HAS_PSUTIL:
        return "Process inspection requires psutil (available on Windows Agent)."

    clean_name = app_name.lower().strip()
    # Remove trigger words
    for w in ["close", "exit", "quit", "terminate", "kill", "the", "app"]:
        clean_name = clean_name.replace(w, "").strip()

    if not clean_name:
        return "Please specify which application to close."

    matched_processes = []
    for proc in psutil.process_iter(["pid", "name", "exe"]):
        try:
            p_name = (proc.info["name"] or "").lower()
            p_exe = (proc.info["exe"] or "").lower()
            if clean_name in p_name or (p_exe and clean_name in os.path.basename(p_exe)):
                matched_processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if not matched_processes:
        return f"No running application matched '{clean_name}'."

    closed_count = 0
    for p in matched_processes:
        try:
            p.terminate()
            closed_count += 1
        except Exception as e:
            logger.warning(f"Could not terminate PID {p.pid}: {e}")

    return f"Closed {closed_count} instance(s) matching '{clean_name}'."


@register_tool(
    name="list_running_apps",
    description="List active user-facing applications currently running on the system.",
    parameters={},
    risk_level="low",
    category="applications",
)
def list_running_apps() -> str:
    if not HAS_PSUTIL:
        return "Process inspection requires psutil (available on Windows Agent)."

    running = []
    for proc in psutil.process_iter(["name", "exe"]):
        try:
            name = proc.info["name"]
            exe = proc.info["exe"]
            if exe and not exe.startswith(r"C:\Windows\System32"):
                if name and name not in running:
                    running.append(name)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if not running:
        return "No non-system applications currently detected."
    return "Running applications:\n- " + "\n- ".join(sorted(running)[:15])


@register_tool(
    name="rebuild_app_index",
    description="Rescan the system and rebuild the index of installed applications.",
    parameters={},
    risk_level="low",
    category="applications",
)
def rebuild_app_index() -> str:
    apps = scan_and_rebuild_index()
    return f"Application index rebuilt successfully. Discovered {len(apps)} installed applications."
