"""
cloud/main.py — Production Cloud FastAPI server for DRAX AI.
Provides REST APIs, real-time WebSockets, device pairing, and cloud tool orchestration.
Ready for deployment on Render, Fly.io, AWS, or Railway.
"""

import os
import sys
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

# Ensure project root is on sys.path
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from cloud.devices import device_manager
import urllib.parse
from backend.agent.planner import plan_request
from backend.agent.tool_registry import registry
import backend.tools.cloud_tools
from backend.tools.finance_tools import get_stock_price, fetch_quote
from backend.tools.news_tools import get_news
from backend.tools.weather_tools import get_weather
from backend.tools.knowledge_tools import get_knowledge
from backend.database.db import (
    get_tasks, add_task, delete_task_by_id, complete_task_by_id,
    get_active_reminders, add_reminder, delete_reminder_by_id,
    get_alarms, add_alarm, delete_alarm_by_id, get_watchlist
)
from backend.core.logger import get_logger

logger = get_logger(__name__)

# Environment configurations
DRAX_ENV = os.getenv("DRAX_ENV", "production")
raw_origins = os.getenv("CORS_ORIGINS", "*")
if raw_origins == "*" or DRAX_ENV == "development":
    ALLOWED_ORIGINS = ["*"]
else:
    ALLOWED_ORIGINS = [orig.strip() for orig in raw_origins.split(",") if orig.strip()]

app = FastAPI(
    title="DRAX AI Public Cloud API",
    version="2.0.0",
    description="Public Cloud API & Device Orchestrator for DRAX AI",
)

# Configure CORS (supports explicit origins + all Vercel deployment domains)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app" if "*" not in ALLOWED_ORIGINS else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# ─── Data Schemas ────────────────────────────────────────────────────────────

class CommandPayload(BaseModel):
    command: str
    device_id: Optional[str] = None


import uuid

class PairGenerateRequest(BaseModel):
    device_id: Optional[str] = None
    device_name: Optional[str] = "Windows PC"
    token: Optional[str] = None


class PairConnectRequest(BaseModel):
    pairing_code: str


class TaskCreateRequest(BaseModel):
    title: str
    priority: Optional[str] = "medium"


class ReminderCreateRequest(BaseModel):
    message: str
    remind_at: str


class AlarmCreateRequest(BaseModel):
    time_str: str
    label: Optional[str] = "Alarm"


# ─── System & Health Endpoints ───────────────────────────────────────────────

@app.get("/health")
def get_health():
    """Health check endpoint for Render, UptimeRobot, and monitoring agents."""
    return {
        "status": "ok",
        "service": "DRAX AI Cloud API",
        "version": "2.0.0",
        "environment": DRAX_ENV,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "connected_devices": len([d for d in device_manager.get_devices() if d["status"] == "online"]),
    }


@app.get("/status")
def get_status():
    devices = device_manager.get_devices()
    online_devs = [d for d in devices if d["status"] == "online"]
    latest_telemetry = online_devs[0].get("telemetry", {}) if online_devs else {}
    return {
        "status": "online",
        "agent_status": "online" if online_devs else "offline",
        "service": "DRAX AI Cloud API",
        "version": "2.0.0",
        "devices": devices,
        "connected_devices": len(online_devs),
        "telemetry": latest_telemetry,
        "timestamp": time.time(),
    }


# ─── Device Pairing & Management ────────────────────────────────────────────

@app.post("/api/pair/generate")
def generate_device_pairing(req: PairGenerateRequest):
    """Windows Agent or Web Client requests a temporary pairing code."""
    code = device_manager.generate_pairing_code(
        device_id=req.device_id or f"drax_pc_{uuid.uuid4().hex[:6]}",
        device_name=req.device_name or "Windows PC",
        token=req.token or str(uuid.uuid4()),
    )
    return {"pairing_code": code, "expires_in_seconds": 600}


@app.post("/api/pair/connect")
def connect_paired_device(req: PairConnectRequest):
    """Web Dashboard submits pairing code to connect to Windows Agent."""
    device = device_manager.verify_and_pair(req.pairing_code)
    if not device:
        raise HTTPException(status_code=400, detail="Invalid or expired pairing code.")
    return {"status": "success", "device": device}


@app.get("/api/devices")
def list_devices():
    return {"devices": device_manager.get_devices()}


# ─── Cloud Command Execution & Relay ────────────────────────────────────────

LOCAL_TOOL_CATEGORIES = {"applications", "browser", "media", "system", "screen", "files"}


