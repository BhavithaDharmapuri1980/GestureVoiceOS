"""
GestureVoice OS - Hand Gesture Engine (MediaPipe Tasks + OpenCV)
Team Novatrix
"""

import math
import time
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import vision, BaseOptions


class GestureType:
    NONE = "NONE"
    POINT_MOVE = "POINT_MOVE"        # Index finger pointing -> cursor movement
    PINCH_CLICK = "PINCH_CLICK"      # Thumb + Index pinch -> mouse click
    SCROLL_UP = "SCROLL_UP"          # Two fingers up -> scroll up
    SCROLL_DOWN = "SCROLL_DOWN"      # Two fingers down -> scroll down
    TWO_HAND_ZOOM_IN = "ZOOM_IN"     # Two hands spreading apart
    TWO_HAND_ZOOM_OUT = "ZOOM_OUT"   # Two hands coming together
    OPEN_PALM = "OPEN_PALM"          # Open hand (neutral / hover)
    FIST = "FIST"                    # Closed fist (neutral / hover)


HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),        # Thumb
    (0, 5), (5, 6), (6, 7), (7, 8),        # Index
    (5, 9), (9, 10), (10, 11), (11, 12),   # Middle
    (9, 13), (13, 14), (14, 15), (15, 16), # Ring
    (13, 17), (17, 18), (18, 19), (19, 20),# Pinky
    (0, 17)                                # Palm base
]


