"""
tests/test_phase1_device_registry.py — Phase 1 Test Suite for DRAX AI Multi-Device Foundation.
Tests:
1. Register device
2. Register second device
3. Multiple devices coexist
4. Heartbeat updates last_seen
5. Disconnect marks offline
6. Capability lookup
7. Primary device
8. Command ID generation
9. Duplicate command ID (Idempotency)
10. Existing Chrome command
11. Existing Spotify command
12. Existing VLC command
13. Cloud weather
14. Cloud stock
15. Cloud news
"""

import time
import pytest
from fastapi.testclient import TestClient

from cloud.main import app
from backend.devices.models import Device, CommandRecord
from backend.devices.registry import device_registry, DeviceRegistry
from backend.devices.router import find_device_for_capability, CapabilityRouter
from backend.database.db import get_device_db, get_command_db
from cloud.devices import device_manager


@pytest.fixture
def client():
    return TestClient(app)


# ─── 1. Register Device ───────────────────────────────────────────────────────

def test_01_register_device():
    """Verify registering a device creates in-memory and DB records with capabilities."""
    dev = device_registry.register_device(
        device_id="drax_pc_01",
        device_name="Workstation Primary",
        platform="windows",
        os_version="Windows 11",
        agent_version="2.0.0",
        capabilities=["apps", "browser", "media", "volume", "screen", "files", "system", "telemetry", "notifications"],
    )
    assert dev.device_id == "drax_pc_01"
    assert dev.status == "online"
    assert "browser" in dev.capabilities
    assert "media" in dev.capabilities

    db_rec = get_device_db("drax_pc_01")
    assert db_rec is not None
    assert db_rec["device_name"] == "Workstation Primary"
    assert "browser" in db_rec["capabilities"]


# ─── 2. Register Second Device ───────────────────────────────────────────────

def test_02_register_second_device():
    """Verify registering a second device registers independently without overwriting the first."""
    dev2 = device_registry.register_device(
        device_id="drax_pc_02",
        device_name="Office Laptop",
        platform="windows",
        os_version="Windows 10",
        capabilities=["apps", "browser", "media", "system"],
    )
    assert dev2.device_id == "drax_pc_02"
    assert dev2.device_name == "Office Laptop"

    db_rec = get_device_db("drax_pc_02")
    assert db_rec is not None
    assert db_rec["device_id"] == "drax_pc_02"


# ─── 3. Multiple Devices Coexist ─────────────────────────────────────────────

def test_03_multiple_devices_coexist():
    """Verify multiple simultaneously registered devices coexist in registry and DB."""
    all_devs = device_registry.get_all_devices()
    dev_ids = [(d.get("device_id") if isinstance(d, dict) else d.device_id) for d in all_devs]
    assert "drax_pc_01" in dev_ids
    assert "drax_pc_02" in dev_ids
    assert len(dev_ids) >= 2


# ─── 4. Heartbeat Updates last_seen ──────────────────────────────────────────

def test_04_heartbeat_updates_last_seen():
    """Verify heartbeat updates last_seen timestamp and status."""
    dev = device_registry.get_device("drax_pc_01")
    old_seen = dev.last_seen
    time.sleep(0.01)

    new_ts = "2026-08-31T18:30:00Z"
    device_registry.update_heartbeat("drax_pc_01", timestamp=new_ts, telemetry={"cpu_percent": 15})

    dev_updated = device_registry.get_device("drax_pc_01")
    assert dev_updated.last_seen == new_ts
    assert dev_updated.status == "online"
    assert dev_updated.telemetry.get("cpu_percent") == 15


# ─── 5. Disconnect Marks Offline ─────────────────────────────────────────────

def test_05_disconnect_marks_offline():
    """Verify unregistering / disconnecting marks device offline."""
    device_registry.mark_offline("drax_pc_02")
    dev2 = device_registry.get_device("drax_pc_02")
    assert dev2.status == "offline"

    db_rec = get_device_db("drax_pc_02")
    assert db_rec["status"] == "offline"


# ─── 6. Capability Lookup ───────────────────────────────────────────────────

def test_06_capability_lookup():
    """Verify capability-based routing finds appropriate online devices."""
    class MockSocket:
        async def send_json(self, data):
            pass

    mock_ws = MockSocket()
    device_registry.register_socket("drax_pc_01", mock_ws)
    device_registry.update_heartbeat("drax_pc_01")

    # Lookup browser capability
    res = find_device_for_capability("browser")
    assert res is not None
    dev, ws = res
    assert dev.device_id == "drax_pc_01"
    assert ws is mock_ws

    # Lookup unsupported capability
    unsupported_res = find_device_for_capability("quantum_teleportation")
    assert unsupported_res is None

    # Cleanup socket so other tests can test offline behavior
    device_registry.unregister_socket("drax_pc_01")


# ─── 7. Primary Device ───────────────────────────────────────────────────────

