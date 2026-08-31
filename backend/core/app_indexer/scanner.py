"""
scanner.py — Main orchestrator for app indexing and caching.
Discovers applications from Start Menu, Windows Registry, UWP Store Apps, Program Files, and local drives.
"""

import json
import os
import threading
import time

from backend.core.config import settings
from backend.core.logger import get_logger
from backend.core.app_indexer.builtins import BUILTIN_APPS
from backend.core.app_indexer.start_menu import scan_start_menu
from backend.core.app_indexer.registry import scan_registry_app_paths
from backend.core.app_indexer.uwp import scan_uwp_apps
from backend.core.app_indexer.program_files import scan_program_directories

logger = get_logger(__name__)

_index_cache: list[dict] | None = None
_cache_lock = threading.Lock()


def load_manual_overrides() -> list[dict]:
    """Load manual overrides from settings manual_overrides path."""
    rel_path = settings.get("app_indexer", "manual_overrides", "backend/data/manual_apps.json")
    path = settings.resolve_path(rel_path)
    overrides = []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                for name, target in data.items():
                    overrides.append({
                        "name": name.lower(),
                        "display_name": name.capitalize(),
                        "aliases": [name.lower()],
                        "type": "uwp" if str(target).startswith("shell:") else "executable",
                        "target": target,
                        "source": "manual",
                    })
            elif isinstance(data, list):
                overrides = data
        except Exception as e:
            logger.error(f"Failed to load manual overrides: {e}")
    return overrides


def scan_and_rebuild_index() -> list[dict]:
    """Perform a full multi-threaded scan across all sources and save structured app index."""
    logger.info("Starting comprehensive PC-wide app indexer scan...")
    start_time = time.time()
    collected: list[dict] = []
    threads = []
    lock = threading.Lock()

    def _run_step(fn):
        try:
            res = fn()
            with lock:
                collected.extend(res)
        except Exception as err:
            logger.error(f"Scanner sub-step failed: {err}")

    # 1. Built-in Windows Apps
    collected.extend(BUILTIN_APPS)

    # 2. Parallel Deep Scans
    if settings.get("app_indexer", "scan_start_menu", True):
        threads.append(threading.Thread(target=_run_step, args=(scan_start_menu,)))
    if settings.get("app_indexer", "scan_registry", True):
        threads.append(threading.Thread(target=_run_step, args=(scan_registry_app_paths,)))
    if settings.get("app_indexer", "scan_uwp", True):
        threads.append(threading.Thread(target=_run_step, args=(scan_uwp_apps,)))

    # Program Files & Drive executables scanner
    threads.append(threading.Thread(target=_run_step, args=(scan_program_directories,)))

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # 3. Manual Overrides (Highest Priority)
    overrides = load_manual_overrides()

    # Deduplicate entries by name & target
    app_map: dict[str, dict] = {}
    for app in collected:
        name = app["name"]
        if name not in app_map or app["source"] in ["builtin", "uwp"]:
            app_map[name] = app

    for app in overrides:
        app_map[app["name"]] = app

    final_index = list(app_map.values())
    elapsed = time.time() - start_time
    logger.info(f"Complete system scan indexed {len(final_index)} applications in {elapsed:.2f}s")

    # Save to JSON cache
    rel_path = settings.get("app_indexer", "cache_file", "backend/data/app_index.json")
    cache_path = settings.resolve_path(rel_path)
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(final_index, f, indent=2)
        logger.info(f"Saved complete application index to {cache_path}")
    except Exception as e:
        logger.error(f"Failed to write app index cache: {e}")

    global _index_cache
    with _cache_lock:
        _index_cache = final_index

    return final_index


def get_app_index(force_rebuild: bool = False) -> list[dict]:
    """Retrieve app index from cache or disk, building if necessary."""
    global _index_cache
    with _cache_lock:
        if _index_cache is not None and not force_rebuild:
            return _index_cache

    rel_path = settings.get("app_indexer", "cache_file", "backend/data/app_index.json")
    cache_path = settings.resolve_path(rel_path)

    if not force_rebuild and os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list) and len(data) > 0:
                with _cache_lock:
                    _index_cache = data
                return data
        except Exception as e:
            logger.warning(f"Could not load app index cache ({e}) — rebuilding")

    return scan_and_rebuild_index()
