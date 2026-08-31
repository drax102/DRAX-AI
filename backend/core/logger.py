"""
logger.py — Centralized logging setup for DRAX AI.
Import and use:  logger = get_logger(__name__)
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

_initialized = False


def setup_logging():
    """Initialize logging once for the entire application."""
    global _initialized
    if _initialized:
        return
    _initialized = True

    # Resolve log directory relative to project root
    if hasattr(sys, "_MEIPASS"):
        root = sys._MEIPASS
    else:
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Try to import settings; fall back to defaults if not ready yet
    try:
        from backend.core.config import settings
        log_file = settings.resolve_path(settings.get("logging", "log_file", "logs/drax.log"))
        level_str = settings.get("logging", "level", "INFO")
        console_enabled = settings.get("logging", "console", True)
    except Exception:
        log_file = os.path.join(root, "logs", "drax.log")
        level_str = "INFO"
        console_enabled = True

    level = getattr(logging, level_str.upper(), logging.INFO)

    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    fmt = logging.Formatter(
        "[%(asctime)s] [%(levelname)-8s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root_logger = logging.getLogger("drax")
    root_logger.setLevel(level)
    root_logger.handlers.clear()

    # Rotating file handler — 5 MB per file, 3 backups
    fh = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
    fh.setFormatter(fmt)
    fh.setLevel(level)
    root_logger.addHandler(fh)

    if console_enabled:
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(fmt)
        ch.setLevel(level)
        root_logger.addHandler(ch)

    root_logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """Get a named child logger under the 'drax' root logger."""
    setup_logging()
    # Strip module path prefix for cleaner names
    short = name.replace("backend.", "").replace("ui.", "")
    return logging.getLogger(f"drax.{short}")
