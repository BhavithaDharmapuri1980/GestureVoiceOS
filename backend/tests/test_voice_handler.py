"""
Unit tests for Safe Voice Command Handler
Team Novatrix
"""

import pytest
from backend.app.config import SystemSettings
from backend.app.mouse_controller import OSController
from backend.app.voice_handler import SafeVoiceCommandHandler


def test_whitelisted_voice_commands():
    settings = SystemSettings()
    controller = OSController(settings=settings, dry_run=True)
    handler = SafeVoiceCommandHandler(controller=controller, settings=settings)

    # Click
    res = handler.execute_command("please click here")
    assert res["success"] is True
    assert res["action"] == "click"

    # Scroll up / down
    res = handler.execute_command("scroll up")
    assert res["success"] is True
    assert res["action"] == "scroll_up"

    res = handler.execute_command("scroll down please")
    assert res["success"] is True
    assert res["action"] == "scroll_down"

    # Zoom in / out
    res = handler.execute_command("zoom in")
    assert res["success"] is True
    assert res["action"] == "zoom_in"

    res = handler.execute_command("zoom out")
    assert res["success"] is True
    assert res["action"] == "zoom_out"

    # Open browser
    res = handler.execute_command("open browser")
    assert res["success"] is True
    assert res["action"] == "open_browser"

    # Stop control
    res = handler.execute_command("stop control")
    assert res["success"] is True
    assert res["action"] == "stop_control"
    assert settings.control_enabled is False

    # Resume control
    res = handler.execute_command("resume")
    assert res["success"] is True
    assert res["action"] == "start_control"
    assert settings.control_enabled is True


def test_rejection_of_arbitrary_or_unsafe_commands():
    settings = SystemSettings()
    controller = OSController(settings=settings, dry_run=True)
    handler = SafeVoiceCommandHandler(controller=controller, settings=settings)

    unsafe_commands = [
        "format C:",
        "rmdir /s /q system32",
        "shutdown -s -t 0",
        "delete files",
        "powershell -c ls",
        "run malware",
        "open cmd"
    ]

    for cmd in unsafe_commands:
        res = handler.execute_command(cmd)
        assert res["success"] is False
        assert "not in the safe whitelist" in res["error"]
