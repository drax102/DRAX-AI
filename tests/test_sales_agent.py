"""
tests/test_sales_agent.py — Targeted unit tests for the Autonomous AI Sales Voice Agent.
Validates Pydantic schemas, isolated database initialization, CRUD operations,
score breakdown serialization, conversation turns, and Drax AI database isolation.
"""

import os
import tempfile
import pytest
from pydantic import ValidationError

from backend.sales_agent.schemas import (
    ScoreBreakdown,
    LeadCreate,
    LeadUpdate,
    LeadRead,
    ConversationTurnCreate,
    ConversationTurnRead,
)
from backend.sales_agent.database import (
    init_sales_db,
    create_lead,
    get_lead_by_id,
    get_lead_by_session,
    update_lead,
    list_leads,
    delete_lead,
    record_conversation_turn,
    get_conversation_history,
)


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database for testing, cleaned up after each test."""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_sales_agent.db")
    init_sales_db(db_path)
    yield db_path
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)
    except Exception:
        pass


# ─── 1. Pydantic Schema Validation Tests ─────────────────────────────────────

def test_score_breakdown_validation():
    """Verify BANT score breakdown bounds and total calculation."""
    breakdown = ScoreBreakdown(
        budget_score=20,
        authority_score=25,
        need_score=25,
        timeline_score=15,
        total_score=85,
        reasoning="Strong budget and authority with Q3 timeline.",
    )
    assert breakdown.total_score == 85
    assert breakdown.budget_score == 20

    # Test out of bounds (score > 25 for component)
    with pytest.raises(ValidationError):
        ScoreBreakdown(budget_score=30)

    # Test out of bounds (total > 100)
    with pytest.raises(ValidationError):
        ScoreBreakdown(total_score=110)


def test_lead_create_and_read_schema():
    """Verify LeadCreate enforces session_id and LeadRead handles fields properly."""
    lead = LeadCreate(
        session_id="sess_12345",
        name="Alice Johnson",
        company="TechCorp",
        role="CTO",
        need="Automate customer qualification calls",
        budget="$20,000/year",
        timeline="Next month",
        authority="decision_maker",
    )
    assert lead.session_id == "sess_12345"
    assert lead.name == "Alice Johnson"
    assert lead.buying_intent == "unqualified"
    assert lead.qualification_status == "in_progress"

    # session_id is required
    with pytest.raises(ValidationError):
        LeadCreate()  # type: ignore


# ─── 2. Database CRUD & Isolation Tests ───────────────────────────────────────

def test_create_and_retrieve_lead(temp_db):
    """Test creating a lead and retrieving by both ID and session_id."""
    lead_in = LeadCreate(
        session_id="sess_alpha",
        name="Bob Smith",
        email="bob@acme.com",
        phone="+1-555-0199",
        company="Acme Corp",
        role="Head of Operations",
        product_interest="Enterprise Plan",
        need="Inbound voice AI qualification",
        budget="$50,000",
        timeline="Immediate",
        authority="decision_maker",
        buying_intent="high",
        qualification_status="qualified",
    )

    created = create_lead(lead_in, db_path=temp_db)
    assert created.id is not None
    assert created.session_id == "sess_alpha"
    assert created.name == "Bob Smith"
    assert created.lead_score == 0

    # Retrieve by ID
    by_id = get_lead_by_id(created.id, db_path=temp_db)
    assert by_id is not None
    assert by_id.name == "Bob Smith"
    assert by_id.email == "bob@acme.com"

    # Retrieve by session_id
    by_session = get_lead_by_session("sess_alpha", db_path=temp_db)
    assert by_session is not None
    assert by_session.company == "Acme Corp"


def test_update_lead(temp_db):
    """Test incremental updates to lead score, status, and summary."""
    lead_in = LeadCreate(session_id="sess_beta", name="Charlie")
    created = create_lead(lead_in, db_path=temp_db)

    # Perform partial update
    score_data = {
        "budget_score": 20,
        "authority_score": 20,
        "need_score": 25,
        "timeline_score": 20,
        "total_score": 85,
        "reasoning": "Decision maker with explicit $10k budget",
    }
    update_data = LeadUpdate(
        company="Innovate AI",
        budget="$10,000",
        lead_score=85,
        score_breakdown=score_data,
        qualification_status="qualified",
        conversation_summary="Customer requested live demo next Tuesday.",
    )

    updated = update_lead("sess_beta", update_data, db_path=temp_db)
    assert updated is not None
    assert updated.company == "Innovate AI"
    assert updated.lead_score == 85
    assert updated.score_breakdown == score_data
    assert updated.qualification_status == "qualified"
    assert "live demo" in updated.conversation_summary


def test_list_leads_filtering_and_pagination(temp_db):
    """Test listing leads with qualification status and score filtering."""
    create_lead(LeadCreate(session_id="s1", name="Lead 1", qualification_status="qualified"), db_path=temp_db)
    create_lead(LeadCreate(session_id="s2", name="Lead 2", qualification_status="in_progress"), db_path=temp_db)
    create_lead(LeadCreate(session_id="s3", name="Lead 3", qualification_status="qualified"), db_path=temp_db)

    update_lead("s1", LeadUpdate(lead_score=90), db_path=temp_db)
    update_lead("s2", LeadUpdate(lead_score=40), db_path=temp_db)
    update_lead("s3", LeadUpdate(lead_score=75), db_path=temp_db)

    # All leads
    all_leads = list_leads(db_path=temp_db)
    assert len(all_leads) == 3

    # Filter by status
    qualified_leads = list_leads(status="qualified", db_path=temp_db)
    assert len(qualified_leads) == 2

    # Filter by minimum score
    high_score_leads = list_leads(min_score=80, db_path=temp_db)
    assert len(high_score_leads) == 1
    assert high_score_leads[0].name == "Lead 1"

    # Pagination
    page_1 = list_leads(limit=2, offset=0, db_path=temp_db)
    assert len(page_1) == 2


def test_conversation_turns_and_cascade_delete(temp_db):
    """Test recording conversation history and cascade deletion upon lead removal."""
    create_lead(LeadCreate(session_id="sess_gamma", name="Diana"), db_path=temp_db)

    # Record message turns
    t1 = record_conversation_turn(
        ConversationTurnCreate(session_id="sess_gamma", role="assistant", content="Hello, thanks for reaching out!"),
        db_path=temp_db,
    )
    t2 = record_conversation_turn(
        ConversationTurnCreate(session_id="sess_gamma", role="user", content="Hi, I need pricing for 50 users."),
        db_path=temp_db,
    )
    assert t1.id is not None
    assert t2.id is not None

    # Retrieve history
    history = get_conversation_history("sess_gamma", db_path=temp_db)
    assert len(history) == 2
    assert history[0].role == "assistant"
    assert history[1].role == "user"
    assert "50 users" in history[1].content

    # Delete lead and verify cascade deletion of turns
    deleted = delete_lead("sess_gamma", db_path=temp_db)
    assert deleted is True
    assert get_lead_by_session("sess_gamma", db_path=temp_db) is None
    assert len(get_conversation_history("sess_gamma", db_path=temp_db)) == 0


def test_isolation_from_drax_database():
    """Verify that the default sales DB path is distinct from Drax's drax.db."""
    from backend.sales_agent.database import resolve_db_path
    from backend.database.db import _DB_PATH as DRAX_DB_PATH

    sales_path = resolve_db_path()
    assert "sales_agent.db" in sales_path
    assert sales_path != DRAX_DB_PATH
    assert os.path.basename(sales_path) != os.path.basename(DRAX_DB_PATH)


