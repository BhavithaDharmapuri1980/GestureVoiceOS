"""
Unit tests for Gesture Detection & Classification Algorithms
Team Novatrix
"""

import math
import pytest
from backend.app.gesture_engine import GestureEngine, GestureType


def create_mock_hand_landmarks(wrist=(0.5, 0.8), fingers_up=(False, False, False, False, False)):
    """
    Helper to synthesize 21 3D landmarks for hand states.
    fingers_up: (thumb, index, middle, ring, pinky)
    """
    landmarks = [{"x": wrist[0], "y": wrist[1], "z": 0.0}]  # 0: wrist
    
    # Finger specs: (base_x, [(mcp, pip, dip, tip)])
    finger_specs = [
        (0.40, [1, 2, 3, 4]),   # thumb
        (0.45, [5, 6, 7, 8]),   # index
        (0.50, [9, 10, 11, 12]), # middle
        (0.55, [13, 14, 15, 16]),# ring
        (0.60, [17, 18, 19, 20]) # pinky
    ]
    
    # Pre-allocate 21 landmarks
    full_landmarks = [None] * 21
    full_landmarks[0] = {"x": wrist[0], "y": wrist[1], "z": 0.0}
    
    for idx, (base_x, indices) in enumerate(finger_specs):
        is_extended = fingers_up[idx]
        if is_extended:
            # Extended upwards (smaller y = higher up)
            full_landmarks[indices[0]] = {"x": base_x, "y": 0.60, "z": 0.0} # mcp
            full_landmarks[indices[1]] = {"x": base_x, "y": 0.45, "z": 0.0} # pip
            full_landmarks[indices[2]] = {"x": base_x, "y": 0.35, "z": 0.0} # dip
            full_landmarks[indices[3]] = {"x": base_x, "y": 0.20, "z": 0.0} # tip (far from wrist)
        else:
            # Folded into palm
            full_landmarks[indices[0]] = {"x": base_x, "y": 0.60, "z": 0.0}
            full_landmarks[indices[1]] = {"x": base_x, "y": 0.65, "z": 0.0}
            full_landmarks[indices[2]] = {"x": base_x, "y": 0.70, "z": 0.0}
            full_landmarks[indices[3]] = {"x": base_x, "y": 0.75, "z": 0.0} # tip (near wrist)

    return full_landmarks


@pytest.fixture
def engine():
    return GestureEngine(lazy_init=True)


def test_distance_calculation(engine):
    p1 = {"x": 0.1, "y": 0.2}
    p2 = {"x": 0.4, "y": 0.6}
    dist = engine._distance_2d(p1, p2)
    assert pytest.approx(dist, 0.001) == 0.5


def test_point_move_gesture(engine):
    # Index up only
    lm = create_mock_hand_landmarks(fingers_up=(False, True, False, False, False))
    fs = engine.extract_finger_states(lm)
    assert fs["index"] is True
    assert fs["middle"] is False
    assert fs["ring"] is False
    assert fs["pinky"] is False

    detected = [{
        "hand_index": 0,
        "handedness": "Right",
        "landmarks": lm,
        "finger_states": fs
    }]
    res = engine.classify_gestures(detected, 640, 480)
    assert res["gesture"] == GestureType.POINT_MOVE
    assert "cursor_norm_x" in res["action_data"]
    assert "cursor_norm_y" in res["action_data"]


def test_pinch_click_gesture(engine):
    # Place thumb tip and index tip at identical position (pinch)
    lm = create_mock_hand_landmarks(fingers_up=(True, True, False, False, False))
    lm[4] = {"x": 0.42, "y": 0.30, "z": 0.0}  # Thumb tip
    lm[8] = {"x": 0.43, "y": 0.31, "z": 0.0}  # Index tip

    dist = engine._distance_2d(lm[4], lm[8])
    assert dist < 0.05

    fs = engine.extract_finger_states(lm)
    detected = [{
        "hand_index": 0,
        "handedness": "Right",
        "landmarks": lm,
        "finger_states": fs
    }]
    res = engine.classify_gestures(detected, 640, 480)
    assert res["gesture"] == GestureType.PINCH_CLICK


def test_scroll_gestures(engine):
    # Index and middle both extended (wrist at y=0.80, PIP at y=0.45, tip extended at y=0.25)
    lm1 = create_mock_hand_landmarks(fingers_up=(False, True, True, False, False))
    lm1[8]["y"] = 0.25
    lm1[12]["y"] = 0.25

    fs1 = engine.extract_finger_states(lm1)
    assert fs1["index"] is True
    assert fs1["middle"] is True
    detected1 = [{"hand_index": 0, "handedness": "Right", "landmarks": lm1, "finger_states": fs1}]
    # First frame initializes baseline
    res1 = engine.classify_gestures(detected1, 640, 480)
    assert res1["gesture"] == GestureType.NONE

    # Second frame: hand moved upwards (y decreased to 0.15, delta = -0.10)
    lm2 = create_mock_hand_landmarks(fingers_up=(False, True, True, False, False))
    lm2[8]["y"] = 0.15
    lm2[12]["y"] = 0.15
    fs2 = engine.extract_finger_states(lm2)
    detected2 = [{"hand_index": 0, "handedness": "Right", "landmarks": lm2, "finger_states": fs2}]
    res2 = engine.classify_gestures(detected2, 640, 480)
    assert res2["gesture"] == GestureType.SCROLL_UP


def test_two_hand_zoom(engine):
    # Two hands
    hand1_lm = create_mock_hand_landmarks(wrist=(0.3, 0.7), fingers_up=(False, True, False, False, False))
    hand2_lm = create_mock_hand_landmarks(wrist=(0.7, 0.7), fingers_up=(False, True, False, False, False))

    hand1_lm[8] = {"x": 0.35, "y": 0.3, "z": 0.0}
    hand2_lm[8] = {"x": 0.65, "y": 0.3, "z": 0.0}

    detected_frame1 = [
        {"hand_index": 0, "landmarks": hand1_lm, "finger_states": {}},
        {"hand_index": 1, "landmarks": hand2_lm, "finger_states": {}}
    ]
    # Frame 1 initializes two-hand distance
    res1 = engine.classify_gestures(detected_frame1, 640, 480)
    assert res1["hands_count"] == 2

    # Frame 2: Hands spread apart (Zoom IN)
    hand1_spread = create_mock_hand_landmarks(wrist=(0.2, 0.7), fingers_up=(False, True, False, False, False))
    hand2_spread = create_mock_hand_landmarks(wrist=(0.8, 0.7), fingers_up=(False, True, False, False, False))
    hand1_spread[8] = {"x": 0.25, "y": 0.3, "z": 0.0}
    hand2_spread[8] = {"x": 0.75, "y": 0.3, "z": 0.0}

    detected_frame2 = [
        {"hand_index": 0, "landmarks": hand1_spread, "finger_states": {}},
        {"hand_index": 1, "landmarks": hand2_spread, "finger_states": {}}
    ]
    res2 = engine.classify_gestures(detected_frame2, 640, 480)
    assert res2["gesture"] == GestureType.TWO_HAND_ZOOM_IN
