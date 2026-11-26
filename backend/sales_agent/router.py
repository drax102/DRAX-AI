"""
backend/sales_agent/router.py — FastAPI APIRouter for the Autonomous AI Sales Voice Agent.
Provides secure REST endpoints for session lifecycle, dialogue progression, history, and lead scoring.
Prefix: /api/sales
"""

import secrets
import logging
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status, Path

from backend.sales_agent.schemas import (
    SessionCreateRequest,
    SessionCreateResponse,
    MessageRequest,
    ConversationResponse,
    SessionHistoryResponse,
    LeadRead,
    LeadCreate,
)
from backend.sales_agent.database import (
    get_lead_by_session,
    create_lead,
    get_conversation_history,
)
from backend.sales_agent.conversation import orchestrator
from backend.sales_agent.llm_provider import (
    LLMTimeoutError,
    LLMCommunicationError,
    LLMResponseFormatError,
)

logger = logging.getLogger(__name__)

sales_router = APIRouter(prefix="/api/sales", tags=["Sales Voice Agent"])


@sales_router.post(
    "/sessions",
    response_model=SessionCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new sales conversation session",
)
def create_sales_session(payload: Optional[SessionCreateRequest] = None) -> SessionCreateResponse:
    """
    Initialize a new, unpredictable sales conversation session.
    Creates the corresponding lead entry in the isolated sales database.
    """
    # Cryptographically secure random token (128-bit entropy via secrets)
    session_id = f"sales_{secrets.token_hex(16)}"

    customer_name = payload.customer_name if payload else None
    company = payload.company if payload else None

    # Guarantee session is unique
    existing = get_lead_by_session(session_id)
    if existing:
        session_id = f"sales_{secrets.token_hex(16)}"

    lead_entry = create_lead(
        LeadCreate(
            session_id=session_id,
            name=customer_name,
            company=company,
        )
    )

    logger.info(f"Initialized new sales session '{session_id}'")
    return SessionCreateResponse(
        session_id=session_id,
        status="initialized",
        created_at=lead_entry.created_at,
    )


@sales_router.post(
    "/sessions/{session_id}/messages",
    response_model=ConversationResponse,
    summary="Send a customer message and receive a sales agent response",
)
def post_sales_message(
    session_id: str = Path(..., description="Unique sales session ID", min_length=4, max_length=64),
    payload: MessageRequest = ...,
) -> ConversationResponse:
    """
    Accept customer voice transcript or text, process consultative response via LLM,
    persist dialogue turns, and update BANT qualification scores.
    """
    clean_text = payload.message.strip()
    if not clean_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content cannot be blank or empty whitespace.",
        )

    # Verify session existence
    lead = get_lead_by_session(session_id)
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sales conversation session '{session_id}' not found.",
        )

    try:
        response = orchestrator.handle_message(
            session_id=session_id,
            message=clean_text,
        )
        return response

    except LLMTimeoutError as te:
        logger.error(f"LLM request timed out for session {session_id}: {te}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Upstream AI service timed out while processing dialogue. Please retry.",
        )
    except (LLMCommunicationError, LLMResponseFormatError) as ce:
        logger.error(f"LLM service failure for session {session_id}: {ce}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Upstream AI service error: {ce}",
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except Exception as e:
        logger.error(f"Unexpected error in sales conversation endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while generating sales dialogue.",
        )


@sales_router.get(
    "/sessions/{session_id}/history",
    response_model=SessionHistoryResponse,
    summary="Retrieve dialogue message history for a session",
)
def get_session_history(
    session_id: str = Path(..., description="Unique sales session ID", min_length=4, max_length=64),
) -> SessionHistoryResponse:
    """Retrieve all chronological conversation turns for the specified session."""
    lead = get_lead_by_session(session_id)
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sales conversation session '{session_id}' not found.",
        )

    turns = get_conversation_history(session_id, limit=100)
    return SessionHistoryResponse(
        session_id=session_id,
        turns=turns,
        total_turns=len(turns),
    )


@sales_router.get(
    "/sessions/{session_id}/lead",
    response_model=LeadRead,
    summary="Retrieve qualification details and BANT score breakdown for a session",
)
def get_session_lead(
    session_id: str = Path(..., description="Unique sales session ID", min_length=4, max_length=64),
) -> LeadRead:
    """
    Retrieve live BANT qualification fields, buying intent, and explainable score
    for a specific caller session.
    """
    lead = get_lead_by_session(session_id)
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sales conversation session '{session_id}' not found.",
        )

    return lead
