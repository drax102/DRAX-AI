"""
cloud_connector.py — Windows Agent background service connecting local workstation to Drax Cloud.
Handles WebSocket connection, device pairing generation, inbound tool execution, and offline fallback.
"""

import asyncio
import json
import os
import threading
import time
import uuid
import requests

from backend.agent.tool_registry import registry
from backend.core.config import settings
from backend.core.logger import get_logger

logger = get_logger(__name__)


class CloudConnector:
    """Maintains outbound connection to Drax Cloud and dispatches remote instructions."""

    def __init__(self):
        self.device_id = self._get_or_create_device_id()
        self.device_name = settings.get("assistant", "device_name", "Windows PC")
        self.token = str(uuid.uuid4())
        self.cloud_url = settings.get("cloud", "url", "http://127.0.0.1:8765")
        self.pairing_code: str = "DRAX-INIT"
        self.is_connected = False
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def _get_or_create_device_id(self) -> str:
        dev_id = settings.get("cloud", "device_id")
        if not dev_id:
            dev_id = f"drax_pc_{uuid.uuid4().hex[:8]}"
        return dev_id

    def request_pairing_code(self) -> str:
        """Fetch a pairing code from the Cloud API."""
        try:
            resp = requests.post(
                f"{self.cloud_url}/api/pair/generate",
                json={
                    "device_id": self.device_id,
                    "device_name": self.device_name,
                    "token": self.token,
                },
                timeout=4,
            )
            if resp.status_code == 200:
                data = resp.json()
                self.pairing_code = data.get("pairing_code", "DRAX-LOCAL")
                logger.info(f"Obtained Cloud pairing code: {self.pairing_code}")
                return self.pairing_code
        except Exception as e:
            logger.debug(f"Cloud pairing code fetch fallback (offline): {e}")
        self.pairing_code = f"DRAX-{self.device_id[-4:].upper()}"
        return self.pairing_code

    def start(self):
        """Start the background connector thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()

    def _run_loop(self):
        """Persistent connection watchdog."""
        self.request_pairing_code()
        while not self._stop_event.is_set():
            try:
                self._connect_and_listen()
            except Exception as e:
                self.is_connected = False
                logger.debug(f"Cloud connection retry in 5s: {e}")
            time.sleep(5)

    def _connect_and_listen(self):
        import websockets.sync.client as ws_client
        ws_url = self.cloud_url.replace("http://", "ws://").replace("https://", "wss://")
        endpoint = f"{ws_url}/ws/device/{self.device_id}"

        with ws_client.connect(endpoint, open_timeout=5) as ws:
            self.is_connected = True
            logger.info(f"🟢 Connected to DRAX Cloud ({endpoint})")

            # Send online handshake
            ws.send(json.dumps({
                "type": "handshake",
                "device_id": self.device_id,
                "device_name": self.device_name,
                "status": "online",
            }))

            while not self._stop_event.is_set():
                msg_raw = ws.recv(timeout=1.0)
                if not msg_raw:
                    continue

                payload = json.loads(msg_raw)
                msg_type = payload.get("type")

                if msg_type == "execute_command":
                    steps = payload.get("steps", [])
                    results = []
                    for s in steps:
                        tool_name = s.get("tool")
                        tool_args = s.get("args", {})

                        # Strict Security Allowlist Validation
                        tool = registry.get(tool_name)
                        if not tool:
                            results.append(f"Rejected unknown tool: {tool_name}")
                            continue

                        try:
                            logger.info(f"Executing cloud-dispatched tool: {tool_name} with {tool_args}")
                            res = tool.execute(**tool_args)
                            results.append(str(res))
                        except Exception as ex:
                            results.append(f"Error executing {tool_name}: {ex}")

                    # Respond back to cloud
                    ws.send(json.dumps({
                        "type": "command_result",
                        "request_id": payload.get("request_id"),
                        "result": "\n".join(results),
                    }))


cloud_connector = CloudConnector()