def test_07_primary_device():
    """Verify setting primary device and ensuring only one device is primary."""
    device_registry.set_primary_device("drax_pc_01")
    assert device_registry.get_device("drax_pc_01").is_primary is True
    assert device_registry.get_device("drax_pc_02").is_primary is False

    # Switch primary to dev2
    device_registry.set_primary_device("drax_pc_02")
    assert device_registry.get_device("drax_pc_02").is_primary is True
    assert device_registry.get_device("drax_pc_01").is_primary is False

    # Restore primary to dev1
    device_registry.set_primary_device("drax_pc_01")
    assert device_registry.get_device("drax_pc_01").is_primary is True


# ─── 8. Command ID Generation ───────────────────────────────────────────────

def test_08_command_id_generation(client):
    """Verify commands received without command_id get an auto-generated command_id."""
    resp = client.post("/command", json={"command": "what is the weather in Delhi"})
    assert resp.status_code == 200
    data = resp.json()
    assert "command_id" in data
    assert data["command_id"].startswith("cmd_")
    assert data["status"] == "success"


# ─── 9. Duplicate Command ID (Idempotency) ───────────────────────────────────

def test_09_duplicate_command_id_idempotency(client):
    """Verify duplicate command_id returns existing execution state without re-executing."""
    fixed_cmd_id = "cmd_test_idempotent_123"

    # First execution
    resp1 = client.post("/command", json={"command": "what is the weather in Delhi", "command_id": fixed_cmd_id})
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["command_id"] == fixed_cmd_id
    assert data1["status"] == "success"

    # Second execution with same command_id
    resp2 = client.post("/command", json={"command": "what is the weather in Delhi", "command_id": fixed_cmd_id})
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["command_id"] == fixed_cmd_id
    assert data2["result"] == data1["result"]
    assert data2["status"] == "success"


# ─── 10. Existing Chrome Command ─────────────────────────────────────────────

def test_10_existing_chrome_command(client):
    """Verify existing Chrome command parses to open_app or browser and routes properly."""
    device_manager.device_sockets.clear()
    device_registry._sockets.clear()
    resp = client.post("/command", json={"command": "open chrome"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] in ["open_app", "open_url", "browser_navigate", "apps.open"]
    assert "Windows Agent" in data["response"] or "device" in data["response"].lower()


# ─── 11. Existing Spotify Command ────────────────────────────────────────────

def test_11_existing_spotify_command(client):
    """Verify existing Spotify command parses and routes properly."""
    device_manager.device_sockets.clear()
    device_registry._sockets.clear()
    resp = client.post("/command", json={"command": "open spotify"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] in ["open_app", "play_media", "apps.open"]


# ─── 12. Existing VLC Command ────────────────────────────────────────────────

def test_12_existing_vlc_command(client):
    """Verify existing VLC command parses and routes properly."""
    device_manager.device_sockets.clear()
    device_registry._sockets.clear()
    resp = client.post("/command", json={"command": "open vlc"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] in ["open_app", "apps.open"]


# ─── 13. Cloud Weather ───────────────────────────────────────────────────────

def test_13_cloud_weather(client):
    """Verify cloud weather command executes server-side and returns forecast."""
    resp = client.post("/command", json={"command": "What is the weather in Delhi?"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["routed_to"] == "cloud"
    assert "Delhi" in data["response"] or "Weather" in data["response"] or "°" in data["response"]


# ─── 14. Cloud Stock ─────────────────────────────────────────────────────────

def test_14_cloud_stock(client):
    """Verify cloud stock command executes server-side and returns price."""
    resp = client.post("/command", json={"command": "What is Nvidia stock price?"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["routed_to"] == "cloud"
    assert "NVDA" in data["response"] or "Nvidia" in data["response"] or "$" in data["response"]


# ─── 15. Cloud News ──────────────────────────────────────────────────────────

def test_15_cloud_news(client):
    """Verify cloud news command executes server-side and returns headlines."""
    resp = client.post("/command", json={"command": "What is the latest AI news?"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["routed_to"] == "cloud"
    assert len(data["response"]) > 10


# ─── 16. Device API Endpoints ────────────────────────────────────────────────

def test_16_device_api_endpoints(client):
    """Verify GET /devices, GET /devices/{id}, POST /devices/{id}/primary."""
    # List devices
    resp = client.get("/devices")
    assert resp.status_code == 200
    devs = resp.json()["devices"]
    assert len(devs) >= 1

    # Get single device
    dev_id = devs[0]["device_id"]
    resp_single = client.get(f"/devices/{dev_id}")
    assert resp_single.status_code == 200
    assert resp_single.json()["device_id"] == dev_id

    # Set primary
    resp_prim = client.post(f"/devices/{dev_id}/primary")
    assert resp_prim.status_code == 200
    assert resp_prim.json()["is_primary"] is True
