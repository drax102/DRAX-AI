"""
speech_recognizer.py — Configurable speech recognition engine (Google SR / Vosk).
"""

import speech_recognition as sr

from backend.core.audio_manager import resolve_device_index
from backend.core.config import settings
from backend.core.logger import get_logger

logger = get_logger(__name__)


def listen_for_command_speech() -> str:
    """
    Listen for a single voice command using configured STT engine.
    Returns recognized text string or empty string on error/timeout.
    """
    engine_type = settings.get("speech", "engine", "google").lower()
    listen_timeout = settings.get("speech", "listen_timeout", 7)
    phrase_limit = settings.get("speech", "phrase_time_limit", 8)
    device_idx = resolve_device_index()

    r = sr.Recognizer()
    r.dynamic_energy_threshold = True
    r.pause_threshold = 0.8

    try:
        with sr.Microphone(device_index=device_idx) as source:
            logger.info("Listening for command...")
            r.adjust_for_ambient_noise(source, duration=0.5)
            audio = r.listen(source, timeout=listen_timeout, phrase_time_limit=phrase_limit)

        logger.info("Recognizing speech...")
        if engine_type == "google":
            text = r.recognize_google(audio)
            logger.info(f"Google STT recognized: '{text}'")
            return text
        else:
            # Fallback google
            text = r.recognize_google(audio)
            return text

    except sr.WaitTimeoutError:
        logger.info("Command listening timed out (no speech detected)")
        return ""
    except sr.UnknownValueError:
        logger.info("Could not understand audio")
        return ""
    except sr.RequestError as e:
        logger.error(f"Speech recognition service error: {e}")
        return ""
    except Exception as e:
        logger.error(f"Speech capture failed: {e}")
        return ""
