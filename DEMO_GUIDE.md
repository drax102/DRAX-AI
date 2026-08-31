# DRAX AI — Company Demonstration Guide

This guide details the **12-Step Deterministic Demo Flow** to present Drax AI to stakeholders, clients, or company executives.

---

## 🎯 Executive Demo Overview

* **Format**: Hybrid Desktop + Cloud Web Assistant
* **Duration**: 3 – 5 minutes
* **Key Subsystems Demonstrated**:
  1. Offline Wake-Word Detection (*"Hey Drax"*)
  2. Windows Application Lifecycle (*Spotify, Chrome, VS Code*)
  3. Hardware Media Controls (*Play, Pause, Next, Volume*)
  4. Real-time Financial Market Quotes (*US & Indian Stocks*)
  5. Live RSS News & Weather
  6. Natural Language Reminders & SQLite Tasks
  7. Cloud Device Pairing (*Code DRAX-xxxx*)
  8. Cloud Web Dashboard $\to$ Windows PC Remote Action Dispatch

---

## 📋 Step-by-Step Live Demo Script

### Step 1: Start Drax AI
Launch Drax AI on your Windows workstation:
```powershell
.\venv\Scripts\python.exe desktop_app.py
```
*(Or launch the standalone binary: `dist\DraxAI\DraxAI.exe`)*

> **Show**: The Cybernetic holographic core avatar starts up with 60 FPS animated glow and reports telemetry.

---

### Step 2: Voice Activation
Say clearly into your microphone:
> 🗣️ **"Hey Drax"**

> **Observe**:
> - Drax responds instantly with visual state change from `IDLE` $\to$ `LISTENING` (cyan/red pulsating core).
> - System tray notification pops up: *"Listening for your command..."*.

---

### Step 3: Application Launch & Multi-Step Intent
Say:
> 🗣️ **"Open Spotify and play music"**

> **Observe**:
> - Natural language planner breaks request into 2 steps: `open_app(app_name="spotify")` then `play_media()`.
> - Spotify launches smoothly, and Windows hardware media keys trigger playback immediately.

---

### Step 4: Live Financial Quotes
Say:
> 🗣️ **"What is Nvidia stock price?"**

> **Observe**:
> - Drax queries Yahoo Finance in real-time.
> - Voice synthesizes: *"NVDA: USD 211.06 (down -1.99 / -0.93%) today."*

---

### Step 5: Real-Time News & Weather
Say:
> 🗣️ **"What is the latest AI news?"**

> **Observe**:
> - Drax fetches verified Google News RSS headlines for Artificial Intelligence and displays them in the chat terminal.

Say:
> 🗣️ **"What is the weather in Delhi?"**

> **Observe**:
> - Open-Meteo provides the current temperature, wind speed, and weather condition without requiring any API keys.

---

### Step 6: Task & Reminder Management
Say:
> 🗣️ **"Remind me to prepare the presentation at 8 PM"**

> **Observe**:
> - Reminder is parsed and saved to SQLite `data/drax.db`.
> - Drax confirms: *"Reminder set for 2026-08-31 20:00:00: prepare the presentation."*

---

### Step 7: Open the Cloud Web Dashboard
Open any web browser (on this PC, laptop, or phone) and navigate to:
```text
http://127.0.0.1:8765/
```
*(Or your public Vercel/Render URL: `https://drax-ai.vercel.app`)*

> **Show**:
> - Cybernetic dark-theme cloud dashboard.
> - Click on **Tasks & Agenda** $\to$ see all SQLite tasks.
> - Click on **Reminders & Alarms** $\to$ see the reminder created in Step 6.
> - Click on **Stocks & Markets** $\to$ see real-time quotes.

---

### Step 8: Remote Workstation Control (Web $\to$ Windows Agent)
1. On the Web Dashboard, navigate to the **My Devices** tab.
2. Verify **My Windows Workstation** displays `● Online & Listening`.
3. Click the **Open Chrome** quick button (or type `"Open Chrome"` in the web command terminal and press Execute).

> **Observe**:
> - Cloud server routes the structured tool payload over WebSocket (`/ws/device/{device_id}`).
> - The Windows PC immediately opens Google Chrome!
> - The web dashboard receives the confirmation: *"Opening Google Chrome."*

---

## 🛡️ Key Technical Takeaways to Highlight
1. **Zero Fake Features**: Every action is driven by actual OS APIs (`user32.dll`, `psutil`, `winreg`, Playwright, SQLite).
2. **Offline-First Resilience**: If cloud/internet is disconnected, local voice, apps, and media controls continue functioning 100% offline.
3. **Enterprise Security**: Disallows arbitrary shell command execution; all remote requests pass through strict tool schemas and confirmation boundaries.
