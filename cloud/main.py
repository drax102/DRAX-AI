"""
cloud/main.py — Production Cloud FastAPI server for DRAX AI.
Provides REST APIs, real-time WebSockets, device pairing, and cloud tool orchestration.
Ready for deployment on Render, Fly.io, AWS, or Railway.
"""

import os
import sys
import time
import asyncio
import uuid
import urllib.parse
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

# Ensure project root is on sys.path
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from cloud.devices import device_manager
from backend.agent.capability_router import capability_router
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
raw_origins = os.getenv("CORS_ORIGINS", "*").strip("\"'")
if not raw_origins or raw_origins == "*":
    ALLOWED_ORIGINS = ["*"]
else:
    ALLOWED_ORIGINS = [orig.strip().strip("\"'") for orig in raw_origins.split(",") if orig.strip()]

# Ensure known production Vercel domains are always present
VERCEL_DOMAINS = [
    "https://draxai-nine.vercel.app",
    "https://draxai-git-main-utkarsh48lpu-7905s-projects.vercel.app",
]
if "*" not in ALLOWED_ORIGINS:
    for vd in VERCEL_DOMAINS:
        if vd not in ALLOWED_ORIGINS:
            ALLOWED_ORIGINS.append(vd)

app = FastAPI(
    title="DRAX AI Public Cloud API",
    version="2.0.0",
    description="Public Cloud API & Device Orchestrator for DRAX AI",
)

