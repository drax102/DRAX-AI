# Technical Interview Preparation Guide

This guide contains concise, speakable answers designed for live technical evaluations and system design interviews. Each answer is 2–4 sentences long, grounded in the actual codebase, and easy to explain clearly to technical recruiters, engineering managers, and senior architects.

---

### 1. What problem does this project solve?
Inbound sales leads often go cold because human sales development reps (SDRs) cannot respond immediately 24/7 or qualify prospects consistently. This autonomous agent conducts real-time consultative discovery conversations over voice or text, extracts customer requirements, and scores lead readiness instantly using the BANT framework.

### 2. Why did you choose FastAPI?
FastAPI is an asynchronous Python ASGI framework that offers native asynchronous I/O, automatic Pydantic request validation, and OpenAPI documentation out of the box. Its high concurrency throughput makes it ideal for handling simultaneous real-time conversation streams with minimal latency compared to traditional WSGI frameworks like Flask or Django.

### 3. What is an LLM provider?
An LLM provider is an abstraction layer that decouples our application code from specific AI model vendors. In our project, `llm_provider.py` conforms to a unified interface so we can seamlessly switch between OpenAI, Groq, OpenRouter, local models, or our offline deterministic demo engine without changing any dialogue logic.

### 4. How does conversation memory work?
Each conversation is assigned a unique session ID, and every message turn is persisted in our SQLite database. When a new customer message arrives, the conversation orchestrator queries the last several turns from the database and passes them as conversational history to the LLM so it maintains continuous context across multi-turn exchanges.

### 5. What is BANT?
BANT is an industry-standard B2B sales qualification framework standing for Budget, Authority, Need, and Timeline. It evaluates whether a prospect has the financial resources, the decision-making power, a genuine business challenge, and a near-term implementation deadline to justify commercial engagement.

### 6. How is lead scoring calculated?
Our scoring engine awards up to 25 points to each of the four BANT pillars, summing to a total score between 0 and 100. For instance, explicit budgets over \$10k earn 25 points, verified sole decision-makers earn 25 points, high-impact automation needs earn 15–25 points, and near-term timelines earn 18–25 points, with full text justifications stored for every awarded score.

### 7. Why use deterministic scoring?
Relying on raw LLMs to calculate numerical scores can lead to hallucinated numbers, scoring drift, and unpredictable variance between similar conversations. By using deterministic code-based scoring rules driven by verified conversational extractions, we guarantee transparent, explainable, and audit-compliant scoring that sales leaders can trust.

### 8. Why SQLite?
For an isolated MVP and local evaluation, SQLite provides zero-configuration, zero-dependency relational persistence that runs completely within the Python process. We enforce thread safety using Python thread locks and WAL mode, while keeping the sales database (`sales_agent.db`) completely separated from the existing Drax assistant database (`drax.db`).

### 9. How does speech recognition work?
We use the browser's native Web Speech API (`SpeechRecognition` / `webkitSpeechRecognition`), which captures microphone audio and streams it to the browser engine's neural acoustic model. The resulting final text transcript is captured in our input box and sent to the FastAPI backend with visual pulse feedback for the user.

### 10. How does text-to-speech work?
We use the browser's native `window.speechSynthesis` API, creating a `SpeechSynthesisUtterance` for every assistant response. Before speaking, we sanitize the text to remove Markdown symbols and URLs so the synthetic voice sounds natural, and we provide immediate mute and stop controls.

### 11. How does the frontend communicate with the backend?
The frontend uses asynchronous JavaScript `fetch()` calls to send JSON payloads to our FastAPI REST endpoints. The client maintains state continuity via `sessionStorage`, ensuring that session IDs persist across page reloads without requiring complex frontend frameworks.

### 12. How would you scale to 100,000 users?
I would replace the single SQLite database with a managed PostgreSQL cluster using PgBouncer for connection pooling, and deploy multiple stateless FastAPI container instances behind an Application Load Balancer. Additionally, I would introduce Redis for session caching and rate limiting, Celery workers for background CRM sync, and streaming Server-Sent Events (SSE) for lower perceived voice latency.

### 13. What are the current limitations?
The current MVP runs locally on SQLite and operates on the offline `DemoLLMProvider`—live external LLM API endpoints have not been validated in this local environment. Additionally, while software-level Web Speech integration is tested in code, live acoustic verification with physical microphones and speakers remains pending manual user evaluation, and the 100k-user scalability architecture is a conceptual proposal rather than an empirical load test.

### 14. How would you debug an API failure?
First, I inspect the HTTP status code and response payload in the browser's DevTools Network tab. Then, I check the Uvicorn application logs to trace whether the error originated from request validation (400), an invalid session ID (404), an upstream LLM timeout (504), or a database constraint (500), using our centralized logger to identify the exact failing function.
