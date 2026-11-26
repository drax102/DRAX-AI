# System Architecture: Autonomous AI Sales Voice Agent

This document details the architectural design, component interactions, data flows, and security boundaries of the **Autonomous AI Sales Voice Agent** extension within the **DRAX AI** ecosystem.

---

## 1. High-Level Architecture Diagram

```mermaid
flowchart TD
    subgraph ClientLayer["Frontend Client (Browser)"]
        UI["Web Dashboard UI\n(Split-View Terminal & Intelligence Panel)"]
        STT["Web Speech Recognition API\n(Microphone Input / STT)"]
        TTS["Web Speech Synthesis API\n(Audio Output / TTS)"]
        SessionStore["sessionStorage\n(Client-side Session Continuity)"]
    end

    subgraph APILayer["FastAPI REST & WebSocket Layer"]
        Router["Sales Router (/api/sales)\n(Prefix: /api/sales)"]
        Guard["Input Validation & Security\n(Pydantic Models + CSPRNG Token)"]
    end

    subgraph AgentCore["Autonomous Sales Agent Core"]
        Orchestrator["Conversation Orchestrator\n(backend/sales_agent/conversation.py)"]
        LLM["Pluggable LLM Provider\n(backend/sales_agent/llm_provider.py)"]
        Qualifier["Lead Qualifier Pipeline\n(backend/sales_agent/lead_qualifier.py)"]
        Scorer["Explainable BANT Scoring Engine\n(backend/sales_agent/lead_scoring.py)"]
    end

    subgraph LLMBackends["LLM Execution Engines"]
        DemoEngine["Deterministic Demo Engine\n(Offline, Zero-Cost Fallback)"]
        CloudLLM["OpenAI-Compatible Cloud LLM\n(OpenAI, Groq, OpenRouter, vLLM)"]
    end

    subgraph StorageLayer["Data Persistence Layer"]
        SalesDB[("Isolated Sales SQLite DB\ndata/sales_agent.db\n(Leads & Turn History)")]
        DraxDB[("Drax Core SQLite DB\ndata/drax.db\n(Tasks, Alarms, Telemetry)")]
    end

    %% Interactions
    UI -->|1. Voice Audio| STT
    STT -->|2. Transcribed Text| UI
    UI -->|3. POST /api/sales/sessions/{id}/messages| Router
    SessionStore <-->|Maintain Session ID| UI

    Router --> Guard
    Guard --> Orchestrator
    Orchestrator -->|Multi-Turn History| SalesDB
    Orchestrator -->|Generate Dialogue| LLM
    LLM --> DemoEngine
    LLM -.-> CloudLLM

    Orchestrator -->|Customer Statements| Qualifier
    Qualifier -->|Extracted Entities| Scorer
    Scorer -->|0-100 Score & Reasoning| Qualifier
    Qualifier -->|Save Lead Profile| SalesDB

    Orchestrator -->|4. Structured JSON Response| Router
    Router -->|5. HTTP 200 JSON| UI
    UI -->|6. Speak Response| TTS
    UI -->|7. Update Live Score & BANT Bars| UI

    %% Strict Isolation
    SalesDB -.->|Strictly Decoupled - No Foreign Keys| DraxDB
```

---

## 2. Component Breakdown

### A. Frontend Layer (`web/`)
1. **Dialogue Terminal (`#sales-chat-messages`)**:
   - Renders chronological conversation bubbles (`msg user`, `msg drax`, `msg system`).
   - Uses `textContent` rendering to ensure complete immunity against Cross-Site Scripting (XSS).
2. **Live Lead Intelligence Panel (`#tab-sales .sales-lead-panel`)**:
   - Radial score badge displaying total BANT qualification score (0–100).
   - 4 animated progress bars displaying individual pillar scores (Budget, Authority, Need, Timeline; max 25 points each).
   - Customer profile table (Name, Company, Email, Phone, Role, Business Need, Budget, Timeline).
   - Explainable reasoning card explaining why points were awarded or withheld.
3. **Speech-to-Text (STT) (`setupSalesSpeechRecognition`)**:
   - Software integration implemented using browser-native `window.SpeechRecognition || window.webkitSpeechRecognition`.
   - Provides live visual pulse feedback (`.mic-active`) when active and a `speechSubmitted` concurrency latch.
   - *Hardware Evaluation Note*: Code-level integration is verified; live acoustic testing with physical microphones and speakers across diverse hardware environments remains marked as pending manual user evaluation.
4. **Text-to-Speech (TTS) (`speakSalesUtterance`)**:
   - Leverages `window.speechSynthesis` with `SpeechSynthesisUtterance`.
   - Cleans Markdown formatting (`*`, `#`, code blocks) prior to speaking for natural cadence.
   - Includes mute toggle (`#sales-voice-toggle-btn`) and instant cancellation (`#sales-stop-speech-btn`).

---

