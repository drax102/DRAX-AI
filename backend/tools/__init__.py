"""
backend/tools/__init__.py — Tool registry orchestrator.
Loads platform-independent cloud tools everywhere, and Windows desktop tools when running on Windows.
"""

import sys
from backend.agent.tool_registry import registry
import backend.tools.cloud_tools

# On Windows desktop, also register Windows-specific computer control tools
if sys.platform == "win32":
    try:
        import backend.tools.windows_tools
    except Exception as e:
        import logging
        logging.getLogger("drax").warning(f"Windows desktop tools not fully loaded: {e}")

__all__ = ["registry"]
