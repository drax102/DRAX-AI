"""
backend/sales_agent/lead_scoring.py — Explainable BANT Lead Scoring Engine.
Implements a deterministic, transparent 0-100 scoring model across Budget, Authority, Need, and Timeline (each 0-25).
Provides human-readable justifications for every awarded score.
"""

import re
from typing import Optional, Dict, Any, Tuple
from backend.sales_agent.schemas import ScoreBreakdown


def evaluate_budget_score(budget_text: Optional[str]) -> Tuple[int, str]:
    """
    Score budget (0-25 points) based on explicit customer statements.
    Unknown or missing budget receives 0 points.
    """
    if not budget_text or not budget_text.strip():
        return 0, "Budget: Not yet disclosed (0/25)"

    b = budget_text.strip().lower()

    # Zero or no budget
    if any(k in b for k in ["no budget", "$0", "0$", "zero budget", "cannot pay", "free only", "no money"]):
        return 0, "Budget: Confirmed zero budget available (0/25)"

    # Look for numerical values
    numbers = re.findall(r"\$?\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*([kKmM]?)", b)
    if numbers:
        raw_num_str, unit = numbers[0]
        try:
            num = float(raw_num_str.replace(",", ""))
            if unit.lower() == "k":
                num *= 1000
            elif unit.lower() == "m":
                num *= 1000000

            if num >= 10000:
                return 25, f"Budget: Substantial verified budget ({budget_text.strip()}) (25/25)"
            elif num >= 2000:
                return 18, f"Budget: Moderate mid-tier budget ({budget_text.strip()}) (18/25)"
            elif num > 0:
                return 8, f"Budget: Limited starter budget ({budget_text.strip()}) (8/25)"
        except ValueError:
            pass

    # Keyword analysis for non-numeric answers
    if any(k in b for k in ["enterprise", "custom plan", "substantial", "well funded", "large budget", "allocated"]):
        return 25, f"Budget: Enterprise or fully allocated budget indicated ({budget_text.strip()}) (25/25)"

    if any(k in b for k in ["flexible", "medium", "negotiable", "adequate", "standard plan", "funded"]):
        return 15, f"Budget: Flexible or funded business budget ({budget_text.strip()}) (15/25)"

    if any(k in b for k in ["tight", "limited", "small", "bootstrap", "minimal", "low"]):
        return 5, f"Budget: Constrained budget indicated ({budget_text.strip()}) (5/25)"

    return 5, f"Budget: Unverified budget mention ({budget_text.strip()}) (5/25)"


def evaluate_authority_score(authority_text: Optional[str]) -> Tuple[int, str]:
    """
    Score purchasing authority (0-25 points).
    Important rule: Do NOT assume authority solely based on job title.
    Requires explicit role in purchasing / evaluation process.
    """
    if not authority_text or not authority_text.strip():
        return 0, "Authority: Decision authority not yet verified (0/25)"

    a = authority_text.strip().lower().replace("_", " ")

    # Explicitly no authority
    if any(k in a for k in ["no authority", "not my decision", "cannot approve", "student", "just looking", "no say"]):
        return 0, "Authority: Customer explicitly stated no purchasing authority (0/25)"

    # Sole or final decision maker
    if any(k in a for k in [
        "sole decision", "final decision", "i decide", "decision maker", "i make the decision",
        "buying authority", "budget owner", "sole authority", "i sign", "final sign-off"
    ]):
        return 25, f"Authority: Confirmed primary decision-maker ({authority_text.strip()}) (25/25)"

    # Co-decision maker, technical lead, or evaluation committee
    if any(k in a for k in [
        "evaluation committee", "evaluation team", "recommending", "part of decision",
        "technical evaluator", "co-decision", "with my team", "lead evaluator", "stakeholder"
    ]):
        return 18, f"Authority: Key stakeholder or evaluation team member ({authority_text.strip()}) (18/25)"

    # Influencer or team member
    if any(k in a for k in ["influencer", "team member", "developer", "engineer", "user", "internal champion"]):
        return 10, f"Authority: Internal user/influencer without sole sign-off ({authority_text.strip()}) (10/25)"

    return 5, f"Authority: Unclear decision role ({authority_text.strip()}) (5/25)"


def evaluate_need_score(need_text: Optional[str]) -> Tuple[int, str]:
    """
    Score business need / pain point (0-25 points).
    """
    if not need_text or not need_text.strip():
        return 0, "Need: Business challenge not yet identified (0/25)"

    n = need_text.strip().lower()

    # Explicit no need
    if any(k in n for k in ["no need", "don't need", "do not need", "no problem", "not looking"]):
        return 0, "Need: Customer explicitly reported no business need (0/25)"

    # High-impact critical business need
    if any(k in n for k in [
        "automate call", "inbound call", "customer support", "high volume", "scale voice",
        "save cost", "churn", "replace manual", "call qualification", "reduce wait", "sla",
        "critical", "bottleneck", "revenue"
    ]):
        return 25, f"Need: High-impact business problem identified ({need_text.strip()}) (25/25)"

    # Moderate business need
    if any(k in n for k in [
        "improve", "efficiency", "explore", "workflow", "faster", "productivity",
        "assist", "security", "automation", "automate", "system", "infrastructure"
    ]):
        return 15, f"Need: Clear operational or technical goal identified ({need_text.strip()}) (15/25)"

    # General curiosity or testing
    if any(k in n for k in ["testing", "curious", "checking out", "browsing", "experiment"]):
        return 5, f"Need: Exploratory interest or testing ({need_text.strip()}) (5/25)"

    return 10, f"Need: Basic requirement stated ({need_text.strip()}) (10/25)"


