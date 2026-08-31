"""
test_pairing_and_remote.py — Unit and integration tests for Windows Agent pairing,
WebSocket communication, heartbeat telemetry, offline detection, and remote command execution.
"""

import asyncio
import time
from fastapi.testclient import TestClient

from cloud.main import app
from cloud.devices import device_manager, HEARTBEAT_TIMEOUT
from backend.core.app_executor import open_app, resolve_known_app
from backend.agent.planner import plan_request


client = TestClient(app)


def test_pairing_code_generation():
    code1 = device_manager.generate_pairing_code("dev_1", "Workstation 1", "token1")
    code2 = device_manager.generate_pairing_code("dev_2", "Workstation 2", "token2")
    assert code1.startswith("DRAX-")
    assert code2.startswith("DRAX-")
    assert len(code1) == 9
    assert code1 != code2


def test_pairing_expiry():
    code = device_manager.generate_pairing_code("dev_expired", "Expired PC", "token")
    device_manager.pairing_codes[code]["expires_at"] = time.time() - 10

    res = device_manager.verify_and_pair(code)
    assert res is None


def test_device_registration_and_auth():
    code = device_manager.generate_pairing_code("dev_auth_1", "Auth PC", "valid_token")
    paired = device_manager.verify_and_pair(code)
    assert paired is not None
    assert paired["device_id"] == "dev_auth_1"
    assert paired["name"] == "Auth PC"
    assert paired["token"] == "valid_token"
    assert paired["status"] == "offline"


def test_websocket_and_heartbeat():
    device_id = "test_ws_device_99"
    # Register and update heartbeat
    device_manager.devices[device_id] = {
        "device_id": device_id,
        "name": "Utkarsh-PC",
        "platform": "Windows",
        "token": "tok_99",
        "paired_at": time.time(),
        "last_seen": time.time(),
        "status": "online",
        "telemetry": {},
    }
    device_manager.update_heartbeat(device_id, {
        "cpu_percent": 14.5,
        "ram_percent": 42.0,
        "ram_used_gb": 6.8,
        "os_name": "Windows 11",
    })

    devices = device_manager.get_devices()
    target = next((d for d in devices if d["device_id"] == device_id), None)
    assert target is not None
    assert target["name"] == "Utkarsh-PC"
    assert target["telemetry"]["cpu_percent"] == 14.5


def test_remote_command_result_future():
    req_id = "test_req_abc"
    fut = device_manager.create_pending_request(req_id)
    assert not fut.done()

    device_manager.resolve_pending_request(req_id, "Opening Spotify.", success=True)
    assert fut.done()
    assert fut.result() == {"result": "Opening Spotify.", "success": True}


def test_offline_detection():
    dev_id = "test_stale_device"
    device_manager.devices[dev_id] = {
        "device_id": dev_id,
        "name": "Stale PC",
        "token": "tok",
        "last_seen": time.time() - (HEARTBEAT_TIMEOUT + 10),
        "status": "online",
    }
    devs = device_manager.get_devices()
    target = next((d for d in devs if d["device_id"] == dev_id), None)
    assert target is not None
    assert target["status"] == "offline"


def test_windows_command_routing_no_agent():
    device_manager.device_sockets.clear()

    resp = client.post("/command", json={"command": "open spotify"})
    assert resp.status_code == 200
    data = resp.json()
    assert "No Windows Agent is connected" in data["response"]
    assert data["routed_to"] is None


def test_app_resolver_aliases():
    spotify = resolve_known_app("open spotify")
    assert spotify is not None
    assert spotify[1] == "Spotify"

    chrome = resolve_known_app("launch google chrome")
    assert chrome is not None
    assert chrome[1] == "Google Chrome"

    vscode = resolve_known_app("start vs code")
    assert vscode is not None
    assert vscode[1] == "Visual Studio Code"

    calc = resolve_known_app("calc")
    assert calc is not None
    assert calc[1] == "Calculator"

    downloads = resolve_known_app("open downloads")
    assert downloads is not None
    assert downloads[0] == "shell:Downloads"


def test_command_classification():
    p_weather = plan_request("what is the weather in Delhi")
    assert all(s.tool_name in ["get_weather"] for s in p_weather.steps)

    p_stock = plan_request("what is apple stock price")
    assert all(s.tool_name in ["get_stock_price"] for s in p_stock.steps)

    p_spotify = plan_request("open spotify")
    assert any(s.tool_name in ["open_app"] for s in p_spotify.steps)

    p_chrome = plan_request("open chrome")
    assert any(s.tool_name in ["open_app"] for s in p_chrome.steps)

    p_play = plan_request("play believer on spotify")
    assert any(s.tool_name in ["play_media"] for s in p_play.steps)


def test_cors_headers_for_vercel_origin():
    """Verify CORS headers are returned for Vercel production frontend."""
    headers = {"Origin": "https://draxai-nine.vercel.app"}
    resp = client.post("/command", json={"command": "what is the weather in Delhi"}, headers=headers)
    assert resp.status_code == 200
    assert "access-control-allow-origin" in resp.headers
    assert resp.headers["access-control-allow-origin"] in ["*", "https://draxai-nine.vercel.app"]


def test_cors_preflight_options():
    """Verify OPTIONS preflight requests return 200 with allowed headers."""
    headers = {
        "Origin": "https://draxai-nine.vercel.app",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type,Accept",
    }
    resp = client.options("/command", headers=headers)
    assert resp.status_code == 200
    assert "access-control-allow-origin" in resp.headers


def test_cloud_commands_rest_response():
    """Verify cloud-only commands return formatted responses with 200 OK."""
    # Stock
    resp = client.post("/command", json={"command": "what is Nvidia stock price"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["routed_to"] == "cloud"
    assert "NVDA" in data["response"] or "USD" in data["response"]

    # Weather
    resp_w = client.post("/command", json={"command": "what is the weather in Delhi"})
    assert resp_w.status_code == 200
    data_w = resp_w.json()
    assert data_w["routed_to"] == "cloud"
    assert "Delhi" in data_w["response"]

    # News
    resp_n = client.post("/command", json={"command": "latest AI news"})
    assert resp_n.status_code == 200
    data_n = resp_n.json()
    assert data_n["routed_to"] == "cloud"
    assert "News Headlines:" in data_n["response"]
