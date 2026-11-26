"""
tests/test_e2e_verification.py — End-to-end verification of the Autonomous AI Sales Voice Agent.
Tests the complete multi-turn consultative dialogue lifecycle, session continuity, BANT lead qualification,
session isolation, history retrieval, error contracts, and XSS safety.
"""

import re
import pytest
from fastapi.testclient import TestClient

from backend.services.api_service import api_app
from backend.sales_agent.database import init_sales_db


@pytest.fixture
def e2e_client(tmp_path):
    """Provide a TestClient connected to an isolated test database."""
    test_db_path = str(tmp_path / "e2e_sales.db")
    init_sales_db(test_db_path)
    client = TestClient(api_app)
    return client


def test_complete_e2e_sales_lifecycle(e2e_client):
    """
    Simulates a full user journey through the Sales Voice Agent:
    1. Initialize session A.
    2. Check CSPRNG session ID format.
    3. Send greeting + customer identity + business challenge.
    4. Verify assistant reply, model attribution, and incremental lead extraction.
    5. Send budget, timeline, and decision-making authority.
    6. Verify live BANT score progression (85/100, qualified, high intent).
    7. Retrieve conversation history and verify turn count & ordering.
    8. Start a new session B and verify total isolation from session A.
    9. Test XSS safety and invalid input handling.
    """
    # ── 1. Create Session A ──────────────────────────────────────────────────
    res_init = e2e_client.post("/api/sales/sessions")
    assert res_init.status_code == 201, f"Failed session init: {res_init.text}"
    session_a = res_init.json()["session_id"]

    # Verify session ID format and entropy
    assert session_a.startswith("sales_")
    assert len(session_a) == 38  # sales_ (6) + 32 hex chars (128 bits)
    assert re.match(r"^sales_[0-9a-f]{32}$", session_a)

    # ── 2. Check initial clean lead state ────────────────────────────────────
    lead_init = e2e_client.get(f"/api/sales/sessions/{session_a}/lead").json()
    assert lead_init["lead_score"] == 0
    assert lead_init["qualification_status"] == "in_progress"
    assert lead_init["buying_intent"] == "unqualified"
    assert lead_init["name"] is None
    assert lead_init["company"] is None

    # ── 3. Send Turn 1: Identity and Business Need ──────────────────────────
    turn1_text = "Hello, my name is Bruce Wayne from Wayne Enterprises. We need automated security systems for our facility."
    res_turn1 = e2e_client.post(
        f"/api/sales/sessions/{session_a}/messages",
        json={"message": turn1_text},
    )
    assert res_turn1.status_code == 200, f"Turn 1 failed: {res_turn1.text}"
    data_turn1 = res_turn1.json()

    assert data_turn1["session_id"] == session_a
    assert len(data_turn1["response"]) > 10
    assert data_turn1["is_demo"] is True
    assert data_turn1["model_used"] == "demo-sales-engine"
    assert data_turn1["history_length"] == 2  # 1 user + 1 assistant

    # Verify Lead Details after Turn 1
    lead_turn1 = e2e_client.get(f"/api/sales/sessions/{session_a}/lead").json()
    assert lead_turn1["name"] == "Bruce Wayne"
    assert lead_turn1["company"] == "Wayne Enterprises"
    assert "security" in lead_turn1["need"].lower()
    assert lead_turn1["lead_score"] > 0
    assert lead_turn1["score_breakdown"]["need_score"] >= 10

    # ── 4. Send Turn 2: Budget, Timeline, and Authority ─────────────────────
    turn2_text = "We have a budget of $150,000 and need deployment next quarter. I am the sole decision maker."
    res_turn2 = e2e_client.post(
        f"/api/sales/sessions/{session_a}/messages",
        json={"message": turn2_text},
    )
    assert res_turn2.status_code == 200, f"Turn 2 failed: {res_turn2.text}"
    data_turn2 = res_turn2.json()

    assert data_turn2["history_length"] == 4  # 2 user + 2 assistant
    assert data_turn2["lead_score"] >= 75
    assert data_turn2["qualification_status"] == "qualified"
    assert data_turn2["buying_intent"] == "high"

    # Verify Complete BANT Breakdown after Turn 2
    lead_turn2 = e2e_client.get(f"/api/sales/sessions/{session_a}/lead").json()
    breakdown = lead_turn2["score_breakdown"]
    assert breakdown["budget_score"] >= 20
    assert breakdown["authority_score"] == 25
    assert breakdown["need_score"] >= 15
    assert breakdown["timeline_score"] >= 15
    assert lead_turn2["lead_score"] == breakdown["total_score"]
    assert lead_turn2["budget"] == "$150,000"
    assert lead_turn2["timeline"] == "next quarter"
    assert lead_turn2["authority"] == "sole_decision_maker"
    assert len(breakdown["reasoning"]) > 10

    # ── 5. Retrieve History for Session A ────────────────────────────────────
    res_hist = e2e_client.get(f"/api/sales/sessions/{session_a}/history")
    assert res_hist.status_code == 200
    hist_data = res_hist.json()
    assert hist_data["total_turns"] == 4
    assert hist_data["turns"][0]["role"] == "user"
    assert "Bruce Wayne" in hist_data["turns"][0]["content"]
    assert hist_data["turns"][1]["role"] == "assistant"
    assert hist_data["turns"][2]["role"] == "user"
    assert "$150,000" in hist_data["turns"][2]["content"]
    assert hist_data["turns"][3]["role"] == "assistant"

    # ── 6. Create New Session B and Verify Isolation ─────────────────────────
    res_init_b = e2e_client.post("/api/sales/sessions")
    assert res_init_b.status_code == 201
    session_b = res_init_b.json()["session_id"]
    assert session_b != session_a

    # Session B must be completely empty and reset
    lead_b = e2e_client.get(f"/api/sales/sessions/{session_b}/lead").json()
    assert lead_b["lead_score"] == 0
    assert lead_b["name"] is None
    assert lead_b["company"] is None

    hist_b = e2e_client.get(f"/api/sales/sessions/{session_b}/history").json()
    assert hist_b["total_turns"] == 0
    assert hist_b["turns"] == []

    # Session A must remain completely unaffected
    lead_a_after = e2e_client.get(f"/api/sales/sessions/{session_a}/lead").json()
    assert lead_a_after["lead_score"] == lead_turn2["lead_score"]
    assert lead_a_after["name"] == "Bruce Wayne"

    # ── 7. Security: XSS Safety ──────────────────────────────────────────────
    xss_payload = "<script>alert('pwned');</script><img src='x' onerror='steal()'>"
    res_xss = e2e_client.post(
        f"/api/sales/sessions/{session_b}/messages",
        json={"message": f"Testing input: {xss_payload}"},
    )
    assert res_xss.status_code == 200
    # Text is stored as raw string data and returned safely in JSON
    hist_b_after = e2e_client.get(f"/api/sales/sessions/{session_b}/history").json()
    assert xss_payload in hist_b_after["turns"][0]["content"]

    # ── 8. Error Contract Verification ───────────────────────────────────────
    # Blank whitespace message
    res_blank = e2e_client.post(
        f"/api/sales/sessions/{session_b}/messages",
        json={"message": "   "},
    )
    assert res_blank.status_code == 400
    assert "blank" in res_blank.json()["detail"].lower()

    # Non-existent session
    res_404 = e2e_client.post(
        "/api/sales/sessions/sales_nonexistent0000000000000000/messages",
        json={"message": "Hello"},
    )
    assert res_404.status_code == 404