# ─── 3. LLM Provider & Demo Mode Tests ───────────────────────────────────────

from unittest.mock import MagicMock
import httpx
from backend.sales_agent.llm_provider import (
    BaseLLMProvider,
    DemoLLMProvider,
    OpenAICompatibleProvider,
    get_llm_provider,
    LLMConfigurationError,
    LLMCommunicationError,
    LLMTimeoutError,
    LLMResponseFormatError,
)
from backend.sales_agent.conversation import (
    ConversationOrchestrator,
    DEFAULT_SALES_SYSTEM_PROMPT,
)


def test_demo_provider_responses():
    """Verify DemoLLMProvider generates deterministic, contextual, and labeled responses."""
    demo = DemoLLMProvider()
    assert demo.is_demo is True
    assert demo.model_name == "demo-sales-engine"

    # Greeting
    r1 = demo.generate_response([{"role": "user", "content": "Hello there!"}])
    assert "DRAX AI's Sales Assistant" in r1

    # Pricing
    r2 = demo.generate_response([{"role": "user", "content": "How much does the enterprise plan cost?"}])
    assert "pricing" in r2.lower() or "plans scale" in r2.lower() or "quote" in r2.lower()

    # Timeline
    r3 = demo.generate_response([{"role": "user", "content": "We need this implemented next month."}])
    assert "timeline" in r3.lower() or "onboarding" in r3.lower()


