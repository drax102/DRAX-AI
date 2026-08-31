"""
tts_engine.py — Thread-safe TTS engine using pyttsx3.
"""

import pyttsx3
import queue
import threading
import time
from PyQt5.QtCore import QObject, pyqtSignal

from backend.core.config import settings
from backend.core.logger import get_logger

logger = get_logger(__name__)


class DraxVoiceEngine(QObject):
    """
    Thread-safe, non-blocking voice synthesis engine for DRAX AI.
    Runs speech synthesis in a dedicated background daemon thread to avoid GUI blocking.
    """
    speech_started = pyqtSignal(str)
    speech_finished = pyqtSignal()

    def __init__(self, rate=None, volume=None):
        super().__init__()
        self.queue = queue.Queue()
        self.rate = rate if rate is not None else settings.get("tts", "rate", 185)
        self.volume = volume if volume is not None else settings.get("tts", "volume", 1.0)
        self._is_speaking = False
        self._stop_event = threading.Event()
        
        # Start worker thread
        self.thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.thread.start()

    def speak(self, text: str):
        """Enqueue text for speech synthesis without blocking caller."""
        if not settings.get("tts", "enabled", True):
            return
        if not text or not text.strip():
            return
        self.queue.put(text.strip())

    def is_speaking(self) -> bool:
        return self._is_speaking or not self.queue.empty()

    def stop(self):
        """Clear queue and interrupt speech."""
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
            except queue.Empty:
                break

    def _worker_loop(self):
        # Initialize pyttsx3 inside worker thread context
        try:
            engine = pyttsx3.init()
            engine.setProperty('rate', self.rate)
            engine.setProperty('volume', self.volume)
            
            # Select male/female voice if available
            voices = engine.getProperty('voices')
            if voices:
                for voice in voices:
                    if "david" in voice.name.lower() or "zira" in voice.name.lower():
                        engine.setProperty('voice', voice.id)
                        break
        except Exception as e:
            logger.warning(f"Voice engine init warning: {e}")
            engine = None

        while not self._stop_event.is_set():
            try:
                text = self.queue.get(timeout=0.2)
            except queue.Empty:
                continue

            self._is_speaking = True
            self.speech_started.emit(text)

            if engine:
                try:
                    engine.say(text)
                    engine.runAndWait()
                except Exception as e:
                    logger.error(f"Speech error: {e}")
            else:
                # Fallback delay if pyttsx3 failed
                time.sleep(len(text) * 0.05)

            self._is_speaking = False
            self.speech_finished.emit()
            self.queue.task_done()


# Global engine instance
_voice_engine_instance = None
_engine_lock = threading.Lock()


def get_voice_engine() -> DraxVoiceEngine:
    global _voice_engine_instance
    with _engine_lock:
        if _voice_engine_instance is None:
            _voice_engine_instance = DraxVoiceEngine()
        return _voice_engine_instance


def speak(text: str):
    """Convenience function to speak text asynchronously."""
    engine = get_voice_engine()
    engine.speak(text)