### B. REST API Layer (`backend/sales_agent/router.py`)
Mounted onto FastAPI at prefix `/api/sales`:
- `POST /api/sales/sessions`: Initializes a new conversation session with 128 bits of CSPRNG entropy (`sales_[0-9a-f]{32}`).
- `POST /api/sales/sessions/{session_id}/messages`: Accepts customer voice transcript or text, invokes orchestrator, returns AI response with live score.
- `GET /api/sales/sessions/{session_id}/history`: Returns complete ordered turn history for the session.
- `GET /api/sales/sessions/{session_id}/lead`: Returns latest customer qualification fields, buying intent, status, and BANT breakdown.

---

### C. Agent Core & Scoring Engine
1. **Conversation Orchestrator (`conversation.py`)**:
   - Enforces consultative sales persona: guides discovery, asks one clarifying question at a time, and avoids aggressive pushiness.
   - Loads last $N$ turns from SQLite to maintain multi-turn context.
2. **Pluggable LLM Provider (`llm_provider.py`)**:
   - Conforms to abstract `BaseLLMProvider`.
   - `DemoLLMProvider` *(Currently Active)*: Deterministic, zero-cost offline engine producing realistic consultative responses without requiring external API keys.
   - `OpenAICompatibleProvider` *(Pluggable Integration)*: Standard completions client tested via mock fixtures; live external paid endpoints have not been validated in this local environment.
3. **Lead Qualifier Pipeline (`lead_qualifier.py`)**:
   - Analyzes conversational utterances to extract contact info, budget figures, timeframes, authority signals, and business needs.
   - Non-destructive merging: previously collected customer details are strictly preserved and never overwritten by subsequent ambiguous turns.
4. **Explainable BANT Scoring Engine (`lead_scoring.py`)**:
   - Evaluates each pillar out of 25 points using a transparent rubric:
     - **Budget (0–25)**: Explicit numeric amounts ($\ge \$10\text{k} \to 25$, $\$2\text{k}\text{--}\$10\text{k} \to 18$, starter $\to 8$, zero budget $\to 0$).
     - **Authority (0–25)**: Sole decision maker $\to 25$, evaluation committee / co-decision $\to 18$, influencer $\to 10$, no authority $\to 0$. Job title alone is never assumed to be decision authority.
     - **Need (0–25)**: High-impact automation/call center pain point $\to 25$, operational/efficiency/security goal $\to 15$, general curiosity $\to 10$, no need $\to 0$.
     - **Timeline (0–25)**: Urgent / $< 1$ month $\to 25$, near-term / 1–3 months / next quarter $\to 18$, medium-term / 3–6 months $\to 10$, indefinite $\to 5$, unmentioned $\to 0$.
   - Generates deterministic, human-readable justification strings stored alongside numerical scores.

---

### D. Storage Isolation
- **Sales Database (`data/sales_agent.db`)**:
  - `sales_leads`: Lead attributes, BANT breakdown JSON, qualification status, buying intent.
  - `sales_conversation_turns`: Chronological dialogue history with foreign key cascade to `sales_leads`.
- **Drax Core Database (`data/drax.db`)**:
  - Completely separate SQLite database storing PC telemetry, desktop tasks, reminders, and alarms.
  - Zero cross-database foreign keys, zero schema dependencies.

---

## 3. End-to-End Data Flow

```text
[User Speaks / Types]
       │
       ▼
[Browser STT captures text -> calls POST /api/sales/sessions/{session_id}/messages]
       │
       ▼
[FastAPI Router validates payload via Pydantic -> loads lead record]
       │
       ▼
[Orchestrator loads recent turn history from data/sales_agent.db]
       │
       ▼
[LLM Provider generates consultative dialogue response (Demo or Real LLM)]
       │
       ▼
[Lead Qualifier scans customer utterances -> extracts BANT entities]
       │
       ▼
[Scoring Engine computes Budget, Authority, Need, and Timeline points (0-100 total)]
       │
       ▼
[Database persists assistant turn and updates lead record in data/sales_agent.db]
       │
       ▼
[Router responds with HTTP 200 JSON payload containing response and score]
       │
       ▼
[Web UI updates chat bubble, refreshes BANT meters, and speaks response via TTS]
```

---

## 4. Architectural Boundaries: Drax Core vs. Sales Voice Agent

| Architectural Aspect | Existing DRAX AI Core | Autonomous Sales Voice Agent |
| :--- | :--- | :--- |
| **Primary Scope** | Personal desktop assistant & PC automation | Inbound commercial consultative sales & qualification |
| **Storage Target** | `data/drax.db` | `data/sales_agent.db` |
| **Execution Trigger** | Vosk Kaldi offline wake word or Cloud remote relay | Web browser microphone or keyboard text input |
| **Target Actions** | Launch apps, control media, lock PC, weather/news | Multi-turn discovery dialogue, lead scoring, CRM extraction |
| **Device Dependency** | Requires active Windows PC agent for desktop actions | 100% standalone cloud/browser execution |
| **API Namespace** | `/status`, `/command`, `/tasks`, `/watchlist` | `/api/sales/...` |
