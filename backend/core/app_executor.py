"""
app_executor.py — Ranked matching and safe launching of Windows applications.
Implements strict 6-tier ranked matching:
  Tier 1: Exact Name Match (1.0)
  Tier 2: Exact Alias Match (0.98)
  Tier 3: Normalized Name Match (0.92)
  Tier 4: Token / Substring Matching (0.85)
  Tier 5: Fuzzy Ratio Matching (0.75 - 0.85)
  Tier 6: Phonetic Soundex Matching (0.65)
"""

import os
import re
import subprocess
import webbrowser
from difflib import SequenceMatcher

from backend.core.app_indexer import get_app_index
from backend.core.logger import get_logger

logger = get_logger(__name__)

STOP_WORDS = ["open", "launch", "start", "run", "the", "app", "application", "game"]

ACRONYMS = {
    "gta v": ["gta v", "grand theft auto v", "grand theft auto 5", "gta 5", "playgtav", "gta5"],
    "gta 5": ["gta 5", "grand theft auto v", "grand theft auto 5", "gta v", "playgtav", "gta5"],
    "gta iv": ["gta iv", "grand theft auto iv", "grand theft auto 4", "gta 4", "gtaiv"],
    "gta 4": ["gta 4", "grand theft auto iv", "grand theft auto 4", "gta iv", "gtaiv"],
    "gta sa": ["gta sa", "grand theft auto san andreas", "gta san andreas"],
    "gta": ["gta", "gta v", "grand theft auto", "grand theft auto v", "gta 5"],
    "vs code": ["visual studio code", "code"],
    "vscode": ["visual studio code", "code"],
    "cmd": ["command prompt"],
    "calc": ["calculator"],
    "ps": ["powershell", "windows powershell"],
    "taskmgr": ["task manager"],
    "tg": ["telegram"],
    "wp": ["whatsapp"],
}


def _soundex(word: str) -> str:
    """Compute a Soundex code for phonetic comparison."""
    word = re.sub(r"[^a-zA-Z]", "", word).upper()
    if not word:
        return "0000"
    keep_first = word[0]
    table = str.maketrans("AEHIOUYWBFPVCGJKQSXZDTLMNR", "00000000111122222222334556")
    coded = word.translate(table)
    result = keep_first
    for c in coded[1:]:
        if c != result[-1] and c != "0":
            result += c
    return (result + "000")[:4]


def _phonetic_match(a: str, b: str) -> bool:
    """Return True if tokens in a and b have substantial phonetic Soundex similarity."""
    tokens_a = [t for t in re.findall(r"\w+", a.lower()) if t not in STOP_WORDS and len(t) > 2]
    tokens_b = [t for t in re.findall(r"\w+", b.lower()) if t not in STOP_WORDS and len(t) > 2]
    if not tokens_a or not tokens_b:
        return False
    matched = sum(1 for ta in tokens_a if any(_soundex(ta) == _soundex(tb) for tb in tokens_b))
    return (matched / len(tokens_a)) >= 0.5


def normalize_command(text: str) -> str:
    """Normalize input command text by removing stop words using word boundaries."""
    text = text.lower().strip()
    for word in STOP_WORDS:
        pattern = r"\b" + re.escape(word) + r"\b"
        text = re.sub(pattern, "", text)
    return re.sub(r"\s+", " ", text).strip()