def test_get_llm_provider_selection(monkeypatch):
    """Verify factory returns DemoLLMProvider when no key is set and OpenAI provider when set."""
    # When no key is set
    monkeypatch.delenv("SALES_LLM_API_KEY", raising=False)
    p1 = get_llm_provider()
    assert isinstance(p1, DemoLLMProvider)
    assert p1.is_demo is True

    # When key is configured
    monkeypatch.setenv("SALES_LLM_API_KEY", "sk-mock-valid-key-12345")
    p2 = get_llm_provider()
    assert isinstance(p2, OpenAICompatibleProvider)
    assert p2.is_demo is False


def test_openai_provider_missing_key():
    """Verify instantiating OpenAICompatibleProvider without a key raises LLMConfigurationError."""
    with pytest.raises(LLMConfigurationError):
        OpenAICompatibleProvider(api_key="")


def test_openai_provider_mock_success():
    """Verify OpenAICompatibleProvider sends expected chat payload and parses response."""
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {"message": {"role": "assistant", "content": "We can certainly schedule a demo for your team."}}
        ]
    }
    mock_client.post.return_value = mock_resp

    provider = OpenAICompatibleProvider(
        api_key="sk-test-key-abc",
        base_url="https://mock.api.com/v1",
        model="mock-gpt",
        client=mock_client,
    )
    res = provider.generate_response([{"role": "user", "content": "Can we see a demo?"}])
    assert res == "We can certainly schedule a demo for your team."
    assert provider.is_demo is False
    assert provider.model_name == "mock-gpt"

    # Verify payload contains only required model and messages without optional unsupported parameters
    called_endpoint = mock_client.post.call_args[0][0]
    called_payload = mock_client.post.call_args[1]["json"]
    assert called_endpoint == "https://mock.api.com/v1/chat/completions"
    assert "model" in called_payload
    assert "messages" in called_payload
    assert "temperature" not in called_payload
    assert "logprobs" not in called_payload
    assert "logit_bias" not in called_payload


def test_openai_provider_http_400_response_handling():
    """Verify HTTP 400 responses from upstream (e.g. Groq) safely capture error details and redact keys."""
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.json.return_value = {
        "error": {
            "message": "Unsupported parameter: 'temperature'. Failed with key gsk_abc1234567890xyz",
            "type": "invalid_request_error",
            "code": "parameter_unsupported",
        }
    }
    mock_resp.text = '{"error": {"message": "Unsupported parameter: \'temperature\'"}}'
    mock_req = MagicMock()
    mock_client.post.side_effect = httpx.HTTPStatusError(
        "400 Client Error: Bad Request",
        request=mock_req,
        response=mock_resp,
    )

    provider = OpenAICompatibleProvider(
        api_key="gsk-test-key-12345",
        client=mock_client,
    )

    with pytest.raises(LLMCommunicationError) as exc_info:
        provider.generate_response([{"role": "user", "content": "Hello"}])

    error_msg = str(exc_info.value)
    # Verify error code and message detail are captured
    assert "HTTP 400" in error_msg
    assert "Unsupported parameter: 'temperature'" in error_msg
    # Verify sensitive Groq API key is masked
    assert "gsk_abc1234567890xyz" not in error_msg
    assert "[REDACTED_API_KEY]" in error_msg
    # Ensure provider remains strictly non-demo (no silent fallback)
    assert provider.is_demo is False


def test_openai_provider_timeout():
    """Verify OpenAICompatibleProvider raises LLMTimeoutError on network timeouts."""
    mock_client = MagicMock()
    mock_client.post.side_effect = httpx.TimeoutException("Connection timed out")

    provider = OpenAICompatibleProvider(
        api_key="sk-test-key-abc",
        client=mock_client,
    )
    with pytest.raises(LLMTimeoutError):
        provider.generate_response([{"role": "user", "content": "Hello"}])


