"""
test_production_audit.py — Comprehensive end-to-end production audit tests for DRAX AI.
Validates:
1. CORS configuration and OPTIONS preflights
2. Cloud API endpoints (GET /, /health, /status, /devices, /watchlist, /knowledge, /tasks, /reminders, /alarms)
3. Unified command response contract for local, cloud, and offline execution
4. Asynchronous command dispatch and polling contract (GET /commands/{command_id})
5. Cloud tools (Weather, Stocks, News, Knowledge, Tasks, Reminders)
6. Capability routing and security allowlist
"""

import pytest
from fastapi.testclient import TestClient
from cloud.main import app
from backend.devices.registry import device_registry
from cloud.devices import device_manager


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


# ─── 1. CORS Preflight Audit ──────────────────────────────────────────────────

def test_cors_options_preflight(client):
    """Verify OPTIONS /command returns 200 OK and appropriate CORS headers for Vercel origin."""
    response = client.options(
        "/command",
        headers={
            "Origin": "https://draxai-nine.vercel.app",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,accept",
        },
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers


def test_cors_get_devices_headers(client):
    """Verify GET /devices returns valid CORS response headers."""
    response = client.get(
        "/devices",
        headers={"Origin": "https://draxai-nine.vercel.app"},
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers


# ─── 2. Cloud API Endpoints Audit ─────────────────────────────────────────────

def test_endpoint_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "DRAX AI Cloud API"


def test_endpoint_status(client):
    response = client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "devices" in data
    assert "connected_devices" in data


def test_endpoint_devices(client):
    response = client.get("/devices")
    assert response.status_code == 200
    assert "devices" in response.json()


def test_endpoint_watchlist(client):
    response = client.get("/watchlist")
    assert response.status_code == 200
    assert "watchlist" in response.json()


def test_endpoint_knowledge(client):
    response = client.get("/knowledge?query=Python")
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    assert "Python" in data["result"] or len(data["result"]) > 0


def test_endpoint_tasks_lifecycle(client):
    # 1. Create task
    create_res = client.post("/tasks", json={"title": "Audit automated test suite", "priority": "high"})
    assert create_res.status_code == 200
    task_id = create_res.json()["id"]

    # 2. List tasks
    list_res = client.get("/tasks")
    assert list_res.status_code == 200
    task_ids = [t["id"] for t in list_res.json().get("tasks", [])]
    assert task_id in task_ids

    # 3. Delete task
    del_res = client.delete(f"/tasks/{task_id}")
    assert del_res.status_code == 200


# ─── 3. Command Response Contract Audit (Offline Agent) ───────────────────────

def test_command_contract_offline_agent(client):
    """When no agent is online, /command must return the exact offline contract."""
    # Ensure offline state for test device
    device_registry.unregister_socket("test_offline_dev")

    response = client.post("/command", json={"command": "Open Chrome"})
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is False
    assert data["status"] == "failed"
    assert "request_id" in data
    assert "command_id" in data
    assert "message" in data
    assert "offline" in data["message"].lower() or "windows agent is offline" in data["message"].lower()
    assert data["source"] == "windows_agent"
    assert data["error"] is not None
    assert data["error"]["code"] == "AGENT_OFFLINE"
    assert data["error"]["layer"] == "WINDOWS AGENT"


# ─── 4. Cloud Command Execution Contract Audit ────────────────────────────────

def test_command_contract_weather(client):
    """Weather queries must execute server-side and return the unified contract."""
    response = client.post("/command", json={"command": "what is the weather in Delhi"})
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["status"] == "success"
    assert data["source"] == "cloud"
    assert "request_id" in data
    assert "command_id" in data
    assert "Delhi" in data["message"] or "weather" in data["message"].lower() or "temperature" in data["message"].lower()


def test_command_contract_stock(client):
    """Stock queries must execute server-side and return the unified contract."""
    response = client.post("/command", json={"command": "what is Nvidia stock price"})
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["status"] == "success"
    assert data["source"] == "cloud"
    assert "NVDA" in data["message"] or "Nvidia" in data["message"] or "stock" in data["message"].lower()


def test_command_contract_news(client):
    """News queries must execute server-side and return the unified contract."""
    response = client.post("/command", json={"command": "latest AI news"})
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["status"] == "success"
    assert data["source"] == "cloud"
    assert "news" in data["message"].lower() or "headlines" in data["message"].lower() or len(data["message"]) > 0


def test_command_contract_task_creation(client):
    """Task addition via natural language /command."""
    response = client.post("/command", json={"command": "add a task to study physics"})
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["status"] == "success"
    assert data["source"] == "cloud"
    assert "study physics" in data["message"].lower() or "added task" in data["message"].lower() or "created" in data["message"].lower()


# ─── 5. Command Status Polling Endpoint (GET /commands/{command_id}) ──────────

def test_command_polling_endpoint(client):
    """Verify that any dispatched command can be polled via GET /commands/{command_id}."""
    # Execute a command first
    cmd_res = client.post("/command", json={"command": "what is Python"})
    assert cmd_res.status_code == 200
    cmd_data = cmd_res.json()
    cmd_id = cmd_data["command_id"]

    # Poll command status
    poll_res = client.get(f"/commands/{cmd_id}")
    assert poll_res.status_code == 200
    poll_data = poll_res.json()

    assert poll_data["command_id"] == cmd_id
    assert poll_data["request_id"] == cmd_id
    assert poll_data["success"] is True
    assert poll_data["status"] == "success"
    assert "message" in poll_data
    assert "result" in poll_data
    assert "source" in poll_data


def test_command_polling_nonexistent(client):
    """Polling a non-existent command ID returns 404."""
    response = client.get("/commands/nonexistent_cmd_id_12345")
    assert response.status_code == 404


# ─── 6. Application & Search Planning Audit ──────────────────────────────────

def test_google_search_planning():
    """Verify search Google for instagram.in plans search_web correctly."""
    from backend.agent.planner import plan_request
    plan = plan_request("search Google for instagram.in")
    assert not plan.is_empty
    assert plan.steps[0].tool_name == "search_web"
    assert plan.steps[0].args["query"] == "instagram.in"
    assert plan.steps[0].args["engine"] == "google"


def test_whatsapp_and_gta_planning():
    """Verify open WhatsApp and open GTA V plan open_app correctly."""
    from backend.agent.planner import plan_request
    plan_wa = plan_request("open WhatsApp")
    assert not plan_wa.is_empty
    assert plan_wa.steps[0].tool_name == "open_app"
    assert "whatsapp" in plan_wa.steps[0].args["app_name"].lower()

    plan_gta = plan_request("open GTA V")
    assert not plan_gta.is_empty
    assert plan_gta.steps[0].tool_name == "open_app"
    assert "gta" in plan_gta.steps[0].args["app_name"].lower()


def test_cloud_features_work_independently_when_agent_offline(client):
    """Verify cloud features work 100% when no Windows Agent is connected."""
    device_registry._sockets.clear()
    device_manager.device_sockets.clear()

    # Weather
    w_res = client.post("/command", json={"command": "what is the weather in Delhi"})
    assert w_res.status_code == 200
    assert w_res.json()["success"] is True

    # Stocks
    s_res = client.post("/command", json={"command": "what is Nvidia stock price"})
    assert s_res.status_code == 200
    assert s_res.json()["success"] is True

    # News
    n_res = client.post("/command", json={"command": "latest AI news"})
    assert n_res.status_code == 200
    assert n_res.json()["success"] is True

    # Knowledge
    k_res = client.post("/command", json={"command": "who is Alan Turing"})
    assert k_res.status_code == 200
    assert k_res.json()["success"] is True
    assert "Alan Turing" in k_res.json()["message"] or "Turing" in k_res.json()["message"]

