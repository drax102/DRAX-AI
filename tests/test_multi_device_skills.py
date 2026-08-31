"""
tests/test_multi_device_skills.py — Unit & Integration tests for Universal Multi-Device Assistant.
Tests device registry models, capability-based routing, modular skills, contextual dialogue,
and response protocol schemas.
"""

import pytest
from fastapi.testclient import TestClient

from cloud.main import app
from cloud.devices import device_manager, DEFAULT_CAPABILITIES
from backend.agent.capability_router import capability_router, CapabilityRouter
from backend.agent.planner import plan_request
from backend.agent.context import context
from backend.skills.media_skill import media_skill
from backend.skills.computer_skill import computer_skill
from backend.skills.productivity_skill import productivity_skill
from backend.skills.communication_skill import communication_skill
from backend.skills.web_skill import web_skill


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def cleanup():
    context.clear()
    yield
    context.clear()


# ─── 1. Universal Multi-Device Model & Registry Tests ───────────────────────

def test_device_capabilities_profile():
    """Verify default platform capability matrices."""
    assert "media" in DEFAULT_CAPABILITIES["windows"]
    assert "apps" in DEFAULT_CAPABILITIES["windows"]
    assert "calls" in DEFAULT_CAPABILITIES["android"]
    assert "sms" in DEFAULT_CAPABILITIES["android"]
    assert "web" in DEFAULT_CAPABILITIES["web"]


def test_pairing_and_primary_device():
    """Test generating pairing code with capabilities and setting primary device."""
    code = device_manager.generate_pairing_code(
        device_id="drax_win_test",
        device_name="Living Room PC",
        platform="windows",
        capabilities=["apps", "media", "volume", "system"],
    )
    assert code.startswith("DRAX-")

    paired = device_manager.verify_and_pair(code)
    assert paired is not None
    assert paired["device_id"] == "drax_win_test"
    assert paired["platform"] == "windows"
    assert "media" in paired["capabilities"]

    # Set as primary
    ok = device_manager.set_primary_device("drax_win_test")
    assert ok is True
    assert device_manager.devices["drax_win_test"]["is_primary"] is True


def test_list_devices_api(client):
    """Test GET /api/devices returns universal device schema."""
    resp = client.get("/api/devices")
    assert resp.status_code == 200
    data = resp.json()
    assert "devices" in data
    assert isinstance(data["devices"], list)