def test_openai_provider_http_error_and_key_redaction():
    """Verify HTTP errors raise LLMCommunicationError and redact sensitive tokens."""
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "Unauthorized. Bearer sk-secret-1234567890 is invalid."
    mock_req = MagicMock()
    mock_client.post.side_effect = httpx.HTTPStatusError(
        "401 Client Error",
        request=mock_req,
        response=mock_resp,
    )

    provider = OpenAICompatibleProvider(
        api_key="sk-test-key-abc",
        client=mock_client,
    )
    with pytest.raises(LLMCommunicationError) as exc_info:
        provider.generate_response([{"role": "user", "content": "Hello"}])

    error_msg = str(exc_info.value)
    assert "sk-secret-1234567890" not in error_msg
    assert "[REDACTED]" in error_msg


def test_openai_provider_malformed_response():
    """Verify malformed JSON or missing fields raise LLMResponseFormatError."""
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"error": "unexpected format", "choices": []}
    mock_client.post.return_value = mock_resp

    provider = OpenAICompatibleProvider(
        api_key="sk-test-key-abc",
        client=mock_client,
    )
    with pytest.raises(LLMResponseFormatError):
        provider.generate_response([{"role": "user", "content": "Hello"}])


# ─── 4. Conversation Orchestrator Tests ──────────────────────────────────────

def test_conversation_orchestrator_multi_turn(temp_db):
    """Test multi-turn conversation flow, session preservation, and history logging."""
    demo_llm = DemoLLMProvider()
    orch = ConversationOrchestrator(llm_provider=demo_llm)

    # Turn 1
    resp1 = orch.handle_message(
        session_id="session_orch_101",
        message="Hi, I am looking for an AI voice solution.",
        db_path=temp_db,
    )
    assert resp1.session_id == "session_orch_101"
    assert resp1.is_demo is True
    assert resp1.model_used == "demo-sales-engine"
    assert resp1.history_length == 2  # 1 user + 1 assistant

    # Turn 2
    resp2 = orch.handle_message(
        session_id="session_orch_101",
        message="What is the pricing for a team of 20?",
        db_path=temp_db,
    )
    assert resp2.history_length == 4  # 2 user + 2 assistant

    # Verify history in database
    history = get_conversation_history("session_orch_101", db_path=temp_db)
    assert len(history) == 4
    assert history[0].role == "user"
    assert history[1].role == "assistant"
    assert history[2].role == "user"
    assert history[3].role == "assistant"


def test_conversation_orchestrator_empty_message(temp_db):
    """Verify empty message throws ValueError."""
    orch = ConversationOrchestrator(llm_provider=DemoLLMProvider())
    with pytest.raises(ValueError):
        orch.handle_message("sess_empty", "   ", db_path=temp_db)


# ─── 5. Milestone 3: Lead Qualification & Explainable BANT Scoring Tests ──────

from backend.sales_agent.lead_scoring import (
    calculate_lead_score,
    determine_qualification_status,
    determine_buying_intent,
    evaluate_budget_score,
    evaluate_authority_score,
    evaluate_need_score,
    evaluate_timeline_score,
)
from backend.sales_agent.lead_qualifier import (
    extract_regex_entities,
    merge_extracted_into_lead,
    qualify_lead_from_session,
)


def test_complete_bant_scoring():
    """Verify full BANT inputs produce maximum 100 points, detailed reasoning, and qualified status."""
    breakdown = calculate_lead_score(
        budget="$50,000",
        authority="sole decision maker",
        need="automate customer support calls",
        timeline="immediate",
    )
    assert breakdown.budget_score == 25
    assert breakdown.authority_score == 25
    assert breakdown.need_score == 25
    assert breakdown.timeline_score == 25
    assert breakdown.total_score == 100
    assert "Budget: Substantial verified budget" in breakdown.reasoning
    assert "Authority: Confirmed primary decision-maker" in breakdown.reasoning
    assert "Need: High-impact business problem" in breakdown.reasoning
    assert "Timeline: Urgent launch planned" in breakdown.reasoning

    status = determine_qualification_status(breakdown, "$50,000", "automate customer support calls")
    assert status == "qualified"

    intent = determine_buying_intent(breakdown, "We want to start immediately and schedule demo", "immediate", "$50,000")
    assert intent == "high"


