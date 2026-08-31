"""
screen_tools.py — Screen capture and awareness tools.
"""

import os
from datetime import datetime
from PIL import ImageGrab
from backend.agent.tool_registry import register_tool
from backend.core.config import settings
from backend.core.logger import get_logger

logger = get_logger(__name__)


@register_tool(
    name="take_screenshot",
    description="Capture a screenshot of the current screen and save to logs/screenshot.png.",
    parameters={},
    risk_level="low",
    category="screen",
)
def take_screenshot() -> str:
    try:
        shot = ImageGrab.grab()
        save_dir = settings.resolve_path("logs/screenshots")
        os.makedirs(save_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(save_dir, f"screen_{timestamp}.png")
        shot.save(filepath)
        return f"Screenshot captured and saved to {filepath}."
    except Exception as e:
        logger.error(f"Failed to capture screenshot: {e}")
        return f"Could not capture screenshot: {e}"


@register_tool(
    name="screen_read",
    description="Analyze active window and report screen context.",
    parameters={},
    risk_level="low",
    category="screen",
)
def screen_read() -> str:
    try:
        shot = ImageGrab.grab()
        width, height = shot.size
        return f"Screen resolution is {width}x{height}. Screen awareness provider is active."
    except Exception as e:
        return f"Screen reading unavailable: {e}"
