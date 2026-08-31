"""
command_processor.py — Unified text & voice command processor connecting to the Agent Core.
Pure Python background worker thread without PyQt5 dependencies.
"""

import threading

from backend.agent.agent import process_user_request
from backend.core.assistant import AssistantState, assistant, Signal
from backend.core.logger import get_logger

logger = get_logger(__name__)


class CommandProcessorWorker(threading.Thread):
    """Worker thread to execute agent processing off the main thread."""

    def __init__(self, command_text: str):
        super().__init__(daemon=True)
        self.command_text = command_text
        self.command_completed = Signal()  # (command, response)

    def run(self):
        logger.info(f"Processing command via Agent: '{self.command_text}'")
        try:
            response = process_user_request(self.command_text)
            self.command_completed.emit(self.command_text, response)
        except Exception as e:
            logger.error(f"Error processing command '{self.command_text}': {e}")
            err_msg = "An error occurred while processing your request."
            assistant.set_state(AssistantState.ERROR)
            assistant.notify_response(err_msg)
            self.command_completed.emit(self.command_text, err_msg)


def process_command_async(command_text: str) -> CommandProcessorWorker:
    """Launch async agent command processing and return worker thread."""
    worker = CommandProcessorWorker(command_text)
    worker.start()
    return worker