def test_missing_bant_components_score_zero():
    """Verify that any missing BANT category receives 0 points with explicit reasoning."""
    # 1. Missing budget
    b_score, b_reason = evaluate_budget_score(None)
    assert b_score == 0
    assert "Not yet disclosed" in b_reason

    # 2. Missing authority
    a_score, a_reason = evaluate_authority_score("")
    assert a_score == 0
    assert "not yet verified" in a_reason

    # 3. Missing need
    n_score, n_reason = evaluate_need_score(None)
    assert n_score == 0
    assert "not yet identified" in n_reason

    # 4. Missing timeline
    t_score, t_reason = evaluate_timeline_score("   ")
    assert t_score == 0
    assert "not yet discussed" in t_reason

    # Combined missing
    partial_score = calculate_lead_score(
        budget=None,
        authority=None,
        need="explore voice AI",
        timeline=None,
    )
    assert partial_score.budget_score == 0
    assert partial_score.authority_score == 0
    assert partial_score.timeline_score == 0
    assert partial_score.need_score == 15
    assert partial_score.total_score == 15


def test_authority_not_assumed_from_job_title():
    """Verify authority requires explicit role verification and is not assumed from title."""
    # Merely stating title gives 0 if authority field is not set
    assert evaluate_authority_score(None)[0] == 0

    # Confirmed sole decision maker
    s_score, _ = evaluate_authority_score("I am the sole decision maker for software purchases")
    assert s_score == 25

    # Member of evaluation team
    c_score, _ = evaluate_authority_score("I am evaluating with my team to make a recommendation")
    assert c_score == 18

    # Explicitly no authority
    no_score, no_reason = evaluate_authority_score("I am a student with no purchasing authority")
    assert no_score == 0
    assert "no purchasing authority" in no_reason


def test_buying_intent_not_inferred_from_company_name():
    """Verify providing a company name alone does NOT classify buying intent as high."""
    breakdown = calculate_lead_score(budget=None, authority=None, need=None, timeline=None)
    intent = determine_buying_intent(breakdown, customer_statements="I work at Microsoft", timeline=None, budget=None)
    assert intent != "high"
    assert intent == "unqualified"

    # High intent requires explicit purchase signals
    high_intent = determine_buying_intent(
        breakdown,
        customer_statements="We are ready to buy and want a proposal sent today",
        timeline="asap",
        budget="$15,000",
    )
    assert high_intent == "high"


def test_disqualification_rules():
    """Verify customer reporting no budget is marked disqualified."""
    breakdown = calculate_lead_score(budget="no budget, $0", authority="sole decision maker", need="automate calls", timeline="asap")
    assert breakdown.budget_score == 0
    status = determine_qualification_status(breakdown, budget="no budget, $0", need="automate calls")
    assert status == "disqualified"


def test_score_boundaries():
    """Verify scoring logic strictly enforces 0-25 per category and 0-100 total."""
    breakdown = calculate_lead_score(
        budget="$1,000,000 enterprise custom allocation",
        authority="sole decision maker final sign-off",
        need="critical call automation replace manual SLAs",
        timeline="urgent immediate today",
    )
    assert 0 <= breakdown.budget_score <= 25
    assert 0 <= breakdown.authority_score <= 25
    assert 0 <= breakdown.need_score <= 25
    assert 0 <= breakdown.timeline_score <= 25
    assert 0 <= breakdown.total_score <= 100


def test_regex_entity_extraction():
    """Verify regex entity extraction correctly extracts contact details, BANT elements, and company."""
    sample = (
        "Hello, my name is Marcus Vance from Apex Technologies. "
        "You can reach me at marcus@apextech.com or 415-555-0199. "
        "We need to automate call qualification because of high volume. "
        "Our budget is $30,000 and we want to launch within 1-3 months. "
        "I am the sole decision maker."
    )
    extracted = extract_regex_entities(sample)
    assert extracted["name"] == "Marcus Vance"
    assert extracted["email"] == "marcus@apextech.com"
    assert "415-555-0199" in extracted["phone"]
    assert "Apex Technologies" in extracted["company"]
    assert "30,000" in extracted["budget"]
    assert "1-3 months" in extracted["timeline"].lower()
    assert extracted["authority"] == "sole_decision_maker"
    assert "automate call qualification" in extracted["need"].lower()


