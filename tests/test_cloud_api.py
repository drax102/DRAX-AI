"""
test_cloud_api.py — Unit tests for Drax Cloud FastAPI endpoints and device pairing.
"""

from fastapi.testclient import TestClient
from cloud.main import app
from cloud.devices import device_manager

client = TestClient(app)


def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "DRAX AI Cloud API"
    assert "version" in data
    assert "timestamp" in data


def test_status_endpoint():
    resp = client.get("/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "online"
    assert "devices" in data


def test_device_pairing_flow():
    # 1. Windows agent generates pairing code
    gen_resp = client.post("/api/pair/generate", json={
        "device_id": "test_win_pc_1",
        "device_name": "Test Windows PC",
        "token": "secret_token_123"
    })
    assert gen_resp.status_code == 200
    code = gen_resp.json()["pairing_code"]
    assert code.startswith("DRAX-")

    # 2. Web dashboard pairs with code
    pair_resp = client.post("/api/pair/connect", json={"pairing_code": code})
    assert pair_resp.status_code == 200
    paired_data = pair_resp.json()
    assert paired_data["status"] == "success"
    assert paired_data["device"]["device_id"] == "test_win_pc_1"

    # 3. Verify in device list
    devs_resp = client.get("/api/devices")
    assert devs_resp.status_code == 200
    devs = devs_resp.json()["devices"]
    assert any(d["device_id"] == "test_win_pc_1" for d in devs)


def test_cloud_tasks_endpoints():
    # Create task
    create_resp = client.post("/tasks", json={"title": "Cloud Demo Task", "priority": "high"})
    assert create_resp.status_code == 200
    t_id = create_resp.json()["id"]

    # List tasks
    list_resp = client.get("/tasks")
    assert list_resp.status_code == 200
    tasks = list_resp.json()["tasks"]
    assert any(t["id"] == t_id for t in tasks)

    # Delete task
    del_resp = client.delete(f"/tasks/{t_id}")
    assert del_resp.status_code == 200


def test_cloud_info_endpoints():
    stocks_resp = client.get("/stocks?symbol=AAPL")
    assert stocks_resp.status_code == 200
    assert "AAPL:" in stocks_resp.json()["quote"] or "USD" in stocks_resp.json()["quote"]

    watchlist_resp = client.get("/watchlist")
    assert watchlist_resp.status_code == 200
    assert "watchlist" in watchlist_resp.json()

    # Test weather for various cities
    for city in ["Delhi", "Mumbai", "Chandigarh", "Jalandhar", "London", "New York"]:
        weather_resp = client.get(f"/weather?city={city}")
        assert weather_resp.status_code == 200
        weather_text = weather_resp.json()["weather"]
        assert "Weather in" in weather_text or "Temperature is" in weather_text or "°C" in weather_text


def test_cloud_command_routing():
    # Cloud-handled weather command
    weather_cmd = client.post("/command", json={"command": "what is the weather in Delhi"})
    assert weather_cmd.status_code == 200
    weather_data = weather_cmd.json()
    assert weather_data["routed_to"] == "cloud"
    assert "Delhi" in weather_data["response"] and ("Weather in" in weather_data["response"] or "°C" in weather_data["response"])

    # Cloud-handled stock command
    cmd_resp = client.post("/command", json={"command": "what is Nvidia stock price"})
    assert cmd_resp.status_code == 200
    data = cmd_resp.json()
    assert data["routed_to"] == "cloud"
    assert "NVDA" in data["response"] or "USD" in data["response"]

    # Cloud-handled news command
    news_cmd = client.post("/command", json={"command": "latest AI news"})
    assert news_cmd.status_code == 200
    news_data = news_cmd.json()
    assert news_data["routed_to"] == "cloud"
    assert "News Headlines:" in news_data["response"]

    # Cloud-handled web search command
    search_cmd = client.post("/command", json={"command": "search for Python tutorials"})
    assert search_cmd.status_code == 200
    search_data = search_cmd.json()
    assert "python tutorials" in search_data["response"].lower()

    # Cloud-handled knowledge command
    know_resp = client.post("/command", json={"command": "tell me about artificial intelligence"})
    assert know_resp.status_code == 200
    know_data = know_resp.json()
    assert know_data["routed_to"] == "cloud"
    assert "intelligence" in know_data["response"].lower() or "ai" in know_data["response"].lower()

    # Cloud-handled task creation command
    task_cmd_resp = client.post("/command", json={"command": "add a task to study"})
    assert task_cmd_resp.status_code == 200
    task_cmd_data = task_cmd_resp.json()
    assert task_cmd_data["routed_to"] == "cloud"
    assert "study" in task_cmd_data["response"].lower()

    # Cloud-handled list tasks command
    list_tasks_resp = client.post("/command", json={"command": "show my tasks"})
    assert list_tasks_resp.status_code == 200
    list_tasks_data = list_tasks_resp.json()
    assert list_tasks_data["routed_to"] == "cloud"
    assert "tasks" in list_tasks_data["response"].lower()
