"""
Unit tests for FastAPI REST Endpoints
Team Novatrix
"""

import os
os.environ["GESTUREVOICE_TESTING"] = "1"

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app, pipeline


@pytest.fixture(scope="module")
def client():
    pipeline.controller.dry_run = True
    with TestClient(app) as test_client:
        yield test_client


def test_api_status(client):
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "screen_resolution" in data
    assert "control_enabled" in data


def test_toggle_control(client):
    # Toggle off
    response = client.post("/api/control/toggle", json={"enabled": False})
    assert response.status_code == 200
    assert response.json()["control_enabled"] is False

    # Toggle on
    response = client.post("/api/control/toggle", json={"enabled": True})
    assert response.status_code == 200
    assert response.json()["control_enabled"] is True


def test_emergency_stop(client):
    response = client.post("/api/control/stop")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "emergency_stopped"
    assert data["control_enabled"] is False


def test_settings_get_and_post(client):
    # Get settings
    get_res = client.get("/api/settings")
    assert get_res.status_code == 200
    current_settings = get_res.json()
    assert "cursor_smoothing" in current_settings

    # Update settings
    current_settings["cursor_smoothing"] = 0.45
    current_settings["scroll_speed"] = 150
    post_res = client.post("/api/settings", json=current_settings)
    assert post_res.status_code == 200
    updated = post_res.json()["settings"]
    assert updated["cursor_smoothing"] == 0.45
    assert updated["scroll_speed"] == 150


def test_voice_command_endpoint(client):
    # Allowed command
    res_ok = client.post("/api/voice/command", json={"transcript": "scroll up"})
    assert res_ok.status_code == 200
    assert res_ok.json()["success"] is True

    # Disallowed command
    res_bad = client.post("/api/voice/command", json={"transcript": "format drive"})
    assert res_bad.status_code == 200
    assert res_bad.json()["success"] is False
