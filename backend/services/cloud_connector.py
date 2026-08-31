"""
cloud_connector.py — Windows Agent background service connecting local workstation to Drax Cloud.
Handles persistent WebSocket connection, automatic pairing generation, periodic heartbeat telemetry,
exponential backoff reconnection, and inbound tool execution with security allowlist enforcement.
"""

import json
import os
import sys
import threading
import time
import uuid
import requests

from backend.agent.tool_registry import registry
from backend.core.config import settings
from backend.core.logger import get_logger

logger = get_logger(__name__)

# Production default cloud backend URL
DEFAULT_CLOUD_URL = "https://drax-cloud-api.onrender.com"


class CloudConnector:
    """Maintains outbound persistent WebSocket connection to Drax Cloud and dispatches remote instructions."""

    def __init__(self):
        self.device_id = self._get_or_create_device_id()
        self.device_name = settings.get("assistant", "device_name", f"{os.getenv('COMPUTERNAME', 'Windows-PC')}")
        self.token = str(uuid.uuid4())
        self.cloud_url = os.getenv("DRAX_CLOUD_URL", settings.get("cloud", "url", DEFAULT_CLOUD_URL)).rstrip("/")
        self.pairing_code: str = f"DRAX-{self.device_id[-4:].upper()}"
        self.is_connected = False
        self.last_heartbeat_time = 0.0
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._backoff_delay = 1.0

    def _get_or_create_device_id(self) -> str:
        dev_id = settings.get("cloud", "device_id")
        if not dev_id:
            # Generate deterministic or persistent ID
            comp_name = os.getenv("COMPUTERNAME", "PC").lower().replace(" ", "_")
            dev_id = f"drax_{comp_name}_{uuid.uuid4().hex[:6]}"
            try:
                settings.set("cloud", "device_id", dev_id)
                settings.save()
            except Exception:
                pass
        return dev_id

    def request_pairing_code(self) -> str:
        """Fetch a validated pairing code from the Cloud API."""
        try:
            resp = requests.post(
                f"{self.cloud_url}/api/pair/generate",
                json={
                    "device_id": self.device_id,
                    "device_name": self.device_name,
                    "token": self.token,
                },
                timeout=6,
            )
            if resp.status_code == 200:
                data = resp.json()
                self.pairing_code = data.get("pairing_code", self.pairing_code)
                logger.info(f"Obtained Cloud pairing code: {self.pairing_code}")
                return self.pairing_code
        except Exception as e:
            logger.debug(f"Cloud pairing code fetch fallback (offline/retry): {e}")

        return self.pairing_code

    def start(self):
        """Start the background connector thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name="DraxCloudConnector", daemon=True)
        self._thread.start()

    def stop(self):
        """Gracefully stop the background connector."""
        self._stop_event.set()

    def _run_loop(self):
        """Persistent connection watchdog with exponential backoff."""
        self.request_pairing_code()
        self._backoff_delay = 1.0

        while not self._stop_event.is_set():
            try:
                self._connect_and_listen()
                # If connection closed normally, reset backoff
                self._backoff_delay = 1.0
            except Exception as e:
                self.is_connected = False
                logger.info(f"Cloud connection interrupted: {e}. Reconnecting in {self._backoff_delay:.1f}s...")
                
                # Sleep with interrupt check
                sleep_ticks = int(self._backoff_delay * 10)
                for _ in range(sleep_ticks):
                    if self._stop_event.is_set():
                        break
                    time.sleep(0.1)

                # Exponential backoff: 1s -> 2s -> 4s -> 8s -> 16s -> 32s -> max 60s
                self._backoff_delay = min(self._backoff_delay * 2.0, 60.0)

    def _connect_and_listen(self):
        """Connect to Cloud WebSocket and process incoming dispatches."""
        import websockets.sync.client as ws_client
        ws_url = self.cloud_url.replace("https://", "wss://").replace("http://", "ws://")
        endpoint = f"{ws_url}/ws/device/{self.device_id}"

        logger.info(f"Connecting to Drax Cloud endpoint: {endpoint}")
        with ws_client.connect(endpoint, open_timeout=8) as ws:
            self.is_connected = True
            self._backoff_delay = 1.0
            logger.info(f"[ONLINE] Workstation successfully connected to DRAX Cloud ({self.device_id})")

            # Send online handshake
            handshake_payload = {
                "type": "handshake",
                "device_id": self.device_id,
                "device_name": self.device_name,
                "platform": "Windows",
                "token": self.token,
                "status": "online",
            }
            ws.send(json.dumps(handshake_payload))
            self._send_heartbeat(ws)

            last_hb = time.time()

            while not self._stop_event.is_set():
                # Send periodic heartbeat every 20 seconds
                now = time.time()
                if (now - last_hb) >= 20.0:
                    self._send_heartbeat(ws)
                    last_hb = now

                try:
                    msg_raw = ws.recv(timeout=1.0)
                except TimeoutError:
                    continue
                except Exception:
                    break

                if not msg_raw:
                    continue

                try:
                    payload = json.loads(msg_raw)
                    msg_type = payload.get("type")

                    if msg_type == "execute_command":
                        self._handle_execute_command(ws, payload)
                    elif msg_type == "ping":
                        ws.send(json.dumps({"type": "pong", "device_id": self.device_id}))
                except Exception as ex:
                    logger.error(f"Error processing inbound cloud message: {ex}")

        self.is_connected = False

    def _send_heartbeat(self, ws):
        """Send telemetry heartbeat to Cloud."""
        try:
            from backend.core.system_info import get_system_telemetry
            telemetry = get_system_telemetry()
        except Exception:
            telemetry = {"os_name": "Windows", "cpu_percent": 0, "ram_percent": 0}

        try:
            ws.send(json.dumps({
                "type": "heartbeat",
                "device_id": self.device_id,
                "timestamp": time.time(),
                "telemetry": telemetry,
            }))
            self.last_heartbeat_time = time.time()
        except Exception as e:
            logger.debug(f"Failed to send heartbeat: {e}")

    def _handle_execute_command(self, ws, payload: dict):
        """Execute cloud-dispatched instruction on local Windows workstation."""
        req_id = payload.get("request_id") or payload.get("command_id")
        steps = payload.get("steps", [])
        command_text = payload.get("command", "")
        results = []
        success = True

        logger.info(f"Received remote execution dispatch [{req_id}]: '{command_text}' ({len(steps)} steps)")

        for s in steps:
            tool_name = s.get("tool")
            tool_args = s.get("args", {})

            # Strict Security Allowlist: Check registered tool
            tool = registry.get(tool_name)
            if not tool:
                msg = f"Rejected unrecognized or unauthorized tool: '{tool_name}'"
                logger.warning(msg)
                results.append(msg)
                success = False
                continue

            try:
                logger.info(f"Executing tool '{tool_name}' with args: {tool_args}")
                res = tool.execute(**tool_args)
                if res:
                    results.append(str(res))
            except Exception as ex:
                err_msg = f"Error executing '{tool_name}': {ex}"
                logger.error(err_msg)
                results.append(err_msg)
                success = False

        combined_result = "\n\n".join(results) if results else f"Executed '{command_text}' on workstation."

        # Send execution response back to Cloud
        try:
            ws.send(json.dumps({
                "type": "command_result",
                "request_id": req_id,
                "command_id": req_id,
                "success": success,
                "result": combined_result,
                "response": combined_result,
            }))
            logger.info(f"Dispatched execution result for [{req_id}] back to Cloud.")
        except Exception as e:
            logger.error(f"Failed to send command result back to Cloud: {e}")


cloud_connector = CloudConnector()

