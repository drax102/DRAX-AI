"""
intent_router.py — Core Siri/JARVIS-style command router for DRAX AI.
Refactored for safety, offline fallback, and structured dispatch.
"""

import ast
import datetime
import os
import re
import urllib.parse
import webbrowser

import requests
try:
    import wikipedia
    HAS_WIKIPEDIA = True
except ImportError:
    HAS_WIKIPEDIA = False

from backend.core.app_executor import open_app
from backend.core.config import settings
from backend.core.logger import get_logger
from backend.core.media_controller import handle_media_command
from backend.core.system_controller import handle_system_command
from backend.plugins.open_website import clean_spoken_url, open_website

logger = get_logger(__name__)

SEARCH_PROVIDERS = {
    "google": "https://www.google.com/search?q=",
    "youtube": "https://www.youtube.com/results?search_query=",
    "github": "https://github.com/search?q=",
    "wikipedia": "https://en.wikipedia.org/wiki/Special:Search?search=",
    "amazon": "https://www.amazon.in/s?k=",
    "spotify": "https://open.spotify.com/search/",
}


def _safe_eval_math(expr: str) -> str:
    """Safely evaluate mathematical expressions using AST parsing."""
    try:
        clean = expr.lower()
        clean = clean.replace("plus", "+").replace("minus", "-")
        clean = clean.replace("times", "*").replace("multiplied by", "*").replace("x", "*")
        clean = clean.replace("divided by", "/").replace("over", "/")
        clean = clean.replace("power", "**").replace("^", "**")
        clean = re.sub(r"[^0-9\+\-\*\/\(\)\.\s]", "", clean).strip()

        if not clean:
            return "Could not extract mathematical expression."

        # Parse AST node
        node = ast.parse(clean, mode="eval")

        def _eval_node(n):
            if isinstance(n, ast.Expression):
                return _eval_node(n.body)
            elif isinstance(n, ast.BinOp):
                left = _eval_node(n.left)
                right = _eval_node(n.right)
                if isinstance(n.op, ast.Add): return left + right
                if isinstance(n.op, ast.Sub): return left - right
                if isinstance(n.op, ast.Mult): return left * right
                if isinstance(n.op, ast.Div): return left / right if right != 0 else "undefined"
                if isinstance(n.op, ast.Pow): return left ** right
            elif isinstance(n, ast.UnaryOp):
                operand = _eval_node(n.operand)
                if isinstance(n.op, ast.UAdd): return +operand
                if isinstance(n.op, ast.USub): return -operand
            elif isinstance(n, ast.Constant):
                return n.value
            raise ValueError(f"Unsupported AST node: {type(n)}")

        val = _eval_node(node)
        return f"The result is {val}."
    except Exception as e:
        logger.warning(f"Math evaluation failed for '{expr}': {e}")
        return "Sorry, I couldn't compute that math expression."


def _get_wikipedia_summary(query: str) -> str:
    """Fetch 2-sentence summary from Wikipedia."""
    if not HAS_WIKIPEDIA:
        return f"Searching Google for {query}."
    try:
        wikipedia.set_lang("en")
        summary = wikipedia.summary(query, sentences=2)
        return summary
    except Exception as e:
        logger.warning(f"Wikipedia search failed for '{query}': {e}")
        webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote(query)}")
        return f"Searching Google for {query}."


def _get_time_response() -> str:
    now = datetime.datetime.now()
    return f"The current time is {now.strftime('%I:%M %p')}."


def _get_date_response() -> str:
    now = datetime.datetime.now()
    return f"Today is {now.strftime('%A, %B %d, %Y')}."


def route_command(raw_command: str) -> str:
    """
    Main command routing engine.
    Maps raw command strings to actions and returns string responses.
    """
    if not raw_command or not raw_command.strip():
        return "I didn't hear anything."

    c = raw_command.lower().strip()
    logger.info(f"Routing command: '{c}'")

    # 1. Identity & Greetings
    if c in ["who are you", "what is your name", "identify yourself"]:
        return "I am Drax, your personal cybernetic AI assistant."

    if any(g in c for g in ["hello", "hey drax", "hi drax", "good morning", "good evening"]):
        return "Hello! How can I assist you today?"

    # 2. Time & Date
    if c in ["time", "what time is it", "tell me the time", "current time"]:
        return _get_time_response()

    if c in ["date", "what is the date", "today's date", "what day is it"]:
        return _get_date_response()

    # 3. System & Telemetry Controls
    if any(k in c for k in ["system status", "telemetry", "cpu", "ram", "volume", "mute", "shutdown", "restart", "lock screen"]):
        res = handle_system_command(c)
        if isinstance(res, tuple):
            return res[0]  # Confirmation prompt text
        return res

    # 4. Media Key Controls (pause, resume, skip, next track)
    if any(k in c for k in ["pause media", "resume media", "next track", "skip song", "previous track"]):
        return handle_media_command(c)

    # 5. Media Playback (Spotify / YouTube search)
    if c.startswith("play "):
        song = c[5:].strip()
        # Truncate run-on speech if present
        song = re.split(r"\s+(and |so that|i want|because)", song)[0].strip()
        if "on youtube" in song:
            song_clean = song.replace("on youtube", "").strip()
            url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(song_clean)}"
            webbrowser.open(url)
            return f"Playing {song_clean} on YouTube."
        else:
            song_clean = song.replace("on spotify", "").strip()
            # Try app launch first, fall back to web Spotify
            res = open_app("spotify")
            url = f"https://open.spotify.com/search/{urllib.parse.quote(song_clean)}"
            webbrowser.open(url)
            return f"Searching for {song_clean} on Spotify."

    # 6. Math evaluation
    if any(k in c for k in ["calculate", "compute", "what is", "math"]) and any(op in c for op in ["+", "-", "*", "/", "plus", "minus", "times", "divided"]):
        clean_expr = c
        for kw in ["calculate", "compute", "what is"]:
            clean_expr = clean_expr.replace(kw, "")
        return _safe_eval_math(clean_expr)

    # 7. Website Opening
    if c.startswith("open website ") or c.startswith("go to ") or c.endswith(".com") or c.endswith(".org") or c.endswith(".io") or c.endswith(".ai"):
        return open_website(c)

    # 8. App Opening
    if c.startswith("open ") or c.startswith("launch ") or c.startswith("start "):
        target_app = c
        for prefix in ["open ", "launch ", "start "]:
            if target_app.startswith(prefix):
                target_app = target_app[len(prefix):]
                break

        # Check if it's a known website first
        if "." in target_app or target_app in ["youtube", "google", "github", "reddit", "twitter", "x"]:
            return open_website(target_app)

        return open_app(target_app)

    # 9. In-App / Platform Search ("search for X on Y")
    if "search for" in c or "search " in c:
        m = re.search(r"search\s+(?:for\s+)?(.+?)\s+on\s+(\w+)", c)
        if m:
            query, platform = m.group(1).strip(), m.group(2).strip()
            if platform in SEARCH_PROVIDERS:
                url = SEARCH_PROVIDERS[platform] + urllib.parse.quote(query)
                webbrowser.open(url)
                return f"Searching for {query} on {platform.capitalize()}."

    # 10. Wikipedia / Knowledge Query
    if c.startswith("who is ") or c.startswith("what is ") or c.startswith("tell me about "):
        query = c
        for prefix in ["who is ", "what is ", "tell me about "]:
            if query.startswith(prefix):
                query = query[len(prefix):]
                break
        return _get_wikipedia_summary(query)

    # Fallback to general Google search or app matching
    app_res = open_app(c)
    return app_res