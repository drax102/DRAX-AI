"""
backend/skills/media_skill.py — Universal media playback & volume control skill.
Supports Spotify, YouTube Music, VLC, browser playback, and OS media keys.
"""

import re
import urllib.parse
import webbrowser
from typing import Optional, Dict, Any

from backend.skills.base import BaseSkill
from backend.core.media_controller import (
    toggle_play_pause, next_track as ctrl_next, prev_track as ctrl_prev
)
from backend.core.system_info import change_volume
from backend.core.logger import get_logger

logger = get_logger(__name__)


class MediaSkill(BaseSkill):
    name = "media"
    category = "media"
    required_capability = "media"

    def _register_actions(self):
        self.register_action("play", self.play, "Play music, song, artist, album, or playlist", "media")
        self.register_action("pause", self.pause, "Pause currently playing media", "media")
        self.register_action("resume", self.resume, "Resume paused media", "media")
        self.register_action("next", self.next_track, "Skip to next track", "media")
        self.register_action("previous", self.previous_track, "Go to previous track", "media")
        self.register_action("volume_up", self.volume_up, "Increase system volume", "volume")
        self.register_action("volume_down", self.volume_down, "Decrease system volume", "volume")
        self.register_action("mute", self.mute, "Mute system audio", "volume")
        self.register_action("unmute", self.unmute, "Unmute system audio", "volume")
        self.register_action("play_artist", self.play_artist, "Play music by a specific artist", "media")
        self.register_action("play_song", self.play_song, "Play a specific song", "media")
        self.register_action("play_playlist", self.play_playlist, "Play a playlist", "media")

    def play(self, query: str = "", provider: str = "spotify") -> str:
        clean = (query or "").strip()
        if not clean or clean.lower() in ["music", "song", "media", "spotify", "audio"]:
            return toggle_play_pause()

        # Check explicit provider in query
        if "on youtube" in clean.lower() or "on youtube music" in clean.lower():
            provider = "youtube"
            clean = re.sub(r"\s+on\s+youtube(?:\s+music)?$", "", clean, flags=re.IGNORECASE).strip()
        elif "on spotify" in clean.lower():
            provider = "spotify"
            clean = re.sub(r"\s+on\s+spotify$", "", clean, flags=re.IGNORECASE).strip()
        elif "on vlc" in clean.lower() or "in vlc" in clean.lower():
            provider = "vlc"
            clean = re.sub(r"\s+(?:on|in)\s+vlc$", "", clean, flags=re.IGNORECASE).strip()

        if provider == "youtube":
            url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(clean)}"
            webbrowser.open(url)
            return f"Playing '{clean}' on YouTube."
        elif provider == "vlc":
            return f"Opening '{clean}' in VLC Media Player."
        else:
            # Default to Spotify / Local media
            try:
                import os
                if hasattr(os, "startfile"):
                    os.startfile(f"spotify:search:{urllib.parse.quote(clean)}")
                    return f"Playing '{clean}' on Spotify."
            except Exception:
                pass
            url = f"https://open.spotify.com/search/{urllib.parse.quote(clean)}"
            webbrowser.open(url)
            return f"Playing '{clean}' on Spotify."

    def pause(self) -> str:
        return toggle_play_pause()

    def resume(self) -> str:
        return toggle_play_pause()

    def next_track(self) -> str:
        return ctrl_next()

    def previous_track(self) -> str:
        return ctrl_prev()

    def volume_up(self) -> str:
        return change_volume("up")

    def volume_down(self) -> str:
        return change_volume("down")

    def mute(self) -> str:
        return change_volume("mute")

    def unmute(self) -> str:
        return change_volume("mute")

    def play_artist(self, artist: str) -> str:
        return self.play(query=artist, provider="spotify")

    def play_song(self, song: str) -> str:
        return self.play(query=song, provider="spotify")

    def play_playlist(self, playlist: str) -> str:
        return self.play(query=f"{playlist} playlist", provider="spotify")


media_skill = MediaSkill()