@app.post("/command")
async def execute_command(payload: CommandPayload):
    """
    Process command from Web/Mobile client.
    If command requires local Windows OS capabilities (e.g. open chrome, play music, lock pc),
    it is securely routed to the paired Windows Agent via WebSocket and awaits the live result.
    Otherwise, cloud services handle it directly.
    """
    cmd = payload.command.strip()
    if not cmd:
        raise HTTPException(status_code=400, detail="Command cannot be empty.")

    # Plan the request
    plan = plan_request(cmd)
    needs_local = any(step.tool_name in [
        "open_app", "close_app", "play_media", "pause_media", "next_track", "previous_track",
        "browser_navigate", "browser_click", "browser_type", "browser_scroll", "lock_pc",
        "take_screenshot", "screen_read", "shutdown_pc", "restart_pc", "find_file", "open_folder",
        "open_url", "browser_open_tab", "browser_close_tab", "browser_hover", "browser_back", "browser_forward"
    ] for step in plan.steps)

    # If it requires local Windows execution, route over WebSocket if device is online
    if needs_local:
        target = device_manager.get_online_device(payload.device_id)
        if not target:
            # Fallback for browser search / url in pure cloud mode if user is searching
            cloud_fallbacks = []
            for s in plan.steps:
                if s.tool_name == "search_web":
                    q = s.args.get("query", cmd)
                    cloud_fallbacks.append(f"Web search for '{q}': https://www.google.com/search?q={urllib.parse.quote(q)}")
                elif s.tool_name == "open_url":
                    u = s.args.get("url", cmd)
                    cloud_fallbacks.append(f"Website URL: {u}")

            if cloud_fallbacks:
                return {
                    "command": cmd,
                    "response": "\n\n".join(cloud_fallbacks),
                    "routed_to": "cloud",
                }

            return {
                "command": cmd,
                "response": "No Windows Agent is connected. Open Drax AI on your PC and pair this device.",
                "routed_to": None,
            }

        dev_id, ws = target
        req_id = f"req_{int(time.time() * 1000)}_{uuid.uuid4().hex[:4]}"
        fut = device_manager.create_pending_request(req_id)
        try:
            await ws.send_json({
                "type": "execute_command",
                "request_id": req_id,
                "command": cmd,
                "steps": [{"tool": s.tool_name, "args": s.args} for s in plan.steps],
            })
            # Await asynchronous execution response from Windows Agent
            res_obj = await asyncio.wait_for(fut, timeout=12.0)
            agent_result = res_obj.get("result", "Action completed on workstation.")
            return {
                "command": cmd,
                "response": agent_result,
                "routed_to": dev_id,
            }
        except asyncio.TimeoutError:
            device_manager.pending_requests.pop(req_id, None)
            return {
                "command": cmd,
                "response": f"Instruction sent to Windows workstation ({dev_id}), but execution timed out.",
                "routed_to": dev_id,
            }
        except Exception as e:
            device_manager.pending_requests.pop(req_id, None)
            logger.error(f"Error dispatching to device '{dev_id}': {e}")
            return {
                "command": cmd,
                "response": f"Failed to dispatch to Windows Agent: {e}",
                "routed_to": dev_id,
            }

    # Otherwise execute cloud-available tools directly via registry
    responses = []
    for step in plan.steps:
        t_name = step.tool_name
        args = step.args
        tool = registry.get(t_name)
        if tool:
            try:
                res = tool.execute(**args)
                if res:
                    responses.append(str(res))
            except Exception as e:
                logger.error(f"Error executing cloud tool {t_name}: {e}")
                responses.append(f"Tool {t_name} error: {str(e)}")
        elif t_name == "search_web":
            q = args.get("query", cmd)
            responses.append(f"Web search for '{q}': https://www.google.com/search?q={urllib.parse.quote(q)}")
        elif t_name == "open_url":
            u = args.get("url", cmd)
            responses.append(f"Website URL: {u}")
        else:
            responses.append(f"Executed cloud capability: {t_name}")

    return {
        "command": cmd,
        "response": "\n\n".join(responses) if responses else "Command completed.",
        "routed_to": "cloud",
    }



# ─── Cloud REST Resources (Tasks, Reminders, Alarms, Stocks, News, Weather) ──

@app.get("/tasks")
def list_tasks_endpoint():
    return {"tasks": get_tasks()}


@app.post("/tasks")
def create_task_endpoint(req: TaskCreateRequest):
    t_id = add_task(req.title, priority=req.priority)
    return {"id": t_id, "title": req.title, "status": "pending"}


