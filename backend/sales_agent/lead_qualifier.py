"""
backend/sales_agent/lead_qualifier.py — Customer Information Extraction and Qualification Pipeline.
Extracts BANT entities, validates customer data, updates lead scores, and updates SQLite storage.
Strictly preserves previously collected information across multi-turn dialogues.
"""

import re
import json
import logging
from typing import Optional, Dict, Any, List

from backend.sales_agent.schemas import LeadRead, LeadUpdate, ScoreBreakdown
from backend.sales_agent.database import (
    get_lead_by_session,
    create_lead,
    update_lead,
    get_conversation_history,
)
from backend.sales_agent.schemas import LeadCreate
from backend.sales_agent.lead_scoring import (
    calculate_lead_score,
    determine_qualification_status,
    determine_buying_intent,
)

logger = logging.getLogger(__name__)


def extract_regex_entities(conversation_text: str) -> Dict[str, Any]:
    """
    Extract lead fields using robust regex and semantic pattern matching.
    Only extracts fields explicitly present in customer statements.
    """
    extracted: Dict[str, Any] = {}
    text = conversation_text.strip()

    # 1. Email Address
    email_match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", text)
    if email_match:
        extracted["email"] = email_match.group(0).lower()

    # 2. Phone Number
    phone_match = re.search(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", text)
    if phone_match:
        extracted["phone"] = phone_match.group(0).strip()

    # 3. Budget
    budget_match = re.search(
        r"(?:budget(?:\s+is|\s+of|\s*:)?|\$)\s*(\$?\s*\d+(?:,\d+)*(?:\.\d+)?\s*[kKmM]?(?:\s*(?:dollars|usd|\/\s*(?:month|year|yr|mo)))?)",
        text,
        re.IGNORECASE,
    )
    if budget_match:
        val = (budget_match.group(1) or budget_match.group(0)).strip()
        if not val.startswith("$") and re.match(r"^\d", val):
            val = "$" + val
        extracted["budget"] = val
    elif re.search(r"\bno\s+budget\b", text, re.IGNORECASE):
        extracted["budget"] = "No budget ($0)"
    elif re.search(r"\b(flexible\s+budget|standard\s+budget|enterprise\s+budget)\b", text, re.IGNORECASE):
        extracted["budget"] = re.search(r"\b(flexible|standard|enterprise)\s+budget\b", text, re.IGNORECASE).group(0).capitalize()

    # 4. Timeline
    timeline_match = re.search(
        r"\b(?:within\s+\d+\s+(?:days?|weeks?|months?)|asap|immediate(?:ly)?|next\s+(?:month|quarter|year|week)|this\s+(?:quarter|month|year)|q[1-4]|3-6\s+months?|1-3\s+months?|\d+\s+months?)\b",
        text,
        re.IGNORECASE,
    )
    if timeline_match:
        extracted["timeline"] = timeline_match.group(0).strip()

    # 5. Authority
    # Note: Evaluated on explicit role statements, never assumed from job title alone
    if re.search(r"\b(i\s+am\s+the\s+sole\s+decision\s+maker|i\s+make\s+the\s+decision|i\s+decide|final\s+authority|sole\s+authority|sole\s+decision)\b", text, re.IGNORECASE):
        extracted["authority"] = "sole_decision_maker"
    elif re.search(r"\b(evaluation\s+committee|part\s+of\s+(?:the\s+)?decision|evaluating\s+(?:for|with)\s+(?:the|my)\s+team|co-decision|recommending)\b", text, re.IGNORECASE):
        extracted["authority"] = "evaluation_committee"
    elif re.search(r"\b(not\s+my\s+decision|cannot\s+approve|no\s+purchasing\s+authority|no\s+authority)\b", text, re.IGNORECASE):
        extracted["authority"] = "no_authority"
    elif re.search(r"\b(i\s+am\s+(?:an?\s+)?(?:developer|engineer|end\s+user|student|intern))\b", text, re.IGNORECASE):
        extracted["authority"] = "influencer_only"

    # 6. Name
    name_match = re.search(
        r"(?:[mM]y\s+name\s+is|[iI]\s+am|[tT]his\s+is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b",
        text,
    )
    if name_match:
        extracted["name"] = name_match.group(1).strip()

    # 7. Company
    company_match = re.search(
        r"(?:at|from|company\s+is|work\s+at)\s+([A-Z][A-Za-z0-9_\s&]+(?:\s+(?:Inc|LLC|Corp|Technologies|AI|Labs|Solutions))?)\b",
        text,
    )
    if company_match:
        extracted["company"] = company_match.group(1).strip()

    # 8. Role / Job Title
    role_match = re.search(
        r"\b(?:i\s+am\s+(?:the\s+|a\s+)?|role\s+is\s+|work\s+as\s+)([A-Z][A-Za-z\s]+?(?:Director|VP|Manager|Officer|Lead|Architect|Specialist|Engineer|CTO|CEO|CFO|COO|President))\b",
        text,
        re.IGNORECASE,
    )
    if role_match:
        extracted["role"] = role_match.group(1).strip().title()

    # 9. Business Need
    need_patterns = [
        r"(?:need\s+(?:to\s+)?|looking\s+(?:to\s+|for\s+)|want\s+(?:to\s+)?|trying\s+to|challenge\s+is|interested\s+in|require\s+)\s*([^.\n]+)",
        r"(?:automate\w*\s+[^.\n]+)",
        r"(?:replace\s+manual\s+[^.\n]+)",
    ]
    for np in need_patterns:
        m = re.search(np, text, re.IGNORECASE)
        if m:
            extracted["need"] = m.group(0).strip()
            break

    # 10. Product Interest
    product_match = re.search(
        r"(?:enterprise\s+plan|pro\s+tier|voice\s+agent|inbound\s+automation|cross-device\s+assistant|api\s+access)",
        text,
        re.IGNORECASE,
    )
    if product_match:
        extracted["product_interest"] = product_match.group(0).title()

    return extracted


def merge_extracted_into_lead(existing_lead: LeadRead, new_data: Dict[str, Any]) -> LeadUpdate:
    """
    Merge newly extracted fields into an existing lead record.
    Guarantees that known information is never overwritten by None, empty strings, or less specific data.
    """
    updates: Dict[str, Any] = {}

    for field, new_val in new_data.items():
        if new_val is None:
            continue
        str_val = str(new_val).strip()
        if not str_val:
            continue

        curr_val = getattr(existing_lead, field, None)
        # If currently unknown, update
        if curr_val is None or str(curr_val).strip() == "" or curr_val == "unqualified":
            updates[field] = str_val
        # If updating with non-empty distinct content (e.g., budget refined from $5k to $20k)
        elif str_val.lower() != str(curr_val).strip().lower():
            updates[field] = str_val

    return LeadUpdate(**updates)


def qualify_lead_from_session(session_id: str, db_path: Optional[str] = None) -> Optional[LeadRead]:
    """
    Main Qualification Pipeline:
    1. Retrieves full conversation turns for the session.
    2. Extracts BANT information and contact details.
    3. Merges safely with existing lead record (preserving historical data).
    4. Computes deterministic BANT score & reasoning.
    5. Determines buying intent & qualification status.
    6. Persists updates to the isolated SQLite sales database.
    """
    existing_lead = get_lead_by_session(session_id, db_path=db_path)
    if not existing_lead:
        existing_lead = create_lead(LeadCreate(session_id=session_id), db_path=db_path)

    # 1. Fetch all customer message turns
    history = get_conversation_history(session_id, limit=50, db_path=db_path)
    user_turns = [t.content for t in history if t.role == "user"]
    combined_user_text = "\n".join(user_turns)

    # 2. Extract entities
    new_extracted = extract_regex_entities(combined_user_text)

    # 3. Merge safely without overwriting known values
    lead_update = merge_extracted_into_lead(existing_lead, new_extracted)

    # Combine updated attributes for scoring
    effective_budget = lead_update.budget or existing_lead.budget
    effective_authority = lead_update.authority or existing_lead.authority
    effective_need = lead_update.need or existing_lead.need
    effective_timeline = lead_update.timeline or existing_lead.timeline

    # 4. Compute explainable BANT score
    score_breakdown: ScoreBreakdown = calculate_lead_score(
        budget=effective_budget,
        authority=effective_authority,
        need=effective_need,
        timeline=effective_timeline,
    )

    # 5. Determine qualification status & buying intent
    qual_status = determine_qualification_status(
        score_breakdown=score_breakdown,
        budget=effective_budget,
        need=effective_need,
    )
    buying_intent = determine_buying_intent(
        score_breakdown=score_breakdown,
        customer_statements=combined_user_text,
        timeline=effective_timeline,
        budget=effective_budget,
    )

    # 6. Apply final qualification fields to update payload
    lead_update.lead_score = score_breakdown.total_score
    lead_update.score_breakdown = score_breakdown.model_dump()
    lead_update.qualification_status = qual_status
    lead_update.buying_intent = buying_intent

    # 7. Persist to database
    updated_lead = update_lead(session_id, lead_update, db_path=db_path)
    return updated_lead
