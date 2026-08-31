"""
config.py — Central configuration loader for DRAX AI.
All modules should import settings from here.
"""

import json
import os
import sys

# Resolve project root regardless of how the app is launched (including PyInstaller)
if hasattr(sys, "_MEIPASS"):
    _PROJECT_ROOT = sys._MEIPASS
else:
    _PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_CONFIG_PATH = os.path.join(_PROJECT_ROOT, "config", "settings.json")

_DEFAULT_SETTINGS = {
    "assistant": {
        "name": "Drax",
        "wake_word": "hey drax",
        "wake_word_aliases": ["hey drax", "drax"],
        "wake_confidence_threshold": 0.72,
        "wake_min_token_match": 1,
        "cooldown_seconds": 2.0,
        "confirm_dangerous_commands": True,
    },
    "speech": {
        "engine": "google",
        "vosk_model": "vosk-model-small-en-us-0.15",
        "sample_rate": 16000,
        "microphone": "auto",
        "listen_timeout": 7,
        "phrase_time_limit": 8,
    },
    "tts": {"enabled": True, "rate": 185, "volume": 1.0},
    "ui": {
        "theme": "dark",
        "accent": "cyan",
        "hide_to_tray_on_start": True,
        "show_notifications": True,
    },
    "startup": {"start_with_windows": False, "rebuild_index_on_start": False},
    "app_indexer": {
        "scan_start_menu": True,
        "scan_registry": True,
        "scan_uwp": True,
        "cache_file": "backend/data/app_index.json",
        "manual_overrides": "backend/data/manual_apps.json",
    },
    "logging": {"level": "INFO", "log_file": "logs/drax.log", "console": True},
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base, returning merged dict."""
    result = dict(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


class _Settings:
    """Lazy-loaded, merged settings object with dot-access sections."""

    def __init__(self):
        self._data = dict(_DEFAULT_SETTINGS)
        self._loaded = False

    def _load(self):
        if self._loaded:
            return
        self._loaded = True
        if os.path.isfile(_CONFIG_PATH):
            try:
                with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                    user_cfg = json.load(f)
                self._data = _deep_merge(self._data, user_cfg)
            except Exception as e:
                print(f"[DRAX Config] Failed to load settings.json: {e} — using defaults.")

    def get(self, section: str, key: str = None, default=None):
        self._load()
        section_data = self._data.get(section, {})
        if key is None:
            return section_data
        return section_data.get(key, default)

    def __getattr__(self, section: str):
        self._load()
        if section.startswith("_"):
            raise AttributeError(section)
        return self._data.get(section, {})

    def resolve_path(self, relative_path: str) -> str:
        """Resolve a path relative to the project root."""
        return os.path.normpath(os.path.join(_PROJECT_ROOT, relative_path))

    @property
    def project_root(self) -> str:
        return _PROJECT_ROOT


settings = _Settings()
