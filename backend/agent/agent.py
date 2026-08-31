"""
agent.py — Central Drax Agent Orchestrator.
Coordinates the entire Voice/Text -> Normalize -> Context -> Intent -> Entities -> Plan -> Tools -> Result -> Response pipeline.
"""

from typing import Tuple
from backend.agent.context import context
from backend.agent.executor import execute_plan, confirm_pending_action
from backend.agent.memory import list_memories, clear_memory
from backend.agent.planner import plan_request
from backend.database.db import log_conversation
from backend.core.assistant import AssistantState, assistant
from backend.core.logger import get_logger
from backend.core.tts_engine import speak

# Ensure all tools are registered
import backend.tools

logger = get_logger(__name__)


class DraxAgent:
    """The central agentic brain of Drax AI."""

    def process(self, raw_input: str) -> str:
        text = raw_input.strip()
        if not text:
            return "I didn't catch that."

        logger.info(f"Agent received input: '{text}'")
        assistant.set_state(AssistantState.PROCESSING)

        # Log user input
        log_conversation(role="user", content=text)

        # 1. Handle confirmation replies
        lower_t = text.lower()
        if context.pending_confirmation:
            if lower_t in ["yes", "confirm", "proceed", "do it", "sure", "ok", "yeah"]:
                res = confirm_pending_action(confirm=True)
                assistant.set_state(AssistantState.RESPONDING)
                speak(res)
                log_conversation(role="assistant", content=res)
                assistant.set_state(AssistantState.IDLE)
                return res
            elif lower_t in ["no", "cancel", "stop", "abort", "don't"]:
                res = confirm_pending_action(confirm=False)
                assistant.set_state(AssistantState.RESPONDING)
                speak(res)
                log_conversation(role="assistant", content=res)
                assistant.set_state(AssistantState.IDLE)
                return res

        # 2. Handle memory queries
        if any(lower_t.startswith(w) for w in ["what do you remember", "what do you know about me", "my preferences"]):
            res = list_memories()
            assistant.set_state(AssistantState.RESPONDING)
            speak(res)
            log_conversation(role="assistant", content=res)
            assistant.set_state(AssistantState.IDLE)
            return res

        if lower_t in ["clear memory", "forget everything", "clear my memory"]:
            res = clear_memory()
            assistant.set_state(AssistantState.RESPONDING)
            speak(res)
            log_conversation(role="assistant", content=res)
            assistant.set_state(AssistantState.IDLE)
            return res

        # 3. Generate plan
        assistant.set_state(AssistantState.PROCESSING)
        plan = plan_request(text)

        # 4. Execute plan
        assistant.set_state(AssistantState.EXECUTING)
        response_text, needs_confirm = execute_plan(plan)

        # 5. Respond
        assistant.set_state(AssistantState.RESPONDING)
        assistant.notify_response(response_text)

        # Speak via async TTS
        speak(response_text)

        # Log assistant response
        log_conversation(role="assistant", content=response_text)

        if not needs_confirm:
            assistant.set_state(AssistantState.IDLE)
        else:
            assistant.set_state(AssistantState.IDLE)

        return response_text


agent = DraxAgent()


def process_user_request(text: str) -> str:
    """Global convenience function for processing user requests."""
    return agent.process(text)
