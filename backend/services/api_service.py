"""
api_service.py — Local & Cloud REST API server for DRAX AI (FastAPI & Uvicorn).
Provides REST endpoints, WebSockets, and hosts the standalone Drax Web Dashboard.
"""

import os
import sys
import threading
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.agent.agent import process_user_request
from backend.core.assistant import assistant
from backend.core.config import settings
from backend.core.system_info import get_system_telemetry
from backend.database.db import get_tasks, get_active_reminders, get_alarms, get_watchlist
from backend.core.logger import get_logger

logger = get_logger(__name__)

api_app = FastAPI(title="DRAX AI Cloud & Local Agent API", version="2.0.0")

# Enable CORS for web and cross-device clients
api_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CommandRequest(BaseModel):
    command: str


@api_app.get("/status")
def get_status():
    return {
        "assistant_name": settings.get("assistant", "name", "Drax"),
        "state": assistant.state.value,
        "telemetry": get_system_telemetry(),
        "version": "2.0.0",
    }


@api_app.post("/command")
def execute_command_endpoint(req: CommandRequest):
    response = process_user_request(req.command)
    return {"command": req.command, "response": response}


@api_app.get("/tasks")
def list_tasks_endpoint():
    return {"tasks": get_tasks()}


@api_app.get("/reminders")
def list_reminders_endpoint():
    return {"reminders": get_active_reminders()}


@api_app.get("/alarms")
def list_alarms_endpoint():
    return {"alarms": get_alarms()}


@api_app.get("/watchlist")
def list_watchlist_endpoint():
    return {"watchlist": get_watchlist()}


@api_app.get("/settings")
def get_settings_endpoint():
    return settings.get("assistant")


@api_app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Bi-directional WebSocket for real-time chat & telemetry."""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            response = process_user_request(data)
            await websocket.send_json({
                "type": "response",
                "command": data,
                "response": response,
                "state": assistant.state.value,
            })
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected.")
    except Exception as e:
        logger.warning(f"WebSocket error: {e}")


# Mount Web Dashboard static directory if it exists
_WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "web")
if os.path.isdir(_WEB_DIR):
    api_app.mount("/", StaticFiles(directory=_WEB_DIR, html=True), name="web")


def run_api_server(host: str = "127.0.0.1", port: int = 8765):
    """Run the API server in a background daemon thread."""
    try:
        import uvicorn
        config = uvicorn.Config(api_app, host=host, port=port, log_level="warning")
        server = uvicorn.Server(config)
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        logger.info(f"DRAX Cloud API & Web Dashboard running at http://{host}:{port}/")
    except Exception as e:
        logger.warning(f"Could not start local API server: {e}")
