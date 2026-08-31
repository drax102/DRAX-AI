"""
media_controller.py — Windows global hardware-level media key controller.
Uses native user32.dll keybd_event to send instant hardware media keys for Spotify, YouTube, VLC, Chrome, etc.
"""

import ctypes
from backend.core.logger import get_logger

logger = get_logger(__name__)

# Windows Virtual-Key Codes for Media and Volume
VK_VOLUME_MUTE = 0xAD        # 173
VK_VOLUME_DOWN = 0xAE        # 174
VK_VOLUME_UP = 0xAF          # 175
VK_MEDIA_NEXT_TRACK = 0xB0   # 176
VK_MEDIA_PREV_TRACK = 0xB1   # 177
VK_MEDIA_STOP = 0xB2         # 178
VK_MEDIA_PLAY_PAUSE = 0xB3   # 179

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002


def send_media_key(vk_code: int):
    """Directly post hardware virtual key event to Windows OS."""
    if not hasattr(ctypes, "windll"):
        logger.info(f"Hardware media key 0x{vk_code:02X} posted (simulation on non-Windows host).")
        return
    try:
        user32 = ctypes.windll.user32
        # Key down
        user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY, 0)
        # Key up
        user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
        logger.info(f"Posted media key 0x{vk_code:02X} to Windows")
    except Exception as e:
        logger.error(f"Failed to send media key {vk_code}: {e}")


def toggle_play_pause() -> str:
    send_media_key(VK_MEDIA_PLAY_PAUSE)
    return "Toggled playback (Play / Pause)."


def next_track() -> str:
    send_media_key(VK_MEDIA_NEXT_TRACK)
    return "Skipped to next track."


def prev_track() -> str:
    send_media_key(VK_MEDIA_PREV_TRACK)
    return "Returned to previous track."


def handle_media_command(command: str) -> str:
    """Handle natural media commands."""
    cmd = command.lower().strip()

    if any(k in cmd for k in ["pause", "resume", "toggle", "stop"]):
        return toggle_play_pause()

    if any(k in cmd for k in ["next", "skip"]):
        return next_track()

    if any(k in cmd for k in ["previous", "back", "prev", "last track", "last song"]):
        return prev_track()

    return toggle_play_pause()
