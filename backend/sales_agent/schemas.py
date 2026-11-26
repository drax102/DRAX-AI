"""
backend/sales_agent/schemas.py — Pydantic data models for the Autonomous AI Sales Voice Agent.
Provides strongly-typed schemas for leads, scoring breakdown, conversation history, and API payloads.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict, EmailStr


class ScoreBreakdown(BaseModel):
    """Explainable BANT (Budget, Authority, Need, Timeline) scoring breakdown."""
    model_config = ConfigDict(from_attributes=True)

    budget_score: int = Field(default=0, ge=0, le=25, description="Budget score (0-25)")
    authority_score: int = Field(default=0, ge=0, le=25, description="Decision authority score (0-25)")
    need_score: int = Field(default=0, ge=0, le=25, description="Pain point/business need score (0-25)")
    timeline_score: int = Field(default=0, ge=0, le=25, description="Purchase timeline score (0-25)")
    total_score: int = Field(default=0, ge=0, le=100, description="Cumulative score (0-100)")
    reasoning: str = Field(default="", description="Human-readable explanation of the score")


class LeadBase(BaseModel):
    """Core attributes representing a sales lead."""
    model_config = ConfigDict(from_attributes=True)

    name: Optional[str] = Field(default=None, description="Customer name if volunteered")
    email: Optional[str] = Field(default=None, description="Contact email address")
    phone: Optional[str] = Field(default=None, description="Contact phone number")
    company: Optional[str] = Field(default=None, description="Customer organization/company")
    role: Optional[str] = Field(default=None, description="Job title or role in company")
    product_interest: Optional[str] = Field(default=None, description="Specific product, tier, or service of interest")
    budget: Optional[str] = Field(default=None, description="Mentioned budget or price range")
    timeline: Optional[str] = Field(default=None, description="Implementation timeline (e.g. 'immediate', '1-3 months')")
    authority: Optional[str] = Field(default=None, description="Decision-making authority (e.g. 'decision_maker', 'evaluator')")
    need: Optional[str] = Field(default=None, description="Core business challenge or use case")
    buying_intent: str = Field(default="unqualified", description="Intent level: 'high', 'medium', 'low', or 'unqualified'")
    qualification_status: str = Field(default="in_progress", description="Status: 'in_progress', 'qualified', 'disqualified', 'follow_up'")


class LeadCreate(LeadBase):
    """Schema for creating a new lead at the start of a conversation."""
    session_id: str = Field(..., description="Unique conversation session identifier")


class LeadUpdate(BaseModel):
    """Schema for updating an existing lead as conversation reveals more context."""
    model_config = ConfigDict(from_attributes=True)

    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    product_interest: Optional[str] = None
    budget: Optional[str] = None
    timeline: Optional[str] = None
    authority: Optional[str] = None
    need: Optional[str] = None
    buying_intent: Optional[str] = None
    lead_score: Optional[int] = Field(default=None, ge=0, le=100)
    score_breakdown: Optional[Dict[str, Any]] = None
    qualification_status: Optional[str] = None
    conversation_summary: Optional[str] = None


class LeadRead(LeadBase):
    """Schema for returning full lead details from the database."""
    id: int
    session_id: str
    lead_score: int = Field(default=0, ge=0, le=100)
    score_breakdown: Dict[str, Any] = Field(default_factory=dict)
    conversation_summary: str = Field(default="")
    created_at: str
    updated_at: str


class ConversationTurnCreate(BaseModel):
    """Schema for recording a single message turn."""
    model_config = ConfigDict(from_attributes=True)

    session_id: str
    role: str = Field(..., description="'user', 'assistant', or 'system'")
    content: str = Field(..., min_length=1, description="Text content of the message")


class ConversationTurnRead(BaseModel):
    """Schema for reading a recorded conversation turn from history."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: str
    role: str
    content: str
    timestamp: str


class ChatMessage(BaseModel):
    """Single chat completion message conforming to standard chat schema."""
    role: str = Field(..., description="'system', 'user', or 'assistant'")
    content: str = Field(..., description="Message text content")


class ConversationResponse(BaseModel):
    """Structured response returned by the Conversation Orchestrator."""
    model_config = ConfigDict(from_attributes=True)

    session_id: str
    response: str
    is_demo: bool
    model_used: str
    history_length: int
    lead_score: Optional[int] = None
    qualification_status: Optional[str] = None
    buying_intent: Optional[str] = None


class SessionCreateRequest(BaseModel):
    """Optional initial session initialization parameters."""
    model_config = ConfigDict(from_attributes=True)
    customer_name: Optional[str] = Field(default=None, description="Pre-identified customer name if available")
    company: Optional[str] = Field(default=None, description="Pre-identified company if available")


class SessionCreateResponse(BaseModel):
    """Confirmation payload returned when a new sales session is generated."""
    model_config = ConfigDict(from_attributes=True)
    session_id: str
    status: str = "initialized"
    created_at: str


class MessageRequest(BaseModel):
    """Payload for customer dialogue input."""
    model_config = ConfigDict(from_attributes=True)
    message: str = Field(..., min_length=1, max_length=2000, description="Customer text or voice transcript")


class SessionHistoryResponse(BaseModel):
    """Full dialogue history for a session."""
    model_config = ConfigDict(from_attributes=True)
    session_id: str
    turns: List[ConversationTurnRead]
    total_turns: int

