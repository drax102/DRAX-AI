"""
context.py — Short-term conversational context manager for multi-turn dialogue and follow-up commands.
Handles pronoun references, follow-up queries ('What about Nvidia?', 'Make it louder', 'Close it').
"""

import time
from typing import Optional, Dict, Any

from backend.core.logger import get_logger

logger = get_logger(__name__)


class ConversationContext:
    """Maintains short-term conversational state across user turns."""

    def __init__(self, timeout_seconds: float = 120.0):
        self.timeout_seconds = timeout_seconds
        self.last_turn_time = 0.0
        self.active_domain: Optional[str] = None  # "finance", "media", "app", "browser", "task"
        self.last_entity: Optional[str] = None    # "Nvidia", "Spotify", "resume.pdf"
        self.last_intent: Optional[str] = None    # "get_stock_price", "play_media"
        self.last_result: Optional[str] = None
        self.pending_confirmation: Optional[Dict[str, Any]] = None  # {tool_name, kwargs}

    def update_turn(self, intent: str, domain: str, entity: Optional[str] = None, result: Optional[str] = None):
        self.last_turn_time = time.time()
        self.last_intent = intent
        self.active_domain = domain
        if entity:
            self.last_entity = entity
        if result:
            self.last_result = result

    def is_context_active(self) -> bool:
        return (time.time() - self.last_turn_time) <= self.timeout_seconds

    def resolve_follow_up(self, user_text: str) -> Optional[tuple[str, dict]]:
        """
        Check if user_text is a follow-up to the previous context.
        Returns (tool_name, kwargs) or None.
        """
        if not self.is_context_active():
            return None

        text = user_text.lower().strip()

        # Follow-up stock lookup: "What about Nvidia?", "How about Tesla?", "And Apple?"
        if self.active_domain == "finance":
            if any(text.startswith(prefix) for prefix in ["what about ", "how about ", "and ", "check "]):
                clean_target = text
                for p in ["what about ", "how about ", "and ", "check ", "what is "]:
                    if clean_target.startswith(p):
                        clean_target = clean_target[len(p):].strip()
                clean_target = clean_target.replace("?", "").strip()
                if clean_target:
                    return ("get_stock_price", {"symbol": clean_target})

        # Follow-up volume / media: "Make it louder", "Quieter", "Next", "Pause"
        if self.active_domain == "media":
            if any(w in text for w in ["louder", "increase volume", "turn it up"]):
                return ("volume_control", {"action": "up"})
            if any(w in text for w in ["quieter", "lower volume", "turn it down"]):
                return ("volume_control", {"action": "down"})
            if text in ["pause", "stop", "resume", "play"]:
                return ("pause_media", {})
            if text in ["next", "skip", "next song"]:
                return ("next_track", {})

        return None

    def clear(self):
        self.active_domain = None
        self.last_entity = None
        self.last_intent = None
        self.last_result = None
        self.pending_confirmation = None


context = ConversationContext()
