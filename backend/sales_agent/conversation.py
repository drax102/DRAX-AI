"""
backend/sales_agent/conversation.py — Multi-turn Conversation Orchestrator for the Sales Voice Agent.
Coordinates session continuity, history retrieval, prompt assembly, LLM execution, and message persistence.
"""

import logging
from typing import Optional, List, Dict, Any

from backend.sales_agent.database import (
    get_lead_by_session,
    create_lead,
    record_conversation_turn,
    get_conversation_history,
)
from backend.sales_agent.schemas import (
    LeadCreate,
    ConversationTurnCreate,
    ConversationResponse,
)
from backend.sales_agent.llm_provider import (
    BaseLLMProvider,
    get_llm_provider,
)
from backend.sales_agent.lead_qualifier import qualify_lead_from_session

logger = logging.getLogger(__name__)

DEFAULT_SALES_SYSTEM_PROMPT = """
You are DRAX AI, an intelligent and professional AI Sales Consultant.

YOUR OBJECTIVE:
Understand the customer's business, identify their requirements,
qualify potential leads, and guide them towards the appropriate next step.

CONVERSATION RULES:

1. Understand the complete conversation history before responding.

2. Always acknowledge the customer's latest message.
Never respond with an unrelated generic greeting.

3. Ask only ONE relevant follow-up question at a time.

4. Never repeat a question that the customer has already answered.

5. Remember information shared in previous messages.

6. Collect these details naturally:
   - Customer name
   - Company name
   - Product interest
   - Business problem
   - Budget
   - Decision-making authority
   - Purchase timeline

7. Ask about missing information only when relevant.
Do not interrogate the customer with all questions at once.

8. Handle ambiguous statements by asking for clarification.

9. For example, if someone says:
   "I want to grow from $20 to $20,000"
   Ask whether they mean business revenue, software budget,
   account balance, or another financial target.

10. If someone wants to automatically fetch accounts,
clarify which accounts and which platform they mean.
Never request passwords, API keys or sensitive credentials.

11. Never invent pricing, product features, customer information,
or guarantees.

12. Never assume a customer is the decision-maker based
only on their job title.

13. Keep responses natural, friendly and professional.
Normally respond in 2–4 sentences.

14. If sufficient information has been collected,
summarize the customer's requirements and suggest
an appropriate next step.

IMPORTANT:
Lead qualification and BANT scoring are handled separately
by the Python backend.

Never invent a numerical lead score.

Your conversation should feel like speaking to a knowledgeable
human sales consultant, not interacting with a scripted chatbot.
"""


class ConversationOrchestrator:
    """
    Manages end-to-end sales dialogue for a customer session.
    Retrieves history, constructs message arrays, triggers LLM inference, and persists dialogue turns.
    """

    def __init__(
        self,
        llm_provider: Optional[BaseLLMProvider] = None,
        system_prompt: str = DEFAULT_SALES_SYSTEM_PROMPT,
        history_window: int = 15,
    ):
        self.llm_provider = llm_provider
        self.system_prompt = system_prompt
        self.history_window = history_window

    def _ensure_session_exists(self, session_id: str, db_path: Optional[str] = None) -> None:
        """Verify that a lead record exists for session_id, creating an initial record if absent."""
        existing = get_lead_by_session(session_id, db_path=db_path)
        if not existing:
            create_lead(LeadCreate(session_id=session_id), db_path=db_path)

    def handle_message(
        self,
        session_id: str,
        message: str,
        db_path: Optional[str] = None,
    ) -> ConversationResponse:
        """
        Process an incoming user message within a persistent conversation session.
        1. Ensures session exists in the database.
        2. Records the incoming customer message.
        3. Assembles system prompt and previous conversation turns.
        4. Calls the LLM provider (or demo mode fallback).
        5. Records the assistant's reply.
        6. Returns a structured ConversationResponse.
        """
        clean_msg = message.strip()
        if not clean_msg:
            raise ValueError("Customer message cannot be empty or blank.")

        # 1. Maintain session record in database
        self._ensure_session_exists(session_id, db_path=db_path)

        # 2. Persist customer turn
        record_conversation_turn(
            ConversationTurnCreate(session_id=session_id, role="user", content=clean_msg),
            db_path=db_path,
        )

        # 3. Retrieve recent history for context
        history_turns = get_conversation_history(
            session_id=session_id,
            limit=self.history_window,
            db_path=db_path,
        )

        # 4. Assemble standard chat completion payload
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": self.system_prompt}
        ]
        for turn in history_turns:
            messages.append({"role": turn.role, "content": turn.content})

        # 5. Execute LLM call
        provider = self.llm_provider or get_llm_provider()
        reply_text = provider.generate_response(messages)

        # 6. Persist assistant turn
        record_conversation_turn(
            ConversationTurnCreate(session_id=session_id, role="assistant", content=reply_text),
            db_path=db_path,
        )

        # 7. Incrementally qualify lead and update BANT score
        score_val = None
        qual_status = None
        intent_val = None
        try:
            qualified = qualify_lead_from_session(session_id=session_id, db_path=db_path)
            if qualified:
                score_val = qualified.lead_score
                qual_status = qualified.qualification_status
                intent_val = qualified.buying_intent
        except Exception as qe:
            logger.warning(f"Lead qualification pipeline notice for {session_id}: {qe}")

        # 8. Return structured response
        return ConversationResponse(
            session_id=session_id,
            response=reply_text,
            is_demo=provider.is_demo,
            model_used=provider.model_name,
            history_length=len(history_turns) + 1,
            lead_score=score_val,
            qualification_status=qual_status,
            buying_intent=intent_val,
        )


# Default singleton orchestrator
orchestrator = ConversationOrchestrator()
