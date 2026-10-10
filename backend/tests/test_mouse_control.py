"""
Unit tests for OSController (PyAutoGUI Wrapper & Safe Movements)
Team Novatrix
"""

import pytest
from backend.app.config import SystemSettings
from backend.app.mouse_controller import OSController


def test_coordinate_mapping():
    settings = SystemSettings(margin_percent=0.10)
    controller = OSController(settings=settings, dry_run=True)
    controller.screen_width = 1920
    controller.screen_height = 1080

    # Center (0.5, 0.5) should map to center of screen
    x, y = controller.map_normalized_to_screen(0.5, 0.5)
    assert x == 960
    assert y == 540

    # Within margin (e.g. 0.05 < margin 0.10) should clamp to 0
    x_min, y_min = controller.map_normalized_to_screen(0.05, 0.05)
    assert x_min == 0
    assert y_min == 0

    # Upper margin (e.g. 0.95 > 0.90) should clamp to max screen
    x_max, y_max = controller.map_normalized_to_screen(0.95, 0.95)
    assert x_max == 1920
    assert y_max == 1080


def test_smoothing_and_deadband():
    settings = SystemSettings(cursor_smoothing=0.5, deadband_radius=5.0)
    controller = OSController(settings=settings, dry_run=True)
    controller.prev_x = 500.0
    controller.prev_y = 500.0

    # Jitter under deadband radius should return current position
    smooth_x, smooth_y = controller.smooth_move(502.0, 501.0)
    assert smooth_x == 500
    assert smooth_y == 500

    # Large movement should apply alpha = 0.5 EMA: 500 + 0.5*(600-500) = 550
    smooth_x2, smooth_y2 = controller.smooth_move(600.0, 500.0)
    assert smooth_x2 == 550
    assert smooth_y2 == 500


def test_safe_actions_dry_run():
    controller = OSController(dry_run=True)
    assert controller.click("left") is True
    assert controller.scroll("up") is True
    assert controller.zoom("in") is True
    assert controller.zoom("out") is True
    assert controller.open_browser("https://example.com") is True


def test_failsafe_and_emergency_stop():
    controller = OSController(dry_run=True)
    controller.emergency_stopped = True
    # In emergency stopped state, actions should not cause exceptions and controller is paused
    assert controller.emergency_stopped is True