def test_preservation_of_existing_lead_info_across_turns(temp_db):
    """
    CRITICAL: Verify that multi-turn conversations incrementally update lead details
    WITHOUT overwriting previously captured fields.
    """
    orch = ConversationOrchestrator(llm_provider=DemoLLMProvider())
    sess = "sess_preserve_101"

    # Turn 1: Customer introduces self, company, and email
    r1 = orch.handle_message(sess, "Hi, my name is Elena Rostova from Quantum AI. My email is elena@quantum.io.", db_path=temp_db)
    lead_t1 = get_lead_by_session(sess, db_path=temp_db)
    assert lead_t1 is not None
    assert lead_t1.name == "Elena Rostova"
    assert "Quantum" in lead_t1.company
    assert lead_t1.email == "elena@quantum.io"

    # Turn 2: Customer specifies business need and timeline (does NOT repeat name or company)
    r2 = orch.handle_message(sess, "We need to automate customer support calls within next month.", db_path=temp_db)
    lead_t2 = get_lead_by_session(sess, db_path=temp_db)
    assert lead_t2 is not None
    # Previous fields MUST be preserved!
    assert lead_t2.name == "Elena Rostova"
    assert "Quantum" in lead_t2.company
    assert lead_t2.email == "elena@quantum.io"
    # New fields added
    assert "automate customer support" in lead_t2.need.lower()
    assert "next month" in lead_t2.timeline.lower()

    # Turn 3: Customer provides budget and authority
    r3 = orch.handle_message(sess, "Our budget is $25,000 and I am the sole decision maker.", db_path=temp_db)
    lead_t3 = get_lead_by_session(sess, db_path=temp_db)
    assert lead_t3 is not None
    # All historical fields intact!
    assert lead_t3.name == "Elena Rostova"
    assert lead_t3.email == "elena@quantum.io"
    assert "Quantum" in lead_t3.company
    assert "25,000" in lead_t3.budget
    assert lead_t3.authority == "sole_decision_maker"

    # Score should be high and status qualified
    assert lead_t3.lead_score >= 80
    assert lead_t3.qualification_status == "qualified"
    assert lead_t3.buying_intent in ["high", "medium"]


def test_ambiguous_customer_responses(temp_db):
    """Verify ambiguous statements do not create fake BANT points."""
    orch = ConversationOrchestrator(llm_provider=DemoLLMProvider())
    sess = "sess_ambiguous_102"

    r = orch.handle_message(sess, "I am just looking around, maybe interested later.", db_path=temp_db)
    lead = get_lead_by_session(sess, db_path=temp_db)
    assert lead is not None
    assert lead.budget is None
    assert lead.authority is None
    assert lead.lead_score < 30
    assert lead.qualification_status != "qualified"


# ─── 6. Milestone 4: FastAPI REST API Integration Tests ───────────────────────

from fastapi.testclient import TestClient
from backend.services.api_service import api_app


@pytest.fixture
def sales_client(temp_db, monkeypatch):
    """FastAPI TestClient wired to an isolated temporary sales database."""
    monkeypatch.setenv("SALES_DB_PATH", temp_db)
    with TestClient(api_app) as client:
        yield client


def test_api_create_session(sales_client):
    """Test POST /api/sales/sessions generates unique, initialized sessions."""
    res = sales_client.post(
        "/api/sales/sessions",
        json={"customer_name": "Bruce Wayne", "company": "Wayne Enterprises"},
    )
    assert res.status_code == 201
    data = res.json()
    assert "session_id" in data
    assert data["session_id"].startswith("sales_")
    assert data["status"] == "initialized"
    assert "created_at" in data