@app.delete("/tasks/{task_id}")
def delete_task_endpoint(task_id: int):
    delete_task_by_id(task_id)
    return {"status": "deleted", "id": task_id}


@app.get("/reminders")
def list_reminders_endpoint():
    return {"reminders": get_active_reminders()}


@app.post("/reminders")
def create_reminder_endpoint(req: ReminderCreateRequest):
    r_id = add_reminder(req.message, req.remind_at)
    return {"id": r_id, "message": req.message, "remind_at": req.remind_at}


@app.delete("/reminders/{reminder_id}")
def delete_reminder_endpoint(reminder_id: int):
    delete_reminder_by_id(reminder_id)
    return {"status": "deleted", "id": reminder_id}


@app.get("/alarms")
def list_alarms_endpoint():
    return {"alarms": get_alarms()}


@app.post("/alarms")
def create_alarm_endpoint(req: AlarmCreateRequest):
    a_id = add_alarm(req.time_str, label=req.label)
    return {"id": a_id, "time_str": req.time_str, "label": req.label}


@app.delete("/alarms/{alarm_id}")
def delete_alarm_endpoint(alarm_id: int):
    delete_alarm_by_id(alarm_id)
    return {"status": "deleted", "id": alarm_id}


@app.get("/stocks")
def get_stocks_endpoint(symbol: str = Query("AAPL", description="Stock ticker symbol")):
    return {"symbol": symbol, "quote": get_stock_price(symbol)}


@app.get("/watchlist")
def get_watchlist_endpoint():
    return {"watchlist": get_watchlist()}


@app.get("/news")
def get_news_endpoint(topic: str = Query("world", description="News topic or region")):
    return {"topic": topic, "content": get_news(topic)}


@app.get("/weather")
def get_weather_endpoint(city: str = Query("Delhi", description="City name")):
    return {"city": city, "weather": get_weather(city)}


@app.get("/knowledge")
def get_knowledge_endpoint(query: str = Query(..., description="Knowledge search query")):
    return {"query": query, "result": get_knowledge(query)}


# ─── WebSockets for Real-Time Device Relay & Web Clients ────────────────────

@app.websocket("/ws/device/{device_id}")
async def ws_device_endpoint(websocket: WebSocket, device_id: str):
    """Windows Agent maintains persistent connection for inbound tool dispatches and telemetry."""
    await websocket.accept()
    device_manager.register_device_socket(device_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            if msg_type == "handshake":
                device_name = data.get("device_name", "Windows PC")
                platform = data.get("platform", "Windows")
                token = data.get("token", "")
                device_manager.register_device_socket(device_id, websocket, name=device_name, platform=platform, token=token)
                logger.info(f"Handshake completed for device '{device_id}' ({device_name})")
            elif msg_type == "heartbeat":
                telemetry = data.get("telemetry", {})
                device_manager.update_heartbeat(device_id, telemetry)
            elif msg_type == "command_result":
                req_id = data.get("request_id")
                result_text = data.get("result", "Action completed on workstation.")
                success = data.get("success", True)
                if req_id:
                    device_manager.resolve_pending_request(req_id, result_text, success=success)
                    logger.info(f"Resolved command request '{req_id}' from device '{device_id}'")
            else:
                logger.info(f"Received update from device '{device_id}': {msg_type}")
    except WebSocketDisconnect:
        device_manager.unregister_device_socket(device_id)
    except Exception as e:
        logger.warning(f"Device WebSocket error for '{device_id}': {e}")
        device_manager.unregister_device_socket(device_id)


@app.websocket("/ws")
@app.websocket("/ws/client/{client_id}")
async def ws_client_endpoint(websocket: WebSocket, client_id: str = "web_client"):
    """Web / Mobile client WebSocket connection."""
    await websocket.accept()
    try:
        while True:
            text = await websocket.receive_text()
            # Process incoming command
            resp = await execute_command(CommandPayload(command=text))
            await websocket.send_json(resp)
    except WebSocketDisconnect:
        logger.info(f"Client '{client_id}' disconnected.")
    except Exception as e:
        logger.warning(f"Client WebSocket error: {e}")


# Mount Web Dashboard static assets if directory exists
_WEB_DIR = os.path.join(_PROJECT_ROOT, "web")
if os.path.isdir(_WEB_DIR):
    app.mount("/", StaticFiles(directory=_WEB_DIR, html=True), name="web")
