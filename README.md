# Drax AI

> An agentic, voice-controlled personal AI assistant for Windows with Cloud Remote Control, Browser Automation, and Multi-Step Execution.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Vercel-00f3ff?style=for-the-badge&logo=vercel)](https://draxai-nine.vercel.app)
[![Cloud API](https://img.shields.io/badge/Cloud%20API-Render-46E3B7?style=for-the-badge&logo=render)](https://drax-cloud-api.onrender.com)
[![Tests](https://img.shields.io/badge/Tests-52%20Passed-00ff88?style=for-the-badge&logo=pytest)](https://github.com/drax102/DRAX-AI)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)

🚀 **Live Demo:** [https://draxai-nine.vercel.app](https://draxai-nine.vercel.app)  
☁️ **Cloud API:** [https://drax-cloud-api.onrender.com](https://drax-cloud-api.onrender.com)  
💻 **GitHub Repository:** [https://github.com/drax102/DRAX-AI](https://github.com/drax102/DRAX-AI)

---

## 🎙️ Overview

**Drax AI** is an open-source, production-ready, Windows-first personal AI assistant built from the ground up for agentic computer control, offline speech recognition, multi-step planning, automated browser actions, and secure cloud connectivity.

### Key Highlights:
* 🚀 **Cloud-to-Desktop Remote Control** — Control your Windows PC from anywhere via the [Live Web Dashboard](https://draxai-nine.vercel.app) using secure WebSockets.
* 🎙️ **Natural Voice Interaction** — Hands-free microphone listening and conversational control.
* 🧠 **Intent Understanding & Planning** — Decomposes complex, multi-clause requests into ordered tool steps.
* 👂 **"Hey Drax" Wake Word** — Continuous offline Vosk Kaldi speech engine with phonetic Soundex matching.
* 🖥️ **Windows Application Control** — Deep 6-tier discovery and control across Start Menu, Registry, Program Files, LocalAppData, and UWP Store apps without AppID truncation.
* 🌐 **Playwright Browser Automation** — Navigates web pages, searches Google/YouTube/GitHub, clicks elements, types input, scrolls, hovers, and extracts page content.
* 🔎 **Web Search** — Direct search across Google, YouTube, Reddit, Wikipedia, and GitHub.
* 📈 **Live Stock Information** — Real-time quotes for US stocks, Indian stocks (NSE/BSE), indices (Nifty 50, Sensex), and cryptocurrencies.
* 📰 **Verified Live News** — Filterable RSS headlines across World, India, AI, Tech, and Business.
* 🌦️ **Global Weather Forecasts** — Live weather conditions and forecasts via Open-Meteo public API (no API keys required).
* ⏰ **Tasks & Agenda Management** — Persistent SQLite database (`data/drax.db`) for task CRUD.
* 🔔 **Natural Language Reminders** — Schedule reminders (*"remind me in 30 minutes"*, *"remind me tomorrow at 8"*) with proactive background alerting.
* ⏰ **Alarms** — Schedule and cancel alarms (*"set alarm for 7:00 PM"*).
* 🎵 **Hardware-Level Media Controls** — Windows virtual key events (`VK_MEDIA_PLAY_PAUSE`, `VK_MEDIA_NEXT_TRACK`, `VK_MEDIA_PREV_TRACK`) and Spotify automation.
* 🔊 **Asynchronous Offline TTS** — Non-blocking voice synthesis via `pyttsx3`.
* 🤖 **Multi-Step Automation** — Execute compound instructions (*"Open Spotify and play music"*, *"Search AI news and remind me to study at 8 PM"*).
* ☁️ **Cloud Connectivity & Relay** — FastAPI backend with secure WebSocket relay between cloud clients and the local Windows workstation.
* 📱 **Public Web Dashboard** — Responsive cyberpunk web client deployed on [Vercel](https://draxai-nine.vercel.app).
* 📦 **Standalone Windows Executable** — Fully bundled portable executable (`dist/DraxAI/DraxAI.exe`) with all dependencies and offline models included.

---

## 🏗️ System Architecture

```text
                  Web Dashboard (Vercel)
                             ↓  (HTTPS / REST)
              FastAPI Cloud Backend (Render)
                             ↓  (Secure WebSockets WSS)
                 Windows Drax Agent (Local PC)
                             ↓
                     Local PC Actions
     (Apps, Playwright Automation, Media Keys, OS)
```

### Complete End-to-End Pipeline:

```text
USER VOICE / TEXT (Desktop & Web Dashboard)
        ↓
DRAX VOICE / TEXT INTERFACE (Vosk Kaldi Offline / Web Speech / GUI)
        ↓
CENTRAL AGENT & CONTEXT MANAGER (Multi-turn memory & SQLite preferences)
        ↓
INTENT PARSER & MULTI-STEP PLANNER (Clause decomposition into ActionSteps)
        ↓
SECURITY & RISK GATES (Allowlist validation, confirmation boundaries)
        ↓
DISPATCH LAYER (Cloud API Tools vs WebSocket Remote Windows Agent)
        ↓
EXECUTION (Windows OS / Playwright Browser / Cloud APIs / SQLite DB)
        ↓
STRUCTURED RESPONSE (Async TTS Voice + Holographic HUD + Web Dashboard)
```

### System Components:

1. **Windows Desktop Agent (`desktop_app.py` / `dist/DraxAI/DraxAI.exe`)**:
   - Resides locally on the user's physical PC.
   - Manages audio hardware, wake-word listener, Windows application launching/closing, Playwright browser instances, local SQLite persistence, and hardware media keys.
   - Runs in the background via the Windows System Tray with single-instance mutex enforcement.
   - Operates 100% offline if internet/cloud is unavailable.

2. **Cloud Backend API (`cloud/main.py`)**:
   - Production FastAPI ASGI application deployed on [Render](https://drax-cloud-api.onrender.com) with CORS and WebSocket relay.
   - Manages device pairing codes (`DRAX-xxxx`), cloud-synced task/reminder endpoints, and public proxies for finance/news/weather.
   - Dispatches remote execution requests from web dashboards to target paired Windows agents over secure WebSockets.

3. **Web Dashboard (`web/`)**:
   - Responsive, zero-dependency static web client deployed on [Vercel](https://draxai-nine.vercel.app) styled in a futuristic cyberpunk cyan aesthetic.
   - Connects to paired Windows PCs via WebSocket/REST, enabling remote PC control (*"Open Chrome"*, *"Open Spotify"*, *"Lock Workstation"*).

---

## 💻 Tech Stack

* **Core Language**: Python 3.10+ / JavaScript (ES6+)
* **Desktop GUI**: PyQt5 (60 FPS animated cybernetic avatar HUD, system tray integration)
* **Speech Recognition**: Vosk (offline Kaldi ASR), SpeechRecognition (Google fallback)
* **Voice Synthesis (TTS)**: pyttsx3 (SAPI5 offline asynchronous engine)
* **Browser Automation**: Playwright (Chromium engine)
* **Database & Persistence**: SQLite3 (thread-safe connection pool)
* **Cloud & REST API**: FastAPI, Uvicorn, Starlette, Pydantic, WebSockets
* **System & Windows APIs**: pywin32 (`win32com`, `win32gui`, `win32con`), `ctypes.windll`, `psutil`, `winreg`
* **Packaging**: PyInstaller (custom multi-asset `.spec` bundle)
* **Testing**: Pytest, HTTPX

---

## ⚙️ Installation & Setup

### 1. Clone Repository
```bash
git clone https://github.com/drax102/DRAX-AI.git
cd DRAX-AI
```

### 2. Create Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Vosk Model Verification
Drax includes the offline `vosk-model-small-en-us-0.15` model in `models/vosk-model-small-en-us-0.15/`. If missing, download it from [alphacephei.com/vosk/models](https://alphacephei.com/vosk/models) and extract it into the `models/` directory.

---

## 🚀 Running Drax AI

### Interactive Foreground GUI:
```powershell
python desktop_app.py
```

### Silent Always-On Background Mode (System Tray):
```powershell
.\venv\Scripts\pythonw.exe desktop_app.py
```

* Say **"Hey Drax"** anytime to activate the assistant.
* Right-click the cyan system tray icon to pause listening, test microphone, view device pairing code, toggle Windows startup, or exit.

---

## 🔨 Building Portable Windows Executable

To build the standalone Windows binary (`dist/DraxAI/DraxAI.exe`):

```powershell
pyinstaller drax_ai.spec --clean --noconfirm
```

The output bundle is generated in:
```text
dist/DraxAI/
├── DraxAI.exe
└── _internal/ (models, web assets, PyQt5 DLLs, Python runtime)
```
*This executable runs on any clean Windows 10/11 system without requiring Python to be installed.*

---

## 🌐 Deployment Architecture

Drax AI utilizes a hybrid cloud-edge deployment architecture separating public web interfaces from secure local desktop automation:

| Component | Platform | URL / Location | Technology | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **Web Dashboard** | **Vercel** | [https://draxai-nine.vercel.app](https://draxai-nine.vercel.app) | Vanilla ES6+, CSS3, Cyberpunk UI | User interface accessible from any browser or mobile device for remote PC actions, chat, and telemetry. |
| **Cloud API Backend** | **Render** | [https://drax-cloud-api.onrender.com](https://drax-cloud-api.onrender.com) | FastAPI, Uvicorn, WebSockets, Python 3.10+ | Central orchestration layer handling device pairing, cloud tool execution, REST endpoints, and WebSocket message relay. |
| **Windows Desktop Agent** | **Local Windows PC** | Local Workstation (`desktop_app.py`) | PyQt5, Vosk Kaldi, Playwright, Win32 API | Background service running on the user's PC with system tray integration, wake-word listener, and local action execution. |
| **Communication Layer** | **WebSocket (WSS)** | `wss://drax-cloud-api.onrender.com/ws/device/{id}` | Secure WebSockets + REST | Asynchronous bidirectional communication channel for instant tool dispatch, execution correlation, and telemetry heartbeats. |

### How Device Pairing & Remote Execution Works:
1. **Agent Registration**: The local Windows Agent generates a secure pairing code (e.g. `DRAX-7K92`) via the Cloud API.
2. **Dashboard Connection**: The user inputs the pairing code into the [Vercel Dashboard](https://draxai-nine.vercel.app).
3. **WebSocket Relay**: The Cloud API associates the session with the persistent WebSocket connection of the Windows workstation.
4. **Command Routing**: When a command like *"Open Chrome"* or *"Play Believer on Spotify"* is submitted from any device, the Cloud routes the instruction over WebSocket to the physical PC, executes it natively, and returns the result in real time.

---

## 🧪 QA & Test Automation

Drax AI is engineered with rigorous test automation practices, deterministic unit testing, REST API validation, and end-to-end browser automation:

### 1. Automated Test Suite (Pytest)
The test suite consists of **52 automated tests** executing in CI/CD and local environments:

```bash
python -m pytest tests/ -v
```

```text
============================= test session starts =============================
platform win32 -- Python 3.13.5, pytest-9.1.1, pluggy-1.6.0
collected 52 items

tests/test_app_matching.py ..                                            [  3%]
tests/test_cloud_api.py ......                                           [ 15%]
tests/test_db_features.py ....                                           [ 23%]
tests/test_full_suite.py ............                                    [ 46%]
tests/test_intent_routing.py ...                                         [ 51%]
tests/test_pairing_and_remote.py ................                        [ 82%]
tests/test_planner.py ....                                               [ 90%]
tests/test_safety.py ..                                                  [ 94%]
tests/test_wake_word.py ...                                              [100%]

============================= 52 passed in 29.49s =============================
```

### 2. QA Automation Highlights & Capabilities:
* **Playwright Browser Automation**:
  - Full browser lifecycle management with Chromium headless/headful automation (`backend/tools/browser_tools.py`).
  - Automated web navigation, resilient DOM selector queries, element clicking, keyboard input typing, scrolling, hovering, and dynamic content scraping.
  - Exception handling and timeout recovery for flaky or slow web pages.
* **FastAPI REST API Automation (`fastapi.testclient.TestClient`)**:
  - Automated integration testing of endpoints: `GET /health`, `GET /status`, `POST /command`, `POST /api/pair/generate`, `POST /api/pair/connect`, `GET /api/devices`.
  - CORS header validation across cross-origin production requests from Vercel (`Access-Control-Allow-Origin`, preflight `OPTIONS`).
  - Negative testing for malformed requests (empty commands, invalid JSON, nonexistent pairing codes).
* **WebSocket Lifecycle & Integration Testing**:
  - Test coverage for WebSocket registration, persistent device mapping, and reconnection lifecycles.
  - Regression testing for socket replacement race conditions (`test_socket_replacement_safe_disconnect`) to ensure reconnects never orphan active sockets.
  - Heartbeat telemetry verification and timeout detection ($\le 45\text{s}$).
  - Asynchronous Future correlation testing (`create_pending_request` / `resolve_pending_request` using `request_id` and `command_id`).
* **Command Routing & Intent Classification Testing**:
  - Intent parser verification ensuring local PC tools (`open_app`, `play_media`, `lock_pc`, `take_screenshot`) correctly route to the Windows Agent.
  - Cloud tool verification ensuring external data queries (`get_weather`, `get_stock_price`, `get_news`, `search_web`) execute server-side without requiring a paired PC.
* **Security & Safety Gate Testing**:
  - Strict allowlist enforcement verifying unregistered tool names and raw shell commands are rejected before execution.
  - Confirmation gate validation for destructive system operations (`shutdown_pc`, `restart_pc`).
* **Database & Persistence Testing**:
  - SQLite transaction testing for task CRUD, reminder scheduling, and preference management with thread-safe isolation.

---

## 🎬 Demo Commands

Try speaking or typing the following commands:

* 🗣️ *"Hey Drax"*
* 🗣️ *"Open Spotify and play music"*
* 🗣️ *"What is Nvidia stock price?"*
* 🗣️ *"What is the latest AI news?"*
* 🗣️ *"What is the weather in Delhi?"*
* 🗣️ *"Remind me to prepare for my interview at 8 PM."*
* 🗣️ *"Open Chrome and search Python developer jobs."*
* 🗣️ *"Open GTA V"*
* 🗣️ *"Close Spotify"*
* 🗣️ *"What are my tasks?"*
* 🗣️ *"Set an alarm for 7:00 AM"*
* 🗣️ *"Lock workstation"*

---

## 🛡️ Security & Privacy

* **Strict Tool Allowlist**: User speech and web commands map strictly to registered tool schemas. Raw shell execution (`cmd.exe`, `PowerShell`, `os.system`) is strictly prohibited.
* **Confirmation Boundaries**: High-risk actions (`shutdown_pc`, `restart_pc`) pause execution and require explicit user confirmation.
* **Local Data Sovereignty**: Personal files, database records, and microphone audio are processed locally on the workstation.
* **Safe Error Propagation**: Detailed errors are categorized without exposing sensitive system secrets or private environment variables.

---

## 🗺️ Roadmap

- [x] Continuous offline "Hey Drax" wake-word recognition (Vosk Kaldi)
- [x] Deep 6-tier Windows application discovery & control
- [x] Native hardware-level media controls
- [x] Multi-step agentic planning & clause decomposition
- [x] SQLite-persisted tasks, reminders, and alarms
- [x] Playwright browser navigation, typing, clicking, and reading
- [x] Real-time US & Indian market financial quotes (100% free)
- [x] Verified Google News RSS feeds & Open-Meteo weather
- [x] Animated 60 FPS cybernetic avatar HUD with system tray background mode
- [x] Standalone PyInstaller portable Windows executable
- [x] Production FastAPI cloud backend with WebSocket relay & device pairing
- [x] Responsive public web dashboard
- [ ] Mobile companion app (React Native / PWA)
- [ ] Local LLM integration (Ollama / Llama-3 / Phi-3 GGUF via llama.cpp)
- [ ] Vision-language multi-modal screen comprehension

---

## ⚠️ Known Limitations

1. **Hardware Media Keys**: Media control uses standard Windows OS virtual key codes (`user32.dll keybd_event`); target media apps (Spotify, YouTube, VLC) must support standard Windows media events.
2. **Microphone Access**: If multiple audio applications lock the microphone in exclusive mode, Drax gracefully waits and automatically reconnects when the stream is freed.
3. **Playwright Automation**: Automated browser interactions run headless or headful depending on configuration; first-time Playwright usage requires `playwright install chromium`.

---

## 📸 Screenshots

*(Add your UI and Web Dashboard screenshots here)*

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