def test_api_dialogue_lifecycle_and_history(sales_client):
    """Test sending dialogue messages, retrieving history, and fetching lead details."""
    # 1. Create Session
    create_res = sales_client.post(
        "/api/sales/sessions",
        json={"customer_name": "Tony Stark", "company": "Stark Industries"},
    )
    assert create_res.status_code == 201
    sess_id = create_res.json()["session_id"]

    # 2. Turn 1 Message
    msg1_res = sales_client.post(
        f"/api/sales/sessions/{sess_id}/messages",
        json={"message": "Hi, we need to automate customer support calls for 100 agents."},
    )
    assert msg1_res.status_code == 200
    msg1_data = msg1_res.json()
    assert msg1_data["session_id"] == sess_id
    assert msg1_data["is_demo"] is True
    assert msg1_data["model_used"] == "demo-sales-engine"
    assert msg1_data["history_length"] == 2
    assert len(msg1_data["response"]) > 0

    # 3. Turn 2 Message (Budget & Authority)
    msg2_res = sales_client.post(
        f"/api/sales/sessions/{sess_id}/messages",
        json={"message": "Our budget is $50,000 for launch next month and I am the sole decision maker."},
    )
    assert msg2_res.status_code == 200
    msg2_data = msg2_res.json()
    assert msg2_data["history_length"] == 4
    assert msg2_data["lead_score"] is not None
    assert msg2_data["lead_score"] >= 80
    assert msg2_data["qualification_status"] == "qualified"

    # 4. Fetch History
    hist_res = sales_client.get(f"/api/sales/sessions/{sess_id}/history")
    assert hist_res.status_code == 200
    hist_data = hist_res.json()
    assert hist_data["session_id"] == sess_id
    assert hist_data["total_turns"] == 4
    assert hist_data["turns"][0]["role"] == "user"
    assert hist_data["turns"][1]["role"] == "assistant"

    # 5. Fetch Lead Details
    lead_res = sales_client.get(f"/api/sales/sessions/{sess_id}/lead")
    assert lead_res.status_code == 200
    lead_data = lead_res.json()
    assert lead_data["session_id"] == sess_id
    assert lead_data["name"] == "Tony Stark"
    assert lead_data["company"] == "Stark Industries"
    assert "50,000" in lead_data["budget"]
    assert lead_data["lead_score"] >= 80
    assert "score_breakdown" in lead_data
    assert lead_data["score_breakdown"]["budget_score"] == 25


def test_api_invalid_messages(sales_client):
    """Test validation errors for empty or whitespace messages."""
    # Create valid session
    sess = sales_client.post("/api/sales/sessions").json()["session_id"]

    # Whitespace message returns 400
    res_blank = sales_client.post(
        f"/api/sales/sessions/{sess}/messages",
        json={"message": "   \n\t  "},
    )
    assert res_blank.status_code == 400
    assert "blank or empty" in res_blank.json()["detail"]

    # Empty payload returns 422 Unprocessable Entity (Pydantic min_length=1)
    res_empty = sales_client.post(
        f"/api/sales/sessions/{sess}/messages",
        json={"message": ""},
    )
    assert res_empty.status_code == 422


def test_api_missing_session_returns_404(sales_client):
    """Verify non-existent sessions return 404 for messages, history, and lead endpoints."""
    bad_sess = "sales_nonexistent_999"

    # Post message to invalid session
    res_msg = sales_client.post(
        f"/api/sales/sessions/{bad_sess}/messages",
        json={"message": "Hello"},
    )
    assert res_msg.status_code == 404
    assert "not found" in res_msg.json()["detail"].lower()

    # Get history of invalid session
    res_hist = sales_client.get(f"/api/sales/sessions/{bad_sess}/history")
    assert res_hist.status_code == 404

    # Get lead of invalid session
    res_lead = sales_client.get(f"/api/sales/sessions/{bad_sess}/lead")
    assert res_lead.status_code == 404


def test_api_upstream_llm_failure_handling(sales_client, monkeypatch):
    """Verify LLM timeout returns 504 and LLM communication error returns 502."""
    sess = sales_client.post("/api/sales/sessions").json()["session_id"]

    from backend.sales_agent.llm_provider import LLMTimeoutError, LLMCommunicationError

    # Test 504 Gateway Timeout
    def mock_timeout(*args, **kwargs):
        raise LLMTimeoutError("Remote LLM timed out after 15s")

    monkeypatch.setattr("backend.sales_agent.conversation.orchestrator.handle_message", mock_timeout)
    res_timeout = sales_client.post(
        f"/api/sales/sessions/{sess}/messages",
        json={"message": "What is the price?"},
    )
    assert res_timeout.status_code == 504
    assert "timed out" in res_timeout.json()["detail"].lower()

    # Test 502 Bad Gateway
    def mock_comm_error(*args, **kwargs):
        raise LLMCommunicationError("HTTP 500 from provider")

    monkeypatch.setattr("backend.sales_agent.conversation.orchestrator.handle_message", mock_comm_error)
    res_502 = sales_client.post(
        f"/api/sales/sessions/{sess}/messages",
        json={"message": "What is the price?"},
    )
    assert res_502.status_code == 502
    assert "error" in res_502.json()["detail"].lower()


