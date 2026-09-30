import cv2
import mediapipe as mp
import numpy as np
import os
import sys
from collections import deque


def _default_hand_landmarker_delegate():
    """GPU delegate on macOS often aborts with unsupported ImageFrame format for webcam RGB."""
    if os.environ.get("MEDIAPIPE_FORCE_GPU", "").strip() in ("1", "true", "yes"):
        return mp.tasks.BaseOptions.Delegate.GPU
    if sys.platform == "darwin":
        return mp.tasks.BaseOptions.Delegate.CPU
    return mp.tasks.BaseOptions.Delegate.GPU

BaseOptions = mp.tasks.BaseOptions
HandLandmarker = mp.tasks.vision.HandLandmarker
HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
RunningMode = mp.tasks.vision.RunningMode
HandConnections = mp.tasks.vision.HandLandmarksConnections
draw_landmarks = mp.tasks.vision.drawing_utils.draw_landmarks


class HandTracker:
    WRIST = 0
    THUMB_TIP = 4
    INDEX_TIP = 8
    MIDDLE_TIP = 12
    RING_TIP = 16
    PINKY_TIP = 20
    INDEX_MCP = 5
    PINKY_MCP = 17

    def __init__(self, smoothing_window=5, min_detection_confidence=0.7, min_tracking_confidence=0.6):
        model_path = os.path.join(os.path.dirname(__file__), "hand_landmarker.task")

        delegate = _default_hand_landmarker_delegate()
        options = HandLandmarkerOptions(
            base_options=BaseOptions(
                model_asset_path=model_path,
                delegate=delegate,
            ),
            running_mode=RunningMode.VIDEO,
            num_hands=1,
            min_hand_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        try:
            self.landmarker = HandLandmarker.create_from_options(options)
        except RuntimeError:
            options.base_options.delegate = BaseOptions.Delegate.CPU
            self.landmarker = HandLandmarker.create_from_options(options)
        self._openness_history = deque(maxlen=smoothing_window)
        self.hand_detected = False
        self._frame_timestamp = 0

    def process_frame(self, frame):
        """Process a BGR frame and return (annotated_frame, openness).
        openness: 0.0 = fist, 1.0 = fully open, None = no hand

        NOTE (Arduino repo uses cvzone HandDetector.fingersUp() which returns
        a 5-element binary list [thumb, index, middle, ring, pinky].
        We use continuous openness (0.0–1.0) instead — better for proportional
        servo control. A fingersUp()-style discrete mode could be added as an
        alternative if distinct finger gestures are needed later.)
        """
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # Contiguous uint8 buffer avoids edge cases with GPU/Metal and OpenCV views.
        rgb = np.ascontiguousarray(rgb)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        self._frame_timestamp += 33  # ~30fps in ms
        result = self.landmarker.detect_for_video(mp_image, self._frame_timestamp)

        self.hand_detected = False

        if result.hand_landmarks and len(result.hand_landmarks) > 0:
            hand = result.hand_landmarks[0]
            self.hand_detected = True

            self._draw_hand(frame, hand)

            h, w = frame.shape[:2]
            openness = self._calculate_openness(hand, w, h)
            self._openness_history.append(openness)

            smoothed = np.mean(self._openness_history)
            return frame, smoothed

        return frame, None

    def _draw_hand(self, frame, landmarks):
        """Draw hand landmarks and connections on the frame."""
        h, w = frame.shape[:2]
        connections = HandConnections.HAND_CONNECTIONS

        points = []
        for lm in landmarks:
            px, py = int(lm.x * w), int(lm.y * h)
            points.append((px, py))
            cv2.circle(frame, (px, py), 4, (0, 255, 0), -1)

        for conn in connections:
            start, end = conn.start, conn.end
            cv2.line(frame, points[start], points[end], (0, 200, 0), 2)

    def _calculate_openness(self, hand, w, h):
        """Calculate how open the hand is (0.0=fist, 1.0=open).
        Uses average distance of all fingertips to wrist,
        normalized by palm size.
        """
        def pt(idx):
            return np.array([hand[idx].x * w, hand[idx].y * h])

        wrist = pt(self.WRIST)
        index_mcp = pt(self.INDEX_MCP)
        pinky_mcp = pt(self.PINKY_MCP)

        palm_size = np.linalg.norm(index_mcp - pinky_mcp)
        if palm_size < 1:
            return 0.5

        tips = [self.THUMB_TIP, self.INDEX_TIP, self.MIDDLE_TIP, self.RING_TIP, self.PINKY_TIP]
        distances = [np.linalg.norm(pt(t) - wrist) for t in tips]

        avg_dist = np.mean(distances)
        openness = (avg_dist / palm_size - 1.5) / (2.8 - 1.5)
        return float(np.clip(openness, 0.0, 1.0))

    def openness_to_angle(self, openness, open_angle=10, close_angle=170):
        """Map hand openness (0-1) to servo angle.
        Open hand (1.0) -> open_angle (gripper open)
        Closed fist (0.0) -> close_angle (gripper closed)
        """
        if openness is None:
            return None
        return int(open_angle + (close_angle - open_angle) * openness)

    def release(self):
        """Release MediaPipe resources."""
        self.landmarker.close()
