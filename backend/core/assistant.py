"""
assistant.py — State machine and central orchestrator for DRAX AI.
"""

from enum import Enum
import threading
from PyQt5.QtCore import QObject, pyqtSignal

from backend.core.logger import get_logger

logger = get_logger(__name__)


class AssistantState(Enum):
    IDLE = "IDLE"
    WAKE = "WAKE"
    LISTENING = "LISTENING"
    PROCESSING = "PROCESSING"
    EXECUTING = "EXECUTING"
    RESPONDING = "RESPONDING"
    ERROR = "ERROR"


class DraxAssistant(QObject):
    """
    Central Assistant singleton with thread-safe state transition and signals.
    """
    state_changed = pyqtSignal(object)  # AssistantState
    log_message = pyqtSignal(str, str)  # (message, level)
    speech_detected = pyqtSignal(str)   # recognized user text
    response_ready = pyqtSignal(str)    # assistant text response

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DraxAssistant, cls).__new__(cls)
            return cls._instance

    def __init__(self):
        super().__init__()
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._state = AssistantState.IDLE
        self._state_lock = threading.Lock()

    @property
    def state(self) -> AssistantState:
        with self._state_lock:
            return self._state

    def set_state(self, new_state: AssistantState):
        with self._state_lock:
            if self._state == new_state:
                return
            old_state = self._state
            self._state = new_state
            logger.info(f"State transition: {old_state.value} -> {new_state.value}")

        self.state_changed.emit(new_state)

    def notify_user_input(self, text: str):
        """Called when user voice or typed input is received."""
        self.speech_detected.emit(text)

    def notify_response(self, text: str):
        """Called when assistant generates a response."""
        self.response_ready.emit(text)


assistant = DraxAssistant()