def test_set_primary_device_api(client):
    """Test POST /api/devices/{device_id}/primary endpoint."""
    code = device_manager.generate_pairing_code(
        device_id="drax_pc_office",
        device_name="Office Workstation",
        platform="windows",
    )
    device_manager.verify_and_pair(code)

    resp = client.post("/api/devices/drax_pc_office/primary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["is_primary"] is True


# ─── 2. Capability-Based Device Routing Tests ───────────────────────────────

def test_capability_router_cloud_vs_device():
    """Test mapping tools to required capabilities."""
    assert CapabilityRouter.get_required_capability("get_weather") == "cloud"
    assert CapabilityRouter.get_required_capability("get_stock_price") == "cloud"
    assert CapabilityRouter.get_required_capability("create_task") == "cloud"
    assert CapabilityRouter.get_required_capability("open_app") == "apps"
    assert CapabilityRouter.get_required_capability("next_track") == "media"
    assert CapabilityRouter.get_required_capability("volume_control") == "volume"
    assert CapabilityRouter.get_required_capability("make_call") == "calls"
    assert CapabilityRouter.get_required_capability("send_sms") == "sms"


def test_route_step_cloud():
    """Test routing pure cloud tools."""
    decision = capability_router.route_step("get_weather")
    assert decision.is_cloud is True
    assert decision.required_capability == "cloud"
    assert decision.is_available is True


def test_route_step_unsupported_when_offline():
    """Test routing device actions when device is offline."""
    decision = capability_router.route_step("make_call")
    assert decision.is_cloud is False
    assert decision.required_capability == "calls"
    assert decision.is_available is False
    assert "voice calls" in decision.unsupported_message.lower()


# ─── 3. Modular Skills Unit Tests ───────────────────────────────────────────

def test_media_skill():
    """Verify MediaSkill actions."""
    assert media_skill.name == "media"
    assert "play" in media_skill.actions
    assert "pause" in media_skill.actions
    assert "next" in media_skill.actions
    assert "volume_up" in media_skill.actions

    res = media_skill.next_track()
    assert "next track" in res.lower() or "skipped" in res.lower() or "playback" in res.lower()


def test_computer_skill():
    """Verify ComputerSkill actions."""
    assert computer_skill.name == "computer"
    assert "open_app" in computer_skill.actions
    assert "shutdown" in computer_skill.actions
    assert computer_skill.get_action("shutdown").requires_confirmation is True


def test_productivity_skill():
    """Verify ProductivitySkill task, reminder, alarm actions."""
    assert productivity_skill.name == "productivity"
    task_res = productivity_skill.add_task("Prepare demo presentation", "high")
    assert "Task added" in task_res

    list_res = productivity_skill.list_tasks()
    assert "Prepare demo presentation" in list_res


def test_communication_skill():
    """Verify CommunicationSkill call, sms, whatsapp actions."""
    assert communication_skill.name == "communication"
    call_res = communication_skill.make_call(contact="Mom")
    assert "Mom" in call_res

    sms_res = communication_skill.send_sms(recipient="Alex", message="Arriving in 10 mins")
    assert "Alex" in sms_res


def test_web_skill():
    """Verify WebSkill information actions."""
    assert web_skill.name == "web_intelligence"
    w_res = web_skill.get_weather("Delhi")
    assert "Delhi" in w_res or "Weather" in w_res


# ─── 4. Contextual Multi-Turn Dialogue Tests ─────────────────────────────────

def test_contextual_conversation_flow():
    """Test follow-up resolution: play music -> next -> make it louder."""
    # Turn 1: User plays music
    plan1 = plan_request("Play Arijit Singh on Spotify")
    assert plan1.steps[0].tool_name == "play_media"
    assert context.active_domain == "media"

    # Turn 2: User says "Next"
    plan2 = plan_request("Next")
    assert plan2.steps[0].tool_name == "next_track"

    # Turn 3: User says "Make it louder"
    plan3 = plan_request("Make it louder")
    assert plan3.steps[0].tool_name == "volume_control"
    assert plan3.steps[0].args["action"] == "up"


def test_contextual_finance_flow():
    """Test financial follow-up: Nvidia stock -> what about Tesla?"""
    plan1 = plan_request("What is Nvidia stock price?")
    assert plan1.steps[0].tool_name == "get_stock_price"
    context.update_turn(intent="get_stock_price", domain="finance", entity="NVDA")

    plan2 = plan_request("What about Tesla?")
    assert plan2.steps[0].tool_name == "get_stock_price"
    assert "tesla" in plan2.steps[0].args["symbol"].lower()


def test_contextual_weather_flow():
    """Test weather follow-up: Weather in Delhi -> and Mumbai?"""
    plan1 = plan_request("What is the weather in Delhi?")
    assert plan1.steps[0].tool_name == "get_weather"
    context.update_turn(intent="get_weather", domain="weather", entity="Delhi")

    plan2 = plan_request("What about Mumbai?")
    assert plan2.steps[0].tool_name == "get_weather"
    assert "mumbai" in plan2.steps[0].args["city"].lower()


# ─── 5. Standardized Response Protocol Schema Tests ─────────────────────────

def test_command_standardized_response_schema(client):
    """Verify /command returns standardized response protocol fields."""
    resp = client.post("/command", json={"command": "what is the weather in Delhi"})
    assert resp.status_code == 200
    data = resp.json()

    # Standardized protocol fields
    assert "command_id" in data
    assert "status" in data
    assert "intent" in data
    assert "timestamp" in data
    assert data["status"] in ["success", "failed", "executing"]

    # Legacy compatibility fields
    assert "success" in data
    assert "command" in data
    assert "response" in data
    assert "routed_to" in data
    assert "error" in data


def test_unsupported_capability_graceful_response(client):
    """Verify communication intent returns clear message when no mobile device is connected."""
    resp = client.post("/command", json={"command": "call Mom"})
    assert resp.status_code == 200
    data = resp.json()

    assert data["success"] is False
    assert data["status"] == "failed"
    assert data["intent"] == "make_call"
    assert "voice calls" in data["response"].lower() or "device" in data["response"].lower()
    assert data["error"]["code"] == "CAPABILITY_UNAVAILABLE"