# Configure CORS for all web clients (Vercel, custom domains, localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if "*" not in ALLOWED_ORIGINS else ["*"],
    allow_origin_regex=r"^https?://.*" if "*" in ALLOWED_ORIGINS else r"https://.*\.vercel\.app.*|http://localhost:\d+|http://127\.0\.0\.1:\d+",
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global unhandled exception on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "layer": "CLOUD",
                "message": "DRAX Cloud API encountered an error processing your request.",
                "details": str(exc),
            },
        },
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
    online_devs = [d for d in devices if d.get("status") == "online" or d.get("online") is True]
    latest_telemetry = online_devs[0].get("telemetry", {}) if online_devs else {}
    first_online_name = online_devs[0].get("name", "Windows PC") if online_devs else None
    first_online_id = online_devs[0].get("device_id") if online_devs else None

    return {
        "status": "online",
        "agent_status": "online" if online_devs else "offline",
        "service": "DRAX AI Cloud API",
        "version": "2.0.0",
        "devices": devices,
        "connected_devices": len(online_devs),
        "online_device_name": first_online_name,
        "online_device_id": first_online_id,
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
    """Web Dashboard submits pairing code to connect to Windows Agent or mobile device."""
    device = device_manager.verify_and_pair(req.pairing_code)
    if not device:
        raise HTTPException(status_code=400, detail="Invalid or expired pairing code.")
    return {"status": "success", "device": device}


@app.get("/api/devices")
def list_devices():
    return {"devices": device_manager.get_devices()}


@app.post("/api/devices/{device_id}/primary")
def set_primary_device_endpoint(device_id: str):
    """Set specified device as primary device."""
    ok = device_manager.set_primary_device(device_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Device not found.")
    return {"status": "success", "device_id": device_id, "is_primary": True}


# ─── Cloud Command Execution & Universal Capability Relay ────────────────────

@app.post("/command")
async def execute_command(payload: CommandPayload):
    """
    Universal multi-device command router.
    Routes intents based on required capabilities to matching online devices (Windows, Android, etc.)
    or executes cloud intelligence skills server-side.
    """
    cmd = payload.command.strip()
    if not cmd:
        raise HTTPException(status_code=400, detail="Command cannot be empty.")

    req_id = f"cmd_{int(time.time() * 1000)}_{uuid.uuid4().hex[:4]}"
    ts_now = datetime.now(timezone.utc).isoformat()

    # 1. Plan the request into ActionSteps
    plan = plan_request(cmd)
    primary_intent = plan.steps[0].tool_name if plan.steps else "unknown"

    # 2. Check if any step requires device capabilities
    device_steps = []
    cloud_steps = []

    for step in plan.steps:
        decision = capability_router.route_step(step.tool_name, preferred_device_id=payload.device_id)
        if decision.is_cloud:
            cloud_steps.append((step, decision))
        else:
            device_steps.append((step, decision))

    # 3. Route Device Capabilities
    if device_steps:
        # Check first device requirement
        first_step, first_decision = device_steps[0]

        if not first_decision.is_available:
            # Fallback for browser search / URL query in pure cloud mode if user is searching
            if first_step.tool_name in ["search_web", "open_url"]:
                q = first_step.args.get("query", first_step.args.get("url", cmd))
                res_url = f"Web search for '{q}': https://www.google.com/search?q={urllib.parse.quote(q)}"
                return {
                    "command_id": req_id,
                    "status": "success",
                    "intent": first_step.tool_name,
                    "device_id": None,
                    "result": res_url,
                    "timestamp": ts_now,
                    "success": True,
                    "command": cmd,
                    "response": res_url,
                    "routed_to": "cloud",
                    "error": None,
                }

            unsupported_msg = first_decision.unsupported_message or "No connected device is currently available for this action."
            err_code = "AGENT_OFFLINE" if first_decision.required_capability in ["apps", "media", "system", "volume", "screen", "files", "browser", "telemetry"] else "CAPABILITY_UNAVAILABLE"
            err_layer = "WINDOWS AGENT" if err_code == "AGENT_OFFLINE" else "DEVICE_ROUTER"
            return {
                "command_id": req_id,
                "status": "failed",
                "intent": first_step.tool_name,
                "device_id": None,
                "result": unsupported_msg,
                "timestamp": ts_now,
                "success": False,
                "command": cmd,
                "response": unsupported_msg,
                "routed_to": None,
                "error": {
                    "code": err_code,
                    "layer": err_layer,
                    "message": unsupported_msg,
                    "details": f"Required capability: '{first_decision.required_capability}'. Connect a compatible device.",
                },
            }

        dev_id = first_decision.device_id
        ws = first_decision.websocket
        fut = device_manager.create_pending_request(req_id)
        logger.info(f"CAPABILITY ROUTING: command_id={req_id} cap={first_decision.required_capability} target={dev_id} cmd='{cmd}'")

        try:
            await ws.send_json({
                "type": "execute_command",
                "request_id": req_id,
                "command_id": req_id,
                "command": cmd,
                "steps": [{"tool": s.tool_name, "args": s.args} for s in plan.steps],
            })
            # Await asynchronous execution response from device with sensible 4s relay window
            try:
                res_obj = await asyncio.wait_for(fut, timeout=4.0)
                agent_result = res_obj.get("result") or res_obj.get("response", f"Executed '{cmd}' on device.")
                agent_success = res_obj.get("success", True)
                agent_error = res_obj.get("error")

                return {
                    "command_id": req_id,
                    "status": "success" if agent_success else "failed",
                    "intent": primary_intent,
                    "device_id": dev_id,
                    "result": agent_result,
                    "timestamp": ts_now,
                    "success": agent_success,
                    "command": cmd,
                    "response": agent_result,
                    "routed_to": dev_id,
                    "error": agent_error,
                }
            except asyncio.TimeoutError:
                # Fast asynchronous acknowledgement: Action has been dispatched and is executing
                logger.info(f"RELAY ACKNOWLEDGED: command_id={req_id} device={dev_id} dispatched and executing.")
                ack_msg = f"Dispatched '{cmd}' to device ({dev_id}). Action is executing."
                return {
                    "command_id": req_id,
                    "status": "executing",
                    "intent": primary_intent,
                    "device_id": dev_id,
                    "result": ack_msg,
                    "timestamp": ts_now,
                    "success": True,
                    "command": cmd,
                    "response": ack_msg,
                    "routed_to": dev_id,
                    "error": None,
                }
        except Exception as e:
            device_manager.pending_requests.pop(req_id, None)
            logger.error(f"Error dispatching to device '{dev_id}': {e}")
            err_msg = f"Failed to dispatch to device: {str(e)}"
            return {
                "command_id": req_id,
                "status": "failed",
                "intent": primary_intent,
                "device_id": dev_id,
                "result": err_msg,
                "timestamp": ts_now,
                "success": False,
                "command": cmd,
                "response": err_msg,
                "routed_to": dev_id,
                "error": {
                    "code": "DISPATCH_FAILED",
                    "layer": "CLOUD",
                    "message": err_msg,
                    "details": "WebSocket connection failure during dispatch.",
                },
            }

    # 4. Otherwise execute cloud-available tools directly via registry
    responses = []
    has_error = False
    cloud_error = None
    logger.info(f"COMMAND ROUTING: route=cloud cmd='{cmd}'")

    for step, decision in cloud_steps:
        t_name = step.tool_name
        args = step.args
        tool = registry.get(t_name)
        if tool:
            try:
                res = tool.execute(**args)
                if res:
                    res_str = str(res)
                    responses.append(res_str)
                    if "Sorry" in res_str or "unavailable" in res_str.lower() or "not find" in res_str.lower() or "error" in res_str.lower():
                        has_error = True
                        cloud_error = {
                            "code": "CLOUD_TOOL_ERROR",
                            "layer": "CLOUD",
                            "message": res_str,
                            "details": f"Cloud tool '{t_name}' returned error response.",
                        }
            except Exception as e:
                logger.error(f"Error executing cloud tool {t_name}: {e}")
                err_msg = f"Tool {t_name} error: {str(e)}"
                responses.append(err_msg)
                has_error = True
                cloud_error = {
                    "code": "CLOUD_EXCEPTION",
                    "layer": "CLOUD",
                    "message": err_msg,
                    "details": f"Exception raised while executing '{t_name}'.",
                }
        elif t_name == "search_web":
            q = args.get("query", cmd)
            responses.append(f"Web search for '{q}': https://www.google.com/search?q={urllib.parse.quote(q)}")
        elif t_name == "open_url":
            u = args.get("url", cmd)
            responses.append(f"Website URL: {u}")
        else:
            responses.append(f"Executed cloud capability: {t_name}")

    final_text = "\n\n".join(responses) if responses else "Command completed."
    return {
        "command_id": req_id,
        "status": "success" if not has_error else "failed",
        "intent": primary_intent,
        "device_id": None,
        "result": final_text,
        "timestamp": ts_now,
        "success": not has_error,
        "command": cmd,
        "response": final_text,
        "routed_to": "cloud",
        "error": cloud_error,
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
                platform = data.get("platform", "windows")
                os_ver = data.get("os_version", "Windows 11")
                agent_ver = data.get("agent_version", "2.0.0")
                caps = data.get("capabilities")
                token = data.get("token", "")
                device_manager.register_device_socket(
                    device_id,
                    websocket,
                    name=device_name,
                    platform=platform,
                    os_version=os_ver,
                    agent_version=agent_ver,
                    capabilities=caps,
                    token=token,
                )
                logger.info(f"Handshake completed for device '{device_id}' ({device_name} - {platform}) with caps: {caps}")
            elif msg_type == "heartbeat":
                telemetry = data.get("telemetry", {})
                device_manager.update_heartbeat(device_id, telemetry)
            elif msg_type == "command_result":
                req_id = data.get("request_id") or data.get("command_id")
                result_text = data.get("result") or data.get("response", "Action completed on workstation.")
                success = data.get("success", True)
                if req_id:
                    device_manager.resolve_pending_request(req_id, result_text, success=success)
                    logger.info(f"Resolved command request '{req_id}' from device '{device_id}'")
            else:
                logger.info(f"Received update from device '{device_id}': {msg_type}")
    except WebSocketDisconnect:
        device_manager.unregister_device_socket(device_id, websocket=websocket)
    except Exception as e:
        logger.warning(f"Device WebSocket error for '{device_id}': {e}")
        device_manager.unregister_device_socket(device_id, websocket=websocket)


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
