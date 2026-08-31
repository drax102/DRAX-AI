"""
media_tools.py — Windows media playback and Spotify integration tools.
"""

import re
import urllib.parse
import webbrowser

from backend.agent.tool_registry import register_tool
from backend.core.app_executor import open_app
from backend.core.media_controller import toggle_play_pause, next_track as ctrl_next_track, prev_track as ctrl_prev_track
from backend.core.system_info import change_volume
from backend.core.logger import get_logger

logger = get_logger(__name__)


@register_tool(
    name="play_media",
    description="Play a song, artist, playlist, or video on Spotify or YouTube.",
    parameters={
        "query": {"type": "string", "description": "Song name, artist, or playlist"},
        "platform": {"type": "string", "description": "'spotify' or 'youtube'", "default": "spotify"},
    },
    risk_level="low",
    category="media",
)
def play_media(query: str = "", platform: str = "spotify") -> str:
    clean_q = (query or "").strip()
    for prefix in ["play ", "listen to ", "song ", "music "]:
        if clean_q.lower().startswith(prefix):
            clean_q = clean_q[len(prefix):].strip()

    # If query is empty or just generic "music", toggle playback
    if not clean_q or clean_q.lower() in ["music", "song", "media", "audio", "spotify"]:
        return toggle_play_pause()

    # Clean trailing "on spotify", "on youtube"
    if "on youtube" in clean_q.lower():
        platform = "youtube"
        clean_q = re.sub(r"\s+on\s+youtube$", "", clean_q, flags=re.IGNORECASE).strip()
    elif "on spotify" in clean_q.lower():
        platform = "spotify"
        clean_q = re.sub(r"\s+on\s+spotify$", "", clean_q, flags=re.IGNORECASE).strip()

    # Remove run-on speech if user continued talking
    clean_q = re.split(r"\s+(and |so that|i want|because)", clean_q)[0].strip()

    if platform.lower() == "youtube":
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(clean_q)}"
        webbrowser.open(url)
        return f"Playing {clean_q} on YouTube."
    else:
        # Launch Spotify desktop app and search URI
        spotify_launched = False
        try:
            import os
            if hasattr(os, "startfile"):
                os.startfile(f"spotify:search:{urllib.parse.quote(clean_q)}")
                spotify_launched = True
        except Exception:
            pass

        if not spotify_launched:
            open_app("spotify")
            web_url = f"https://open.spotify.com/search/{urllib.parse.quote(clean_q)}"
            webbrowser.open(web_url)

        return f"Playing '{clean_q}' on Spotify."


@register_tool(
    name="pause_media",
    description="Pause or resume the currently playing media in Spotify, YouTube, Chrome, or Windows Media Player.",
    parameters={},
    risk_level="low",
    category="media",
)
def pause_media() -> str:
    return toggle_play_pause()


@register_tool(
    name="next_track",
    description="Skip to the next song/track.",
    parameters={},
    risk_level="low",
    category="media",
)
def next_track() -> str:
    return ctrl_next_track()


@register_tool(
    name="previous_track",
    description="Go back to the previous song/track.",
    parameters={},
    risk_level="low",
    category="media",
)
def previous_track() -> str:
    return ctrl_prev_track()


@register_tool(
    name="volume_control",
    description="Adjust system audio volume up, down, or mute.",
    parameters={"action": {"type": "string", "description": "'up', 'down', 'mute', or 'max'"}},
    risk_level="low",
    category="media",
)
def volume_control(action: str = "up") -> str:
    return change_volume(action)
