"""
assistant.py — State machine and central orchestrator for DRAX AI.
Pure Python implementation without any PyQt5 dependencies.
"""

from enum import Enum
import threading
from typing import Callable, List, Any

from backend.core.logger import get_logger

logger = get_logger(__name__)


class Signal:
    """
    Lightweight, thread-safe pure Python signal emitter compatible with PyQt pyqtSignal (.connect, .disconnect, .emit).
    Allows desktop UI, background services, cloud servers, and CLI to communicate without PyQt5 dependency.
    """

    def __init__(self):
        self._handlers: List[Callable] = []
        self._lock = threading.Lock()

    def connect(self, handler: Callable):
        with self._lock:
            if handler not in self._handlers:
                self._handlers.append(handler)

    def disconnect(self, handler: Callable):
        with self._lock:
            if handler in self._handlers:
                self._handlers.remove(handler)

    def emit(self, *args: Any, **kwargs: Any):
        with self._lock:
            handlers = list(self._handlers)
        for handler in handlers:
            try:
                handler(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in signal handler {handler}: {e}")


class AssistantState(Enum):
    IDLE = "IDLE"
    WAKE = "WAKE"
    LISTENING = "LISTENING"
    PROCESSING = "PROCESSING"
    EXECUTING = "EXECUTING"
    RESPONDING = "RESPONDING"
    ERROR = "ERROR"


class DraxAssistant:
    """
    Central Assistant singleton with thread-safe state transition and signals.
    """

    _instance = None
    _singleton_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = super(DraxAssistant, cls).__new__(cls)
            return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._state = AssistantState.IDLE
        self._state_lock = threading.Lock()
        self.state_changed = Signal()    # Emits AssistantState
        self.log_message = Signal()      # Emits (message, level)
        self.speech_detected = Signal()  # Emits recognized user text
        self.response_ready = Signal()   # Emits assistant text response

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