def test_existing_drax_routes_unaffected(sales_client):
    """Verify that existing Drax AI API endpoints continue to function without regression."""
    # 1. GET /status
    res_status = sales_client.get("/status")
    assert res_status.status_code == 200
    assert "assistant_name" in res_status.json()

    # 2. GET /tasks
    res_tasks = sales_client.get("/tasks")
    assert res_tasks.status_code == 200
    assert "tasks" in res_tasks.json()

    # 3. GET /settings
    res_settings = sales_client.get("/settings")
    assert res_settings.status_code == 200


def test_session_id_entropy_and_uniqueness(sales_client):
    """
    Verify session IDs use cryptographically secure tokens with 128-bit entropy,
    have the correct format ('sales_' + 32 hex chars = 38 chars total),
    and produce strictly unique IDs across multiple consecutive generations.
    """
    import re
    session_ids = set()
    total_samples = 40

    for _ in range(total_samples):
        res = sales_client.post("/api/sales/sessions")
        assert res.status_code == 201
        sid = res.json()["session_id"]

        # Validate format: sales_ followed by 32 hex characters (16 bytes CSPRNG)
        assert sid.startswith("sales_"), f"Invalid prefix for session ID: {sid}"
        assert len(sid) == 38, f"Expected 38 characters (sales_ + 32 hex), got {len(sid)}: {sid}"
        assert re.match(r"^sales_[0-9a-f]{32}$", sid), f"Session ID does not match expected regex: {sid}"

        session_ids.add(sid)

    # Guarantee zero collisions across all samples
    assert len(session_ids) == total_samples, "Collision detected in cryptographically generated session IDs!"


def test_xss_payload_safety_in_message(sales_client):
    """
    Verify that raw HTML or script tags in customer messages are accepted as raw data
    without server-side error, and preserved verbatim for safe frontend textContent rendering.
    """
    sess = sales_client.post("/api/sales/sessions").json()["session_id"]

    xss_payload = "<script>alert('xss');</script><img src=x onerror=alert(1)>"
    res = sales_client.post(
        f"/api/sales/sessions/{sess}/messages",
        json={"message": f"Hello, I am testing security: {xss_payload}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "response" in data

    # Verify message is persisted in history without crashing
    hist = sales_client.get(f"/api/sales/sessions/{sess}/history").json()
    turns = hist["turns"]
    assert any(xss_payload in t["content"] for t in turns)


def test_api_app_sales_and_drax_routes_registered():
    """
    Regression test verifying that importing api_app from backend.services.api_service
    has all four Sales Voice Agent routes registered directly on the application instance,
    and all original Drax endpoints remain intact.
    """
    from backend.services.api_service import api_app

    routes = {r.path: getattr(r, "methods", set()) for r in api_app.routes}

    # 1. Verify all 4 Sales Voice Agent routes
    assert "/api/sales/sessions" in routes, "POST /api/sales/sessions missing from api_app!"
    assert "POST" in routes["/api/sales/sessions"]

    assert "/api/sales/sessions/{session_id}/messages" in routes, "POST .../messages missing from api_app!"
    assert "POST" in routes["/api/sales/sessions/{session_id}/messages"]

    assert "/api/sales/sessions/{session_id}/history" in routes, "GET .../history missing from api_app!"
    assert "GET" in routes["/api/sales/sessions/{session_id}/history"]

    assert "/api/sales/sessions/{session_id}/lead" in routes, "GET .../lead missing from api_app!"
    assert "GET" in routes["/api/sales/sessions/{session_id}/lead"]

    # 2. Verify original Drax core routes remain intact
    assert "/status" in routes
    assert "/command" in routes
    assert "/tasks" in routes
    assert "/reminders" in routes
    assert "/alarms" in routes
    assert "/watchlist" in routes
    assert "/settings" in routes
    assert "/ws" in routes





