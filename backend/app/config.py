"""
GestureVoice OS - Configuration and Settings
Team Novatrix
"""

from pydantic import BaseModel
from typing import Optional


class SystemSettings(BaseModel):
    # Operating control toggle
    control_enabled: bool = True
    
    # Cursor sensitivity and smoothing
    cursor_smoothing: float = 0.35  # Exponential moving average alpha (0.1 = very smooth/slower, 0.9 = fast/raw)
    deadband_radius: float = 4.0    # Pixels of jitter tolerance
    margin_percent: float = 0.15     # 15% margin for boundary reachability
    
    # Gesture thresholds (normalized 0.0 - 1.0)
    pinch_threshold: float = 0.055   # Thumb-to-Index distance for click
    pinch_release_threshold: float = 0.08
    click_cooldown_seconds: float = 0.35
    
    # Scroll settings
    scroll_threshold: float = 0.03   # Delta Y needed to trigger scroll
    scroll_speed: int = 120          # Scroll units per tick
    scroll_cooldown_seconds: float = 0.12
    
    # Two-hand zoom settings
    zoom_distance_delta_threshold: float = 0.04
    zoom_cooldown_seconds: float = 0.3
    
    # Camera settings
    camera_index: int = 0
    frame_width: int = 640
    frame_height: int = 480
    fps_target: int = 30
    
    # Safe stop
    failsafe_enabled: bool = True


# Global default settings instance
default_settings = SystemSettings()
