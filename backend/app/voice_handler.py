"""
GestureVoice OS - Safe Voice Command Handler
Team Novatrix
"""

import logging
from typing import Dict, Any, Optional
from .config import SystemSettings
from .mouse_controller import OSController

logger = logging.getLogger("voice_handler")


class SafeVoiceCommandHandler:
    """
    Executes strictly whitelisted OS commands received from Web Speech API.
    Guarantees no arbitrary shell execution or command injection.
    """

    ALLOWED_ACTIONS = {
        "click": "Triggers left mouse click",
        "left click": "Triggers left mouse click",
        "double click": "Triggers double mouse click",
        "right click": "Triggers right mouse click",
        "scroll up": "Scrolls page/window up",
        "scroll down": "Scrolls page/window down",
        "zoom in": "Zooms in (Ctrl + Plus)",
        "zoom out": "Zooms out (Ctrl + Minus)",
        "open browser": "Opens default web browser safely",
        "stop control": "Pauses gesture and system controls",
        "pause": "Pauses gesture and system controls",
        "start control": "Resumes gesture and system controls",
        "resume": "Resumes gesture and system controls",
        "safe stop": "Emergency stop system controls"
    }

    def __init__(self, controller: OSController, settings: SystemSettings):
        self.controller = controller
        self.settings = settings

    def execute_command(self, raw_transcript: str) -> Dict[str, Any]:
        """
        Parses spoken input against whitelist and triggers the safe action.
        """
        if not raw_transcript:
            return {"success": False, "error": "Empty command transcript"}

        text = raw_transcript.strip().lower()
        logger.info(f"Received voice command: '{text}'")

        # Match against whitelist
        matched_cmd = None
        for allowed in sorted(self.ALLOWED_ACTIONS.keys(), key=len, reverse=True):
            if allowed in text:
                matched_cmd = allowed
                break

        if not matched_cmd:
            return {
                "success": False,
                "error": f"Command '{text}' is not in the safe whitelist.",
                "allowed_commands": list(self.ALLOWED_ACTIONS.keys())
            }

        # Dispatch safe action
        try:
            if matched_cmd in ("click", "left click"):
                res = self.controller.click("left")
                return {"success": res, "action": "click", "message": "Left click executed"}

            elif matched_cmd == "double click":
                if not self.controller.dry_run:
                    import pyautogui
                    pyautogui.doubleClick()
                return {"success": True, "action": "double_click", "message": "Double click executed"}

            elif matched_cmd == "right click":
                res = self.controller.click("right")
                return {"success": res, "action": "right_click", "message": "Right click executed"}

            elif matched_cmd == "scroll up":
                res = self.controller.scroll("up", multiplier=2.5)
                return {"success": res, "action": "scroll_up", "message": "Scrolled up"}

            elif matched_cmd == "scroll down":
                res = self.controller.scroll("down", multiplier=2.5)
                return {"success": res, "action": "scroll_down", "message": "Scrolled down"}

            elif matched_cmd == "zoom in":
                res = self.controller.zoom("in")
                return {"success": res, "action": "zoom_in", "message": "Zoomed in"}

            elif matched_cmd == "zoom out":
                res = self.controller.zoom("out")
                return {"success": res, "action": "zoom_out", "message": "Zoomed out"}

            elif matched_cmd == "open browser":
                res = self.controller.open_browser("https://www.google.com")
                return {"success": res, "action": "open_browser", "message": "Browser opened safely"}

            elif matched_cmd in ("stop control", "pause", "safe stop"):
                self.settings.control_enabled = False
                self.controller.release_all()
                return {"success": True, "action": "stop_control", "message": "Controls safely paused"}

            elif matched_cmd in ("start control", "resume"):
                self.settings.control_enabled = True
                self.controller.emergency_stopped = False
                return {"success": True, "action": "start_control", "message": "Controls resumed"}

        except Exception as e:
            logger.error(f"Voice execution error for '{matched_cmd}': {e}")
            return {"success": False, "error": str(e)}

        return {"success": False, "error": "Unhandled whitelist action"}
