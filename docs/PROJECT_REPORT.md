# Project Report: Autonomous AI Sales Voice Agent

**Project Title:** DRAX AI — Autonomous AI Sales Voice Agent Extension  
**Candidate / Developer:** AI Engineering Candidate  
**Date:** November 2026  
**Status:** MVP Implemented, Tested, and Verified (137/137 Tests Passed)  

---

## 1. Executive Summary & Problem Statement

Modern B2B enterprises face substantial pipeline inefficiency in top-of-funnel inbound sales:
1. **Slow Lead Response Times**: Inbound prospects waiting hours or days for SDR follow-up experience an $8\times$ drop in qualification conversion rates.
2. **Subjective & Inconsistent Qualification**: Human sales representatives evaluate Budget, Authority, Need, and Timeline (BANT) inconsistently across conversations.
3. **High Operational Costs**: Staffing round-the-clock SDR coverage for global prospects is cost-prohibitive.

**The Solution:** An autonomous, voice-capable AI Sales Agent integrated into the DRAX AI platform that conducts real-time consultative discovery conversations, automatically extracts lead parameters, scores readiness using a transparent 0–100 BANT rubric, and persists structured intelligence for enterprise sales teams.

---

## 2. Key Capabilities & Implemented Features

- **Dual-Modality Interface**: Full conversational interaction via browser-native voice (Speech-to-Text and Text-to-Speech) or keyboard text.
- **Consultative Discovery Agent**: Dialogue orchestrator that asks clarifying questions sequentially rather than interrogating the prospect with an inflexible script.
- **Explainable BANT Scoring Engine**: Deterministic 0–100 rubric evaluating Budget (25), Authority (25), Need (25), and Timeline (25) with human-readable rationales.
- **Non-Destructive Entity Extraction**: Captures names, companies, emails, phone numbers, budgets, and deadlines, strictly preserving historical context across multi-turn exchanges.
- **Isolated Storage Architecture**: Dedicated SQLite database (`data/sales_agent.db`) preventing any cross-contamination with existing Drax assistant records.
- **Deterministic Offline Fallback**: Active `DemoLLMProvider` ensures full functional demonstration without external API credit consumption or network latency risks.

---

## 3. Technology Stack

- **Backend**: Python 3.10+, FastAPI (ASGI framework), Pydantic v2 (type validation), SQLite 3 (isolated relational storage), HTTPX (asynchronous HTTP client).
- **Frontend**: Vanilla ES6+ JavaScript, CSS3 Grid/Flexbox (cyberpunk theme), HTML5 Semantic markup.
- **Browser Voice APIs**: Web Speech API (`SpeechRecognition` / `webkitSpeechRecognition` for STT; `window.speechSynthesis` for TTS).
- **Testing**: Pytest with `TestClient` (137 automated unit and end-to-end lifecycle tests).

---

## 4. System Architecture & End-to-End Workflow

```text
Prospect (Voice/Text)
       ↓
Browser Web Speech UI (Transcription & Input Sanitization)
       ↓
FastAPI Router (/api/sales/sessions/{id}/messages)
       ↓
Conversation Orchestrator (Multi-turn History from data/sales_agent.db)
       ↓
Pluggable LLM Provider (Demo Engine or OpenAI-compatible Cloud API)
       ↓
Lead Qualifier & BANT Scorer (0-100 Points + Text Justification)
       ↓
Isolated SQLite Persistence (sales_leads & sales_conversation_turns)
       ↓
Browser Terminal & Intelligence Card (Live Score & Voice Playback)
```

**Demonstrated Business Workflow**:
1. Prospect initiates a session and states commercial requirements (*"My name is Bruce Wayne from Wayne Enterprises. We need security AI with a $150,000 budget next quarter. I am the sole decision maker."*).
2. The agent responds consultatively, acknowledging the budget and asking targeted operational follow-ups.
3. The lead card immediately reflects: Name: *Bruce Wayne*, Company: *Wayne Enterprises*, Budget: *$150,000*, Authority: *Sole Decision Maker*, Lead Score: **83/100 (Qualified, High Intent)**.

---

## 5. Verification & Testing Summary

- **Total Test Suite**: **137/137 tests passing (100%)** in 61.53 seconds.
- **Coverage**: Includes isolated schema validation, SQLite CRUD, multi-turn memory continuity, regex entity extraction boundaries, BANT scoring rubrics, XSS payload neutralization, CSPRNG session entropy, and existing Drax regression safety.
- **Active Engine Disclosure**: The system currently runs locally using `DemoLLMProvider` (`demo-sales-engine`). While the `OpenAICompatibleProvider` is implemented and unit-tested via mock fixtures, live external LLM API connectivity has NOT been validated against external paid endpoints in this environment.
- **Hardware Testing Status**: Software-level Web Speech STT and TTS integrations are implemented and tested in code; live acoustic verification with physical microphones and speakers remains pending manual user evaluation.

---

## 6. MVP Scope vs. Proposed Production Improvements

1. **Active MVP Implementation**:
   - Single-instance FastAPI backend running on `localhost:8765`.
   - Local relational persistence via isolated SQLite database (`data/sales_agent.db`).
   - Browser-native Web Speech API for zero-cost client-side voice transcription and synthesis.
   - 128-bit CSPRNG session token management (`sales_[0-9a-f]{32}`).
2. **Proposed Production Roadmap (Conceptual Architecture)**:
   - Transition from SQLite to managed PostgreSQL with PgBouncer connection pooling (proposal for 100k user scale; not an empirically load-tested MVP benchmark).
   - Redis cluster for token bucket rate limiting and session caching.
   - Enterprise OAuth2 / JWT bearer authentication and role-based access control.

---

## 7. Conclusion

The DRAX Autonomous AI Sales Voice Agent successfully proves that consultative discovery, transparent lead qualification, and real-time voice interaction can be implemented cleanly inside an existing enterprise codebase without breaking legacy functionality. It delivers an immediate, functional MVP ready for technical evaluation and production scaling.
