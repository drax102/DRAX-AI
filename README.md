# Drax AI

> An agentic, voice-controlled personal AI assistant for Windows.

---

## 🎙️ Overview

Drax AI is an open-source, production-ready, Windows-first personal AI assistant built from the ground up for agentic computer control, offline speech recognition, and cloud connectivity.

### Key Highlights:
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
* 📱 **Public Web Dashboard** — Responsive cyberpunk web client deployable on Vercel/Cloudflare Pages.
* 📦 **Standalone Windows Executable** — Fully bundled portable executable (`dist/DraxAI/DraxAI.exe`) with all dependencies and offline models included.

---

## 🏗️ Architecture

```text
USER VOICE / TEXT (Desktop & Web)
        ↓
DRAX VOICE / TEXT INTERFACE (Vosk Kaldi Offline / Web Speech / GUI)
        ↓
CENTRAL AGENT & CONTEXT MANAGER (Multi-turn memory & SQLite preferences)
        ↓
INTENT PARSER & MULTI-STEP PLANNER (Clause decomposition into ActionSteps)
        ↓
TOOL REGISTRY (50 discrete tools, parameter schemas, risk gates)
        ↓
WINDOWS OS / PLAYWRIGHT BROWSER / CLOUD APIs / SQLITE DATABASE
        ↓
MULTI-MODAL RESPONSE (Async TTS Voice + Holographic HUD + Web Dashboard)
```

### System Components:

1. **Windows Agent (`desktop_app.py` / `dist/DraxAI/DraxAI.exe`)**:
   - Resides locally on the user's PC.
   - Manages audio hardware, wake-word listener, Windows application launching/closing, Playwright browser instances, local SQLite persistence, and hardware media keys.
   - Runs in the background via the Windows System Tray with single-instance mutex enforcement.
   - Operates 100% offline if internet/cloud is unavailable.

2. **Cloud Backend (`cloud/main.py`)**:
   - Production FastAPI ASGI application with CORS and WebSocket relay.
   - Manages device pairing codes (`DRAX-xxxx`), cloud-synced task/reminder endpoints, and public proxies for finance/news/weather.
   - Dispatches remote execution requests from web dashboards to target paired Windows agents over secure WebSockets.

3. **Web Dashboard (`web/`)**:
   - Responsive, zero-dependency static web client styled in a futuristic cyberpunk cyan aesthetic.
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

## ☁️ Cloud & Web Deployment

### 1. Cloud Backend (Render Deployment)
1. Fork or push this repository to GitHub.
2. In the [Render Dashboard](https://dashboard.render.com), create a **New +** $\to$ **Blueprint** service.
3. Select this repository. Render will automatically read `render.yaml` and configure:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn cloud.main:app --host 0.0.0.0 --port $PORT`
4. The service will be live at `https://<service-name>.onrender.com`.

### 2. Web Dashboard (Vercel Deployment)
1. In the [Vercel Dashboard](https://vercel.com), import this repository.
2. Root Directory: `./` (Vercel automatically detects `vercel.json` and routes to `web/`).
3. Set Environment Variable: `VITE_API_URL=https://<your-render-service>.onrender.com`.
4. Deploy.

### 3. Device Pairing
1. On your Windows PC, right-click the Drax tray icon and click **🔗 Show Device Pairing Code** $\to$ you will receive a code (e.g. `DRAX-7K92`).
2. On your Web Dashboard, click **Pair PC**, enter `DRAX-7K92`, and connect.
3. You can now execute remote instructions from the web dashboard directly on your physical PC!

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
* **Local Data Sovereignty**: Personal files, database records, and microphone audio are processed locally and never uploaded to public clouds without explicit intent.
* **No Secrets in Source**: All deployment configurations use environment variables (`.env.example`).

---

## 🧪 Testing

Run the complete automated test suite (36 tests covering wake word, app matching, multi-step planner, SQLite persistence, cloud API, and confirmation gates):

```bash
python -m pytest tests/
```

```text
============================= 36 passed in 15.34s =============================
```

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
