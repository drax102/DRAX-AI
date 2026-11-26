# Live Demonstration Guide & Script (3–5 Minutes)

This step-by-step guide is designed for presenting the **Autonomous AI Sales Voice Agent** during a live technical hiring evaluation or stakeholder review.

---

## 1. Demo Scenario Overview

**Prospect Profile (Demonstration Persona)**:
- **Name**: Alex Mercer
- **Role**: VP of Operations
- **Company**: Apex Logistics
- **Business Need**: Inbound call automation for delivery tracking and driver dispatch
- **Budget**: \$45,000 annually
- **Timeline**: Next quarter (within 3 months)
- **Authority**: Primary decision-maker evaluating alongside the CTO

---

## 2. Step-by-Step Demonstration Script

### Step 1: Start the Application (30 seconds)
Open your terminal in the project directory (`d:\PROJECTS\drax-ai-v2`) and run:

```bash
.\venv\Scripts\python -m uvicorn backend.services.api_service:api_app --host 127.0.0.1 --port 8765
```

**What to say**:
> *"Here, I am starting our FastAPI server on port 8765. Notice that it serves our static web dashboard and mounts our dedicated Autonomous Sales Agent router at `/api/sales` with isolated SQLite database storage."*

---

### Step 2: Open the Dashboard and Navigate to Sales Tab (30 seconds)
Open Google Chrome and navigate to:
`http://localhost:8765`

Click the **"Sales Voice Agent"** button in the left sidebar navigation.

**What to show**:
- Point out the **split-panel architecture**: the left column is the real-time dialogue terminal, and the right column is the live Lead Intelligence panel with BANT meters and customer profile table.
- Highlight the **session indicator badge**: it displays an unpredictable 128-bit CSPRNG session ID (`sales_[0-9a-f]{32}`).
- Point out the engine badge: it displays `DEMO ENGINE`, confirming that our deterministic zero-cost offline engine is active.

---

### Step 3: Initiate Customer Conversation & Voice Input (60 seconds)
Click the **Microphone** button (or paste the prompt below into the input bar):

```text
Hello, my name is Alex Mercer from Apex Logistics. We are looking to automate our inbound customer support and driver dispatch calls.
```

Press **Send** (or pause to let the speech recognition auto-submit).

**What happens**:
1. The user bubble appears on the terminal.
2. The agent responds consultatively:
   *"Hello! I am DRAX AI's Sales Assistant. We help teams automate business workflows and voice operations. What specific challenge or product capability are you looking to explore?"*
3. The browser speaks the response aloud using Web Speech TTS.
4. **On the Lead Intelligence Panel**:
   - Customer Name updates to **Alex Mercer**.
   - Company updates to **Apex Logistics**.
   - Business Need updates to the captured automation requirement.
   - The Need progress bar fills to **15 / 25**.
   - Overall Lead Score increases to **15 / 100** (`in_progress`).

---

### Step 4: Supply Commercial BANT Parameters (60 seconds)
In the input box (or via microphone), enter:

```text
We have an allocated budget of $45,000 for next quarter. As VP of Operations, I am the primary decision maker evaluating this with our CTO.
```

Click **Send**.

**What happens**:
1. The agent acknowledges the commercial scope and proposes scheduling a technical demonstration.
2. **On the Lead Intelligence Panel**:
   - Budget Details updates to **$45,000** (Budget bar leaps to **25 / 25**).
   - Timeline Details updates to **next quarter** (Timeline bar leaps to **18 / 25**).
   - Authority updates to **sole_decision_maker / evaluation team** (Authority bar leaps to **25 / 25**).
   - **Total Lead Score leaps to 83 / 100**.
   - Status badge transitions to bright green: **QUALIFIED**.
   - Buying Intent updates to **HIGH**.
   - The radial score ring glows green.

**What to say**:
> *"Notice how the scoring engine updated in real time. Unlike black-box AI scores, every single point is backed by our deterministic scoring rubric. Notice the 'Score Explanation' box at the bottom, which provides an exact, human-readable justification for why each pillar received its points."*

---

### Step 5: Demonstrate Voice Controls & Session Persistence (45 seconds)
1. **Audio Interrupt**: While the assistant is speaking, click the **Stop** button ($\blacksquare$) to show instant audio interruption.
2. **Mute Toggle**: Click **"Voice On"** to toggle voice playback to **"Voice Off"**.
3. **Session Continuity**: Refresh the browser page ($F5$).
   - Switch back to the **Sales Voice Agent** tab.
   - Point out that the conversation history, turns counter, lead score (83/100), and customer profile were completely restored from `sessionStorage` and SQLite.
4. **New Consultation**: Click **"New Session"** ($\mathbf{+}$) to demonstrate resetting to a clean state for the next prospective caller.

---

### Step 6: Conclude & Explain Architecture (30 seconds)
**What to say**:
> *"In summary, this autonomous agent achieves complete end-to-end qualification without human SDR bottlenecks. It features dual-modality voice and text, 100% database isolation from the core Drax assistant, explainable BANT evaluation, and a pluggable architecture ready for live OpenAI, Groq, or local vLLM models."*

---

## 3. Demonstration Data Reference Sheet

Use these sample phrases if asked to demonstrate edge cases during the interview:

| Scenario | Input Text | Expected System Behavior |
| :--- | :--- | :--- |
| **High-Value Enterprise Lead** | *"I am Sarah Connor, CTO at Cyberdyne. We have a $100,000 budget for next month and I make the final purchasing decision."* | Score: **86–93 / 100**; Status: `QUALIFIED`; Intent: `HIGH`. |
| **Disqualified / No Budget** | *"I am a college student testing this for a class project. I have zero budget and no company."* | Score: **0 / 100**; Status: `DISQUALIFIED`; Intent: `LOW`. |
| **XSS Security Check** | `Testing script: <script>alert('hack')</script><img src=x onerror=alert(1)>` | Renders verbatim as plain text; zero script execution; turn recorded safely in SQLite. |