class GestureEngine:
    """
    Analyzes hand landmarks using MediaPipe HandLandmarker Tasks,
    computes geometric spatial features, and classifies multi-modal gestures.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        max_num_hands: int = 2,
        min_detection_confidence: float = 0.6,
        min_tracking_confidence: float = 0.6,
        lazy_init: bool = True
    ):
        self.max_num_hands = max_num_hands
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence
        
        if model_path is None:
            model_path = str(Path(__file__).parent / "hand_landmarker.task")
            
        self.model_path = model_path
        self._detector = None
        
        if not lazy_init:
            self._init_detector()

        # History tracking for gestures
        self.prev_scroll_y: Optional[float] = None
        self.prev_two_hand_dist: Optional[float] = None
        self.last_zoom_action_time: float = 0.0
        self.pinch_active: bool = False

    @property
    def detector(self):
        """Lazily initialize MediaPipe HandLandmarker on first use."""
        if self._detector is None:
            self._init_detector()
        return self._detector

    @detector.setter
    def detector(self, value):
        self._detector = value

    def _init_detector(self):
        if self._detector is None and os.path.exists(self.model_path):
            options = vision.HandLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=self.model_path),
                num_hands=self.max_num_hands,
                min_hand_detection_confidence=self.min_detection_confidence,
                min_hand_presence_confidence=self.min_tracking_confidence,
                min_tracking_confidence=self.min_tracking_confidence
            )
            self._detector = vision.HandLandmarker.create_from_options(options)

    def close(self):
        """Release underlying detector resources."""
        if self._detector is not None:
            try:
                self._detector.close()
            except Exception:
                pass
            self._detector = None

    def _distance_2d(self, p1: Dict[str, float], p2: Dict[str, float]) -> float:
        """Euclidean distance between two normalized 2D points."""
        return math.hypot(p1['x'] - p2['x'], p1['y'] - p2['y'])

    def _finger_is_extended(self, landmarks: List[Dict[str, float]], tip_idx: int, pip_idx: int, mcp_idx: int) -> bool:
        """
        Determines if a finger is extended comparing tip distance to wrist vs pip/mcp distance to wrist.
        """
        wrist = landmarks[0]
        tip_dist = self._distance_2d(landmarks[tip_idx], wrist)
        pip_dist = self._distance_2d(landmarks[pip_idx], wrist)
        mcp_dist = self._distance_2d(landmarks[mcp_idx], wrist)
        return (tip_dist > pip_dist) and (tip_dist > mcp_dist)

    def _thumb_is_extended(self, landmarks: List[Dict[str, float]], handedness: str = "Right") -> bool:
        """Determines if thumb is extended based on IP and MCP landmarks."""
        wrist = landmarks[0]
        thumb_tip = landmarks[4]
        thumb_ip = landmarks[3]
        return self._distance_2d(thumb_tip, wrist) > self._distance_2d(thumb_ip, wrist)

    def extract_finger_states(self, landmarks: List[Dict[str, float]], handedness: str = "Right") -> Dict[str, bool]:
        """
        Returns boolean status for each finger: extended (True) or folded (False).
        """
        return {
            "thumb": self._thumb_is_extended(landmarks, handedness),
            "index": self._finger_is_extended(landmarks, 8, 6, 5),
            "middle": self._finger_is_extended(landmarks, 12, 10, 9),
            "ring": self._finger_is_extended(landmarks, 16, 14, 13),
            "pinky": self._finger_is_extended(landmarks, 20, 18, 17)
        }

    def process_frame(self, bgr_frame: np.ndarray) -> Dict[str, Any]:
        """
        Processes a single BGR OpenCV frame, runs HandLandmarker detection,
        extracts normalized coordinates, and classifies gestures.
        """
        h, w, _ = bgr_frame.shape
        detected_hands: List[Dict[str, Any]] = []

        if self.detector is not None:
            rgb_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            detection_result = self.detector.detect(mp_image)

            if detection_result.hand_landmarks:
                for idx, hand_lms in enumerate(detection_result.hand_landmarks):
                    handedness = "Right"
                    if detection_result.handedness and idx < len(detection_result.handedness):
                        if len(detection_result.handedness[idx]) > 0:
                            handedness = detection_result.handedness[idx][0].category_name

                    landmarks_list = []
                    for lm in hand_lms:
                        landmarks_list.append({
                            "x": float(lm.x),
                            "y": float(lm.y),
                            "z": float(lm.z)
                        })

                    finger_states = self.extract_finger_states(landmarks_list, handedness)

                    detected_hands.append({
                        "hand_index": idx,
                        "handedness": handedness,
                        "landmarks": landmarks_list,
                        "finger_states": finger_states
                    })

        return self.classify_gestures(detected_hands, frame_width=w, frame_height=h)

    def classify_gestures(self, detected_hands: List[Dict[str, Any]], frame_width: int, frame_height: int) -> Dict[str, Any]:
        """
        Classifies current active gesture from detected hands.
        Prioritizes:
        1. Two-Hand Zoom (if two hands are present)
        2. Single-Hand Pinch Click
        3. Single-Hand Two-Finger Scroll
        4. Single-Hand Point Move
        5. Neutral / Idle
        """
        gesture = GestureType.NONE
        action_data: Dict[str, Any] = {}
        now = time.time()

        num_hands = len(detected_hands)

        # ----------------------------------------------------
        # 1. TWO-HAND GESTURES: Zoom In / Zoom Out
        # ----------------------------------------------------
        if num_hands >= 2:
            hand1 = detected_hands[0]
            hand2 = detected_hands[1]

            h1_index = hand1["landmarks"][8]
            h2_index = hand2["landmarks"][8]

            current_dist = self._distance_2d(h1_index, h2_index)
            action_data["two_hand_dist"] = current_dist

            if self.prev_two_hand_dist is not None:
                delta_dist = current_dist - self.prev_two_hand_dist
                threshold = 0.035

                if abs(delta_dist) > threshold and (now - self.last_zoom_action_time > 0.28):
                    if delta_dist > 0:
                        gesture = GestureType.TWO_HAND_ZOOM_IN
                        action_data["direction"] = "in"
                    else:
                        gesture = GestureType.TWO_HAND_ZOOM_OUT
                        action_data["direction"] = "out"
                    self.last_zoom_action_time = now
                    self.prev_two_hand_dist = current_dist
            else:
                self.prev_two_hand_dist = current_dist

            return {
                "gesture": gesture,
                "hands_count": num_hands,
                "action_data": action_data,
                "hands": detected_hands
            }
        else:
            self.prev_two_hand_dist = None

        # ----------------------------------------------------
        # 2. SINGLE-HAND GESTURES
        # ----------------------------------------------------
        if num_hands == 1:
            hand = detected_hands[0]
            lm = hand["landmarks"]
            fs = hand["finger_states"]

            thumb_tip = lm[4]
            index_tip = lm[8]
            middle_tip = lm[12]

            pinch_dist = self._distance_2d(thumb_tip, index_tip)
            action_data["pinch_distance"] = pinch_dist

            # PINCH CLICK
            pinch_threshold = 0.055
            if pinch_dist < pinch_threshold:
                gesture = GestureType.PINCH_CLICK
                action_data["x"] = index_tip["x"]
                action_data["y"] = index_tip["y"]
                self.prev_scroll_y = None
                return {
                    "gesture": gesture,
                    "hands_count": 1,
                    "action_data": action_data,
                    "hands": detected_hands
                }

            # SCROLL: Index AND Middle fingers extended, Ring and Pinky folded
            if fs["index"] and fs["middle"] and not fs["ring"] and not fs["pinky"]:
                mid_y = (index_tip["y"] + middle_tip["y"]) / 2.0
                action_data["scroll_y"] = mid_y

                if self.prev_scroll_y is not None:
                    delta_y = mid_y - self.prev_scroll_y
                    scroll_threshold = 0.025
                    if delta_y < -scroll_threshold:
                        gesture = GestureType.SCROLL_UP
                        action_data["delta_y"] = delta_y
                        self.prev_scroll_y = mid_y
                    elif delta_y > scroll_threshold:
                        gesture = GestureType.SCROLL_DOWN
                        action_data["delta_y"] = delta_y
                        self.prev_scroll_y = mid_y
                else:
                    self.prev_scroll_y = mid_y

                return {
                    "gesture": gesture,
                    "hands_count": 1,
                    "action_data": action_data,
                    "hands": detected_hands
                }
            else:
                self.prev_scroll_y = None

            # POINT MOVE: Index extended, Middle, Ring, Pinky folded
            if fs["index"] and not fs["middle"] and not fs["ring"] and not fs["pinky"]:
                gesture = GestureType.POINT_MOVE
                action_data["cursor_norm_x"] = index_tip["x"]
                action_data["cursor_norm_y"] = index_tip["y"]
                return {
                    "gesture": gesture,
                    "hands_count": 1,
                    "action_data": action_data,
                    "hands": detected_hands
                }

            # Neutral states
            if fs["index"] and fs["middle"] and fs["ring"] and fs["pinky"]:
                gesture = GestureType.OPEN_PALM
            elif not fs["index"] and not fs["middle"] and not fs["ring"] and not fs["pinky"]:
                gesture = GestureType.FIST

        return {
            "gesture": gesture,
            "hands_count": num_hands,
            "action_data": action_data,
            "hands": detected_hands
        }

    def draw_hud_landmarks(self, frame: np.ndarray, detected_hands: List[Dict[str, Any]], active_gesture: str):
        """
        Draws high-contrast cyber HUD landmarks and connections on frame.
        """
        h, w, _ = frame.shape

        for hand in detected_hands:
            landmarks = hand.get("landmarks", [])
            if not landmarks:
                continue

            # Draw skeletal lines
            for start_idx, end_idx in HAND_CONNECTIONS:
                p1 = (int(landmarks[start_idx]["x"] * w), int(landmarks[start_idx]["y"] * h))
                p2 = (int(landmarks[end_idx]["x"] * w), int(landmarks[end_idx]["y"] * h))
                cv2.line(frame, p1, p2, (0, 220, 255), 2, cv2.LINE_AA)

            # Draw joint circles
            for idx, lm in enumerate(landmarks):
                px = int(lm["x"] * w)
                py = int(lm["y"] * h)
                color = (0, 255, 128) if idx in (4, 8, 12) else (255, 200, 0)
                radius = 5 if idx in (4, 8, 12) else 3
                cv2.circle(frame, (px, py), radius, color, -1, cv2.LINE_AA)
                cv2.circle(frame, (px, py), radius + 1, (20, 20, 20), 1, cv2.LINE_AA)

        # Draw status overlay banner
        cv2.rectangle(frame, (0, 0), (w, 38), (15, 17, 26), -1)
        gesture_color = (0, 255, 128) if active_gesture != GestureType.NONE else (160, 160, 170)
        cv2.putText(
            frame,
            f"NOVATRIX OS // ACTION: {active_gesture}",
            (14, 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            gesture_color,
            2,
            cv2.LINE_AA
        )
