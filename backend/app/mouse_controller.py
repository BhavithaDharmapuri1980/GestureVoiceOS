"""
GestureVoice OS - Mouse & System Controller (PyAutoGUI Wrapper)
Team Novatrix
"""

import math
import time
import logging
import webbrowser
from typing import Tuple, Optional
import pyautogui

from .config import SystemSettings, default_settings

logger = logging.getLogger("mouse_controller")

# Setup PyAutoGUI defaults
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.001


class OSController:
    """Safe, smoothed, failsafe-protected OS controller."""

    def __init__(self, settings: Optional[SystemSettings] = None, dry_run: bool = False):
        self.settings = settings or default_settings
        self.dry_run = dry_run
        
        try:
            self.screen_width, self.screen_height = pyautogui.size()
        except Exception:
            self.screen_width, self.screen_height = 1920, 1080
            
        self.prev_x = self.screen_width / 2.0
        self.prev_y = self.screen_height / 2.0
        
        self.is_mouse_down = False
        self.last_click_time = 0.0
        self.last_scroll_time = 0.0
        self.last_zoom_time = 0.0
        self.emergency_stopped = False

    def reset_smoothing(self):
        """Reset smoothed coordinates to screen center or current mouse pos."""
        try:
            curr_x, curr_y = pyautogui.position()
            self.prev_x = float(curr_x)
            self.prev_y = float(curr_y)
        except Exception:
            self.prev_x = self.screen_width / 2.0
            self.prev_y = self.screen_height / 2.0

    def map_normalized_to_screen(self, norm_x: float, norm_y: float) -> Tuple[int, int]:
        """
        Maps normalized [0, 1] coordinates from camera to screen pixels,
        applying margin calibration padding so edge targets are reachable.
        """
        m = self.settings.margin_percent
        # Clamp within margins
        clamped_x = max(m, min(1.0 - m, norm_x))
        clamped_y = max(m, min(1.0 - m, norm_y))
        
        # Rescale [m, 1-m] -> [0, 1]
        scaled_x = (clamped_x - m) / (1.0 - 2 * m)
        scaled_y = (clamped_y - m) / (1.0 - 2 * m)
        
        target_x = scaled_x * self.screen_width
        target_y = scaled_y * self.screen_height
        
        return int(target_x), int(target_y)

    def smooth_move(self, target_x: float, target_y: float) -> Tuple[int, int]:
        """
        Applies Exponential Moving Average (EMA) and deadband jitter reduction.
        """
        alpha = self.settings.cursor_smoothing
        dx = target_x - self.prev_x
        dy = target_y - self.prev_y
        dist = math.hypot(dx, dy)
        
        # Deadband to suppress micro-tremors
        if dist < self.settings.deadband_radius:
            return int(self.prev_x), int(self.prev_y)
            
        new_x = self.prev_x + alpha * dx
        new_y = self.prev_y + alpha * dy
        
        # Clamp within screen bounds
        new_x = max(2, min(self.screen_width - 3, new_x))
        new_y = max(2, min(self.screen_height - 3, new_y))
        
        self.prev_x = new_x
        self.prev_y = new_y
        
        if not self.dry_run and not self.emergency_stopped:
            try:
                pyautogui.moveTo(int(new_x), int(new_y))
            except pyautogui.FailSafeException:
                logger.warning("PyAutoGUI FailSafe triggered! Emergency stop active.")
                self.emergency_stopped = True
            except Exception as e:
                logger.error(f"Move error: {e}")
                
        return int(new_x), int(new_y)

    def click(self, button: str = "left", bypass_cooldown: bool = False) -> bool:
        """Triggers a mouse click with cooldown."""
        now = time.time()
        if not bypass_cooldown and not self.dry_run and (now - self.last_click_time < self.settings.click_cooldown_seconds):
            return False
            
        self.last_click_time = now
        if not self.dry_run and not self.emergency_stopped:
            try:
                pyautogui.click(button=button)
                return True
            except pyautogui.FailSafeException:
                self.emergency_stopped = True
            except Exception as e:
                logger.error(f"Click error: {e}")
        return True

    def mouse_down(self, button: str = "left"):
        """Holds down the mouse button for dragging."""
        if not self.is_mouse_down:
            self.is_mouse_down = True
            if not self.dry_run and not self.emergency_stopped:
                try:
                    pyautogui.mouseDown(button=button)
                except pyautogui.FailSafeException:
                    self.emergency_stopped = True
                except Exception as e:
                    logger.error(f"MouseDown error: {e}")

    def mouse_up(self, button: str = "left"):
        """Releases the mouse button after dragging."""
        if self.is_mouse_down:
            self.is_mouse_down = False
            if not self.dry_run and not self.emergency_stopped:
                try:
                    pyautogui.mouseUp(button=button)
                except pyautogui.FailSafeException:
                    self.emergency_stopped = True
                except Exception as e:
                    logger.error(f"MouseUp error: {e}")

    def scroll(self, direction: str, multiplier: float = 1.0, bypass_cooldown: bool = False) -> bool:
        """
        Scrolls up or down. direction in ('up', 'down').
        """
        now = time.time()
        if not bypass_cooldown and not self.dry_run and (now - self.last_scroll_time < self.settings.scroll_cooldown_seconds):
            return False
            
        self.last_scroll_time = now
        amount = int(self.settings.scroll_speed * multiplier)
        if direction.lower() == "down":
            amount = -amount
            
        if not self.dry_run and not self.emergency_stopped:
            try:
                pyautogui.scroll(amount)
                return True
            except pyautogui.FailSafeException:
                self.emergency_stopped = True
            except Exception as e:
                logger.error(f"Scroll error: {e}")
        return True

    def zoom(self, mode: str, bypass_cooldown: bool = False) -> bool:
        """
        Zooms in or out via standard OS keyboard shortcuts (Ctrl + +/-).
        mode in ('in', 'out').
        """
        now = time.time()
        if not bypass_cooldown and not self.dry_run and (now - self.last_zoom_time < self.settings.zoom_cooldown_seconds):
            return False
            
        self.last_zoom_time = now
        if not self.dry_run and not self.emergency_stopped:
            try:
                if mode.lower() == "in":
                    # Ctrl + '+' or Ctrl + '='
                    pyautogui.hotkey('ctrl', '+')
                elif mode.lower() == "out":
                    # Ctrl + '-'
                    pyautogui.hotkey('ctrl', '-')
                return True
            except pyautogui.FailSafeException:
                self.emergency_stopped = True
            except Exception as e:
                logger.error(f"Zoom error: {e}")
        return True

    def open_browser(self, url: str = "https://www.google.com") -> bool:
        """Safely opens user's default browser."""
        try:
            # Validate url starts with http/https to prevent local file execution
            if not url.startswith("http://") and not url.startswith("https://"):
                url = "https://" + url
            webbrowser.open(url)
            return True
        except Exception as e:
            logger.error(f"Failed to open browser: {e}")
            return False

    def release_all(self):
        """Safety release on stop."""
        if self.is_mouse_down:
            self.mouse_up()
        self.is_mouse_down = False