def find_app_match(query: str) -> tuple[dict | None, float]:
    """
    Search app index for query using 6-tier ranked matching.
    Returns tuple of (matched_app_dict, confidence_score 0.0-1.0).
    """
    index = get_app_index()
    clean_q = normalize_command(query)
    if not clean_q:
        return None, 0.0

    search_queries = [clean_q]
    if clean_q in ACRONYMS:
        search_queries = ACRONYMS[clean_q] + search_queries

    best_app = None
    best_score = 0.0

    for sq in search_queries:
        for app in index:
            name_raw = app.get("name", "").lower().strip()
            display_raw = app.get("display_name", "").lower().strip()
            aliases = [a.lower().strip() for a in app.get("aliases", [])]

            # ── Tier 1: Exact Name Match (1.0) ───────────────────────────
            if sq == name_raw or sq == display_raw:
                return app, 1.0

            # ── Tier 2: Exact Alias Match (0.98) ─────────────────────────
            if sq in aliases:
                if 0.98 > best_score:
                    best_score = 0.98
                    best_app = app
                    continue

            # ── Tier 3: Normalized Substring Match (0.92) ────────────────
            norm_name = re.sub(r"[^a-z0-9]", "", name_raw)
            norm_sq = re.sub(r"[^a-z0-9]", "", sq)
            if norm_sq and (norm_sq == norm_name or norm_sq in norm_name):
                score = 0.92
                if score > best_score:
                    best_score = score
                    best_app = app
                    continue

            # ── Tier 4: Token Matching (0.85) ───────────────────────────
            sq_tokens = set(re.findall(r"\w+", sq))
            app_tokens = set(re.findall(r"\w+", name_raw) + re.findall(r"\w+", display_raw))
            if sq_tokens and sq_tokens.issubset(app_tokens):
                score = 0.85
                if score > best_score:
                    best_score = score
                    best_app = app
                    continue

            # ── Tier 5: Fuzzy Matching (0.75 - 0.85) ─────────────────────
            ratio = SequenceMatcher(None, sq, name_raw).ratio()
            if ratio >= 0.75 and ratio > best_score:
                best_score = ratio
                best_app = app
                continue

            # ── Tier 6: Phonetic Matching (0.65) ─────────────────────────
            if _phonetic_match(sq, name_raw) or _phonetic_match(sq, display_raw):
                if 0.65 > best_score:
                    best_score = 0.65
                    best_app = app

    return best_app, best_score


def launch_target(target: str) -> bool:
    """Safely launch application target (executable path, shortcut, or shell URI)."""
    try:
        logger.info(f"Launching target: {target}")
        if target.startswith("shell:") or target.lower().endswith(".lnk"):
            os.startfile(target)
            return True
        elif os.path.exists(target) and target.lower().endswith(".exe"):
            cwd = os.path.dirname(target)
            subprocess.Popen([target], cwd=cwd, shell=True)
            return True
        else:
            try:
                os.startfile(target)
                return True
            except Exception:
                cwd = os.path.dirname(target) if os.path.exists(target) else None
                subprocess.Popen(f'"{target}"', cwd=cwd, shell=True)
                return True
    except Exception as e:
        logger.error(f"Failed to launch target '{target}': {e}")
        try:
            cwd = os.path.dirname(target) if os.path.exists(target) else None
            subprocess.Popen(f'"{target}"', cwd=cwd, shell=True)
            return True
        except Exception as e2:
            logger.error(f"Secondary launch fallback failed: {e2}")
            return False


def open_app(command: str) -> str:
    """
    Main entry point for app opening command.
    Enforces confidence threshold to prevent launching incorrect applications.
    """
    app, score = find_app_match(command)

    # High Confidence Match (>= 0.70) -> Launch
    if app and score >= 0.70:
        target = app.get("target", "")
        display = app.get("display_name", app.get("name", "App"))
        if launch_target(target):
            return f"Opening {display}."
        else:
            return f"Could not launch {display}."

    # Ambiguous / Low Confidence (0.50 <= score < 0.70) -> Ask User
    elif app and 0.50 <= score < 0.70:
        display = app.get("display_name", app.get("name", "App"))
        return f"Did you mean to open {display}? Please say 'Open {display}' to confirm."

    # Fallback to search query
    else:
        clean_q = normalize_command(command)
        if clean_q:
            logger.info(f"App not found for '{command}' — searching Google")
            url = f"https://www.google.com/search?q={clean_q}"
            webbrowser.open(url)
            return f"Searching Google for {clean_q}."
        return "I couldn't find that application."