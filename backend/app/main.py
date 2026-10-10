"""
GestureVoice OS - FastAPI REST & WebSocket Backend
Team Novatrix
"""

import asyncio
import json
import logging
from typing import Dict, Any, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

from .config import SystemSettings, default_settings
from .camera_pipeline import CameraPipelineManager
from .voice_handler import SafeVoiceCommandHandler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("main")

app = FastAPI(
    title="GestureVoice OS API",
    description="Multimodal Touchless Computer Control System for Team Novatrix",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global singleton managers
settings = default_settings
pipeline = CameraPipelineManager(settings=settings)
voice_handler = SafeVoiceCommandHandler(controller=pipeline.controller, settings=settings)


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)


ws_manager = ConnectionManager()


@app.on_event("startup")
async def startup_event():
    import os
    if os.getenv("GESTUREVOICE_TESTING") == "1":
        logger.info("Test mode active: hardware camera pipeline skipped.")
        pipeline.controller.dry_run = True
        return
    logger.info("Starting GestureVoice OS camera pipeline...")
    pipeline.start()


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Stopping GestureVoice OS camera pipeline...")
    pipeline.stop()


# ----------------------------------------------------
# REST API Endpoints
# ----------------------------------------------------

@app.get("/api/status")
def get_status():
    latest = pipeline.get_latest_telemetry()
    return {
        "status": "online",
        "control_enabled": settings.control_enabled,
        "emergency_stopped": pipeline.controller.emergency_stopped,
        "camera_connected": latest.get("camera_connected", False),
        "screen_resolution": {
            "width": pipeline.controller.screen_width,
            "height": pipeline.controller.screen_height
        },
        "latest_telemetry": latest
    }


class ControlToggleRequest(BaseModel):
    enabled: bool


@app.post("/api/control/toggle")
def toggle_control(req: ControlToggleRequest):
    settings.control_enabled = req.enabled
    if not req.enabled:
        pipeline.controller.release_all()
    else:
        pipeline.controller.emergency_stopped = False
    return {"control_enabled": settings.control_enabled, "message": "Control state updated"}


@app.post("/api/control/stop")
def emergency_stop():
    """Safe stop mechanism - immediately halts all simulated mouse actions."""
    settings.control_enabled = False
    pipeline.controller.emergency_stopped = True
    pipeline.controller.release_all()
    logger.warning("EMERGENCY SAFE STOP TRIGGERED via API")
    return {"status": "emergency_stopped", "control_enabled": False, "message": "All controls safely halted"}


@app.get("/api/settings")
def get_settings():
    return settings.dict()


@app.post("/api/settings")
def update_settings(new_settings: SystemSettings):
    global settings
    settings.cursor_smoothing = new_settings.cursor_smoothing
    settings.deadband_radius = new_settings.deadband_radius
    settings.margin_percent = new_settings.margin_percent
    settings.pinch_threshold = new_settings.pinch_threshold
    settings.scroll_speed = new_settings.scroll_speed
    settings.control_enabled = new_settings.control_enabled
    pipeline.controller.settings = settings
    return {"status": "success", "settings": settings.dict()}


class VoiceCommandRequest(BaseModel):
    transcript: str


@app.post("/api/voice/command")
def execute_voice_command(req: VoiceCommandRequest):
    result = voice_handler.execute_command(req.transcript)
    return result


@app.get("/api/voice/allowed")
def get_allowed_voice_commands():
    return {"allowed_commands": voice_handler.ALLOWED_ACTIONS}


# ----------------------------------------------------
# Live MJPEG Video Stream
# ----------------------------------------------------

def generate_video_stream():
    while True:
        frame_bytes = pipeline.get_latest_frame_bytes()
        if frame_bytes:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        asyncio.run(asyncio.sleep(0.033))  # ~30 FPS


@app.get("/api/video_feed")
async def video_feed():
    """Live MJPEG video stream showing OpenCV camera feed and MediaPipe landmarks."""
    async def frame_generator():
        try:
            while True:
                frame_bytes = pipeline.get_latest_frame_bytes()
                if frame_bytes:
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n"
                        b"Content-Length: " + str(len(frame_bytes)).encode() + b"\r\n\r\n"
                        + frame_bytes + b"\r\n"
                    )
                await asyncio.sleep(0.033)
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Connection": "close"
        }
    )


# ----------------------------------------------------
# Real-time WebSocket: Telemetry & Voice Dispatch
# ----------------------------------------------------

@app.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    await ws_manager.connect(websocket)
    tick_task = None
    try:
        # Background task to send telemetry ticks
        async def send_ticks():
            while True:
                try:
                    telemetry = pipeline.get_latest_telemetry()
                    await websocket.send_json({"type": "telemetry", "data": telemetry})
                    await asyncio.sleep(0.08)  # 12.5 updates/sec
                except (WebSocketDisconnect, RuntimeError, asyncio.CancelledError):
                    break
                except Exception:
                    break

        tick_task = asyncio.create_task(send_ticks())

        while True:
            # Handle incoming messages from frontend (e.g. voice transcript)
            raw_msg = await websocket.receive_text()
            try:
                data = json.loads(raw_msg)
                msg_type = data.get("type")

                if msg_type == "voice_command":
                    transcript = data.get("transcript", "")
                    res = voice_handler.execute_command(transcript)
                    await websocket.send_json({
                        "type": "voice_response",
                        "transcript": transcript,
                        "result": res
                    })

                elif msg_type == "toggle_control":
                    enabled = bool(data.get("enabled", True))
                    settings.control_enabled = enabled
                    if not enabled:
                        pipeline.controller.release_all()
                    else:
                        pipeline.controller.emergency_stopped = False
                    await websocket.send_json({
                        "type": "control_status",
                        "control_enabled": settings.control_enabled
                    })

                elif msg_type == "safe_stop":
                    settings.control_enabled = False
                    pipeline.controller.emergency_stopped = True
                    pipeline.controller.release_all()
                    await websocket.send_json({
                        "type": "control_status",
                        "control_enabled": False,
                        "emergency_stopped": True
                    })

            except json.JSONDecodeError:
                pass

    except (WebSocketDisconnect, RuntimeError):
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if tick_task and not tick_task.done():
            tick_task.cancel()
        ws_manager.disconnect(websocket)
