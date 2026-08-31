"""
wake_word.py — Robust wake-word detection for DRAX AI.

Uses Vosk offline ASR + multi-strategy matching:
  1. Exact / substring match
  2. Token-based match (configurable min token count)
  3. Fuzzy similarity (SequenceMatcher)
  4. Phonetic similarity (Soundex)

False-positive protection:
  - Configurable confidence threshold
  - Cooldown / debounce
  - Minimum audio length guard
  - Auto-reconnection & error resilience for 24/7 always-on operation
"""

import json
import os
import queue
import re
import sys
import threading
import time
from difflib import SequenceMatcher

import sounddevice as sd
from vosk import KaldiRecognizer, Model

from backend.core.audio_manager import resolve_device_index
from backend.core.config import settings
from backend.core.logger import get_logger

logger = get_logger(__name__)


def _soundex(word: str) -> str:
    """Compute a simple Soundex code for phonetic comparison."""
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
    """Return True if any token pair between a and b has the same Soundex code."""
    tokens_a = a.lower().split()
    tokens_b = b.lower().split()
    for ta in tokens_a:
        for tb in tokens_b:
            if len(ta) > 2 and len(tb) > 2 and _soundex(ta) == _soundex(tb):
                return True
    return False


_vosk_model: Model | None = None
_model_lock = threading.Lock()


def _get_model() -> Model | None:
    global _vosk_model
    with _model_lock:
        if _vosk_model is not None:
            return _vosk_model

        vosk_model_name = settings.get("speech", "vosk_model", "vosk-model-small-en-us-0.15")
        if hasattr(sys, "_MEIPASS"):
            model_path = os.path.join(sys._MEIPASS, "models", vosk_model_name)
        else:
            root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            model_path = os.path.join(root, "models", vosk_model_name)

        if not os.path.isdir(model_path):
            logger.error(f"Vosk model not found at: {model_path}")
            return None

        logger.info(f"Loading Vosk model: {model_path}")
        _vosk_model = Model(model_path)
        return _vosk_model


def _score_against_wake_words(text: str) -> float:
    """
    Score `text` against all configured wake words.
    Returns the highest confidence score (0.0 – 1.0).
    """
    wake_word = settings.get("assistant", "wake_word", "hey drax").lower()
    aliases = [w.lower() for w in settings.get("assistant", "wake_word_aliases", [wake_word])]
    all_targets = list(set([wake_word] + aliases))
    text = text.lower().strip()

    best = 0.0
    for target in all_targets:
        if text == target or target in text:
            return 1.0

        target_tokens = target.split()
        text_tokens = text.split()
        matched = sum(1 for tt in target_tokens if any(
            SequenceMatcher(None, tt, wt).ratio() > 0.75 for wt in text_tokens
        ))
        min_required = settings.get("assistant", "wake_min_token_match", 1)
        if matched >= min_required and len(target_tokens) > 0:
            token_score = matched / len(target_tokens)
            best = max(best, token_score * 0.90)

        ratio = SequenceMatcher(None, target, text).ratio()
        best = max(best, ratio)

        if _phonetic_match(target, text):
            best = max(best, best + 0.15)

    return min(best, 1.0)


def _is_false_positive(text: str) -> bool:
    reject_patterns = [
        r"^(hello|hi|hey|ok|okay|yes|no|sure|thanks|thank you)$",
        r"^hey (google|alexa|siri|cortana|bixby)$",
        r"^(what|how|why|when|where|who)\b",
    ]
    t = text.lower().strip()
    for pattern in reject_patterns:
        if re.match(pattern, t):
            return True
    return False


def listen_for_wake_word(on_wake_detected_cb, stop_event: threading.Event | None = None):
    """
    Continuously listen for the wake word on the configured microphone with auto-reconnect resilience.
    Calls `on_wake_detected_cb()` when the wake phrase is detected.
    """
    model = _get_model()
    if not model:
        logger.warning("Wake word listener disabled — Vosk model unavailable.")
        return

    sample_rate = settings.get("speech", "sample_rate", 16000)
    threshold = settings.get("assistant", "wake_confidence_threshold", 0.60)
    cooldown = settings.get("assistant", "cooldown_seconds", 1.5)

    logger.info("🟢 DRAX Wake Word Listener Active — Listening for 'Hey Drax'...")

    last_trigger = 0.0

    while stop_event is None or not stop_event.is_set():
        device_idx = resolve_device_index()
        recognizer = KaldiRecognizer(model, sample_rate)
        recognizer.SetWords(False)
        audio_q: queue.Queue = queue.Queue()

        def _audio_callback(indata, frames, time_info, status):
            audio_q.put(bytes(indata))

        try:
            with sd.RawInputStream(
                samplerate=sample_rate,
                blocksize=8000,
                dtype="int16",
                channels=1,
                device=device_idx,
                callback=_audio_callback,
            ):
                while stop_event is None or not stop_event.is_set():
                    try:
                        data = audio_q.get(timeout=0.5)
                    except queue.Empty:
                        continue

                    if len(data) < 4000:
                        continue

                    if recognizer.AcceptWaveform(data):
                        result = json.loads(recognizer.Result())
                        text = result.get("text", "").strip()
                        if not text:
                            continue

                        score = _score_against_wake_words(text)
                        logger.info(f"🗣️ Audio heard: '{text}' (wake confidence: {score:.2f})")

                        if _is_false_positive(text):
                            continue

                        if score >= threshold:
                            now = time.time()
                            if now - last_trigger < cooldown:
                                continue
                            last_trigger = now
                            logger.info(f"🟣 Wake Word Triggered: '{text}'")
                            if on_wake_detected_cb:
                                on_wake_detected_cb()

        except Exception as e:
            if stop_event and stop_event.is_set():
                break
            logger.warning(f"Wake word audio stream encountered error: {e}. Reconnecting in 2s...")
            time.sleep(2.0)
