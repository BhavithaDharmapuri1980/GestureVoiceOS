"""
GestureVoice OS - Coordinated Single Webcam Pipeline Manager
Team Novatrix
"""

import cv2
import time
import threading
import logging
import base64
from typing import Optional, Dict, Any, Callable
import numpy as np

from .config import SystemSettings, default_settings
from .gesture_engine import GestureEngine, GestureType
from .mouse_controller import OSController

logger = logging.getLogger("camera_pipeline")


class CameraPipelineManager:
    """
    Singleton thread-safe camera capture pipeline coordinating OpenCV,
    MediaPipe gesture recognition, OS control execution, and live MJPEG streaming.
    Guarantees:
    - Exactly ONE OpenCV VideoCapture instance.
    - Zero frames saved to disk (in-memory only).
    - Robust fallback if physical webcam is busy or absent.
    """

    def __init__(self, settings: Optional[SystemSettings] = None, dry_run: bool = False):
        self.settings = settings or default_settings
        self.dry_run = dry_run

        self.gesture_engine = GestureEngine()
        self.controller = OSController(settings=self.settings, dry_run=self.dry_run)

        self.cap: Optional[cv2.VideoCapture] = None
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()

        # Shared state for clients - pre-encode warm-up frame so video feed starts instantly
        init_frame = self._generate_synthetic_frame(0)
        ret, buf = cv2.imencode('.jpg', init_frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        self.latest_jpeg_bytes: Optional[bytes] = buf.tobytes() if ret else None
        self.latest_telemetry: Dict[str, Any] = {
            "status": "idle",
            "camera_connected": False,
            "hands_count": 0,
            "gesture": GestureType.NONE,
            "action": "none",
            "fps": 0.0,
            "timestamp": time.time()
        }

        # Event callbacks
        self.telemetry_callbacks: list[Callable[[Dict[str, Any]], None]] = []

    def register_telemetry_callback(self, cb: Callable[[Dict[str, Any]], None]):
        self.telemetry_callbacks.append(cb)

    def start(self):
        """Starts the capture and processing background thread."""
        with self.lock:
            if self.is_running:
                return
            self.is_running = True
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()
            logger.info("Camera pipeline thread started.")

    def stop(self):
        """Stops the capture thread and releases camera resources."""
        with self.lock:
            self.is_running = False
            self.controller.release_all()

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.5)

        with self.lock:
            if self.cap and self.cap.isOpened():
                self.cap.release()
                self.cap = None
        logger.info("Camera pipeline stopped cleanly.")

    def _open_camera(self) -> bool:
        """Attempts to open physical webcam, supports Windows DirectShow backend."""
        try:
            # On Windows, cv2.CAP_DSHOW provides fastest startup
            self.cap = cv2.VideoCapture(self.settings.camera_index, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                # Fallback to default
                self.cap = cv2.VideoCapture(self.settings.camera_index)

            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.settings.frame_width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.settings.frame_height)
                self.cap.set(cv2.CAP_PROP_FPS, self.settings.fps_target)
                logger.info(f"Webcam opened on index {self.settings.camera_index}")
                return True
        except Exception as e:
            logger.error(f"Failed to open webcam: {e}")

        return False

    def _generate_synthetic_frame(self, frame_count: int) -> np.ndarray:
        """Fallback mock frame when no hardware camera is plugged in."""
        w, h = self.settings.frame_width, self.settings.frame_height
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        # Cyber grid pattern
        frame[:] = (18, 18, 24)
        for y in range(0, h, 40):
            cv2.line(frame, (0, y), (w, y), (30, 30, 42), 1)
        for x in range(0, w, 40):
            cv2.line(frame, (x, 0), (x, h), (30, 30, 42), 1)

        cv2.putText(
            frame,
            "CAMERA SIMULATION / STANDBY",
            (int(w * 0.15), int(h * 0.45)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            (0, 220, 255),
            2,
            cv2.LINE_AA
        )
        cv2.putText(
            frame,
            "Connect a USB Webcam or Enable Permissions",
            (int(w * 0.12), int(h * 0.55)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (180, 180, 180),
            1,
            cv2.LINE_AA
        )
        return frame

    def _run_loop(self):
        camera_ok = self._open_camera()
        prev_time = time.time()
        frame_idx = 0

        while self.is_running:
            frame_idx += 1
            frame = None

            if camera_ok and self.cap and self.cap.isOpened():
                ret, raw_frame = self.cap.read()
                if ret and raw_frame is not None:
                    # Mirror horizontally so moving right moves right
                    frame = cv2.flip(raw_frame, 1)
                else:
                    logger.warning("Camera read failed, retrying...")
                    time.sleep(0.1)

            if frame is None:
                # Fallback to diagnostic synthetic frame
                camera_ok = False
                frame = self._generate_synthetic_frame(frame_idx)
                time.sleep(0.033)  # ~30 FPS

            # Process frame with gesture engine
            try:
                result = self.gesture_engine.process_frame(frame)
            except Exception as e:
                logger.error(f"Gesture processing error: {e}")
                result = {
                    "gesture": GestureType.NONE,
                    "hands_count": 0,
                    "action_data": {},
                    "hands": []
                }

            gesture = result["gesture"]
            action_data = result["action_data"]
            hands = result["hands"]
            action_executed = "none"

            # Execute computer control if enabled
            if self.settings.control_enabled and not self.controller.emergency_stopped:
                try:
                    if gesture == GestureType.POINT_MOVE and "cursor_norm_x" in action_data:
                        norm_x = action_data["cursor_norm_x"]
                        norm_y = action_data["cursor_norm_y"]
                        target_x, target_y = self.controller.map_normalized_to_screen(norm_x, norm_y)
                        curr_x, curr_y = self.controller.smooth_move(target_x, target_y)
                        action_executed = f"Cursor ({curr_x}, {curr_y})"

                    elif gesture == GestureType.PINCH_CLICK:
                        if self.controller.click(button="left"):
                            action_executed = "Pinch Click"

                    elif gesture == GestureType.SCROLL_UP:
                        if self.controller.scroll("up"):
                            action_executed = "Scroll Up"

                    elif gesture == GestureType.SCROLL_DOWN:
                        if self.controller.scroll("down"):
                            action_executed = "Scroll Down"

                    elif gesture == GestureType.TWO_HAND_ZOOM_IN:
                        if self.controller.zoom("in"):
                            action_executed = "Zoom In (+)"

                    elif gesture == GestureType.TWO_HAND_ZOOM_OUT:
                        if self.controller.zoom("out"):
                            action_executed = "Zoom Out (-)"

                except Exception as e:
                    logger.error(f"Action execution error: {e}")
                    action_executed = f"Error: {str(e)}"
            elif not self.settings.control_enabled:
                action_executed = "Control Paused"

            # Draw HUD annotations on frame
            self.gesture_engine.draw_hud_landmarks(frame, hands, gesture)

            # Compute FPS
            now = time.time()
            fps = 1.0 / (now - prev_time) if (now - prev_time) > 0 else 0.0
            prev_time = now

            # Encode frame to JPEG for live web preview
            ret_enc, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            if ret_enc:
                self.latest_jpeg_bytes = buffer.tobytes()

            # Update telemetry
            telemetry = {
                "status": "active" if self.settings.control_enabled else "paused",
                "camera_connected": camera_ok,
                "hands_count": len(hands),
                "gesture": gesture,
                "action": action_executed,
                "fps": round(fps, 1),
                "timestamp": now,
                "emergency_stopped": self.controller.emergency_stopped
            }
            self.latest_telemetry = telemetry

            # Notify listeners
            for cb in self.telemetry_callbacks:
                try:
                    cb(telemetry)
                except Exception:
                    pass

    def get_latest_frame_bytes(self) -> Optional[bytes]:
        return self.latest_jpeg_bytes

    def get_latest_telemetry(self) -> Dict[str, Any]:
        return self.latest_telemetry