def evaluate_timeline_score(timeline_text: Optional[str]) -> Tuple[int, str]:
    """
    Score purchase timeline (0-25 points).
    """
    if not timeline_text or not timeline_text.strip():
        return 0, "Timeline: Purchase timeline not yet discussed (0/25)"

    t = timeline_text.strip().lower()

    # Urgent / Immediate (< 1 month)
    if any(k in t for k in [
        "asap", "immediate", "urgent", "this week", "next week", "this month",
        "1 month", "right now", "immediately", "upcoming days"
    ]):
        return 25, f"Timeline: Urgent launch planned ({timeline_text.strip()}) (25/25)"

    # Near-term (1 to 3 months)
    if any(k in t for k in ["1-3 month", "2 month", "3 month", "next month", "this quarter", "next quarter", "q1", "q2", "q3", "q4"]):
        return 18, f"Timeline: Active near-term timeframe ({timeline_text.strip()}) (18/25)"

    # Medium-term (3 to 6 months)
    if any(k in t for k in ["3-6 month", "4 month", "5 month", "6 month", "later this year", "half year"]):
        return 10, f"Timeline: Medium-term horizon ({timeline_text.strip()}) (10/25)"

    # Long-term (> 6 months or indefinite)
    if any(k in t for k in ["next year", "indefinite", "no rush", "> 6 month", "eventually"]):
        return 5, f"Timeline: Long-term or uncommitted timeline ({timeline_text.strip()}) (5/25)"

    return 5, f"Timeline: Timeline stated ({timeline_text.strip()}) (5/25)"


def calculate_lead_score(
    budget: Optional[str],
    authority: Optional[str],
    need: Optional[str],
    timeline: Optional[str],
) -> ScoreBreakdown:
    """
    Deterministic BANT scoring algorithm.
    Calculates 0-25 points per pillar and sums to 0-100 total.
    Returns a validated ScoreBreakdown model with human-readable reasoning.
    """
    b_score, b_reason = evaluate_budget_score(budget)
    a_score, a_reason = evaluate_authority_score(authority)
    n_score, n_reason = evaluate_need_score(need)
    t_score, t_reason = evaluate_timeline_score(timeline)

    total = b_score + a_score + n_score + t_score
    total = max(0, min(100, total))

    reasoning_lines = [b_reason, a_reason, n_reason, t_reason]
    full_reasoning = " | ".join(reasoning_lines)

    return ScoreBreakdown(
        budget_score=b_score,
        authority_score=a_score,
        need_score=n_score,
        timeline_score=t_score,
        total_score=total,
        reasoning=full_reasoning,
    )


def determine_qualification_status(score_breakdown: ScoreBreakdown, budget: Optional[str], need: Optional[str]) -> str:
    """
    Determine qualification status using transparent business rules:
    - 'disqualified': explicit zero budget or explicit 'no need'.
    - 'qualified': total score >= 60 with validated need and authority/budget.
    - 'in_progress': partial details collected, ongoing conversation.
    - 'unqualified': zero details or score is 0.
    """
    b_str = (budget or "").lower()
    n_str = (need or "").lower()

    if any(k in b_str for k in ["no budget", "$0", "cannot pay"]) or any(k in n_str for k in ["no need", "do not need"]):
        return "disqualified"

    if score_breakdown.total_score >= 60 and score_breakdown.need_score >= 15:
        if score_breakdown.budget_score >= 15 or score_breakdown.authority_score >= 18:
            return "qualified"

    if score_breakdown.total_score > 0:
        return "in_progress"

    return "unqualified"


def determine_buying_intent(
    score_breakdown: ScoreBreakdown,
    customer_statements: str = "",
    timeline: Optional[str] = None,
    budget: Optional[str] = None,
) -> str:
    """
    Classify buying intent into: 'high', 'medium', 'low', or 'unqualified'.
    Requires explicit conversational evidence, never inferred from company name alone.
    """
    text = (customer_statements or "").lower()
    t = (timeline or "").lower()
    b = (budget or "").lower()

    # Disqualification indicators
    if any(k in b for k in ["no budget", "$0", "cannot pay"]) or any(k in text for k in ["not interested", "student", "just looking", "no budget"]):
        return "low"

    # High Intent: Strong purchase triggers or urgent timeline with verified budget
    high_triggers = [
        "ready to buy", "sign contract", "send invoice", "live demo", "schedule demo",
        "proposal", "start trial", "get started", "pricing agreement", "enterprise agreement",
        "procurement", "rollout immediately"
    ]
    if any(k in text for k in high_triggers):
        return "high"

    if (score_breakdown.timeline_score >= 18 and score_breakdown.budget_score >= 18 and score_breakdown.need_score >= 15) or (score_breakdown.total_score >= 70 and score_breakdown.authority_score >= 18 and score_breakdown.budget_score >= 18):
        return "high"

    # Medium Intent: Evaluating, comparing, active timeline, or solid need
    medium_triggers = [
        "evaluating", "comparing", "considering", "exploring", "looking for",
        "interested", "test out", "team requirement"
    ]
    if any(k in text for k in medium_triggers) or score_breakdown.total_score >= 35:
        return "medium"

    # Low Intent
    if score_breakdown.total_score > 0:
        return "low"

    return "unqualified"
