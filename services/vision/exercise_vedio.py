import os
import cv2
import av
import numpy as np
import mediapipe as mp
import threading
from streamlit_webrtc import VideoProcessorBase
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from detectors.squad import SquatDetector
from detectors.push_up import PushUpDetector
from detectors.biceps import BicepsCurlDetector
from detectors.shoulders import ShoulderPressDetector
from detectors.lunges import LungesDetector

# Use MediaPipe's standard connections matrix
POSE_CONNECTIONS = mp.solutions.pose.POSE_CONNECTIONS

class VideoProcessorClass(VideoProcessorBase):
    def __init__(self):
        self._lock = threading.Lock()
        self._latest_metrics = None
        self._exercise_type = "Squats"

        # --- ABSOLUTE PATH CALCULATION ---
        current_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(current_dir, "..", "..", "ml_models", "pose_landmarker_full.task")
        model_path = os.path.normpath(model_path)

        if not os.path.exists(model_path):
            ml_folder = os.path.join(current_dir, "..", "..", "ml_models")
            contents = os.listdir(ml_folder) if os.path.exists(ml_folder) else "Folder does not exist"
            raise FileNotFoundError(
                f"Model file not found at: {model_path}\n"
                f"Contents of {ml_folder}: {contents}"
            )

        base_option = python.BaseOptions(model_asset_path=model_path)
        options = vision.PoseLandmarkerOptions(
            base_options=base_option,
            running_mode=vision.RunningMode.VIDEO,
            min_pose_detection_confidence=0.7,
            min_pose_presence_confidence=0.7,
            min_tracking_confidence=0.7,
            output_segmentation_masks=False
        )

        self._landmarker = vision.PoseLandmarker.create_from_options(options)

        self._detectors = {
            "Squats": SquatDetector(),
            "Push-ups": PushUpDetector(),
            "Biceps Curls (Dumbbell)": BicepsCurlDetector(),
            "Shoulder Press": ShoulderPressDetector(),
            "Lunges": LungesDetector(),
        }

        self._frame_timestamps_ms = 0
    
    def set_latest_metrics(self, metrics):
        with self._lock:
            self._latest_metrics = metrics.copy()

    def get_latest_metrics(self):
        with self._lock:
            return None if self._latest_metrics is None else self._latest_metrics.copy()
        
    def set_exercise(self, exercise_type):
        with self._lock:
            self._exercise_type = exercise_type

    def get_exercise(self):
        with self._lock:
            return self._exercise_type
        
    def _draw_skeleton(self, img, landmarks):
        h, w = img.shape[:2]
        # Draw skeleton connections lines securely
        for start_idx, end_idx in POSE_CONNECTIONS:
            if start_idx < len(landmarks) and end_idx < len(landmarks):
                p1, p2 = landmarks[start_idx], landmarks[end_idx]
                if p1.visibility > 0.5 and p2.visibility > 0.5:
                    cv2.line(img, (int(p1.x * w), int(p1.y * h)), (int(p2.x * w), int(p2.y * h)), (0, 255, 0), 3)
        
        # Draw key joint track points
        for lm in landmarks:
            if lm.visibility > 0.5:
                cv2.circle(img, (int(lm.x * w), int(lm.y * h)), 5, (255, 0, 0), -1)
            
    def _draw_no_pose_warnings(self, img):
        cv2.putText(img, "NO POSE DETECTED", (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)
        cv2.putText(img, "PLEASE FACE THE CAMERA", (30, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)

    def _draw_overlays(self, img, metrics, ex_type):
        if ex_type == "Squats": self._draw_squats_overlays(img, metrics)
        elif ex_type == "Push-ups": self._draw_pushup_overlays(img, metrics)
        elif ex_type == "Biceps Curls (Dumbbell)": self._draw_curl_overlays(img, metrics)
        elif ex_type == "Shoulder Press": self._draw_press_overlays(img, metrics)
        elif ex_type == "Lunges": self._draw_lunge_overlays(img, metrics)

    def _draw_squats_overlays(self, img, metrics):
        h, _ = img.shape[:2]
        cv2.putText(img, f"DEPTH: {metrics.get('depth_status', 'N/A')}", (20, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    
    def _draw_pushup_overlays(self, img, metrics):
        h, _ = img.shape[:2]
        cv2.putText(img, f"BODY: {metrics.get('body_alignment', 'N/A')} | HIP: {metrics.get('hip_status', 'N/A')}", (20, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    def _draw_curl_overlays(self, img, metrics):
        h, _ = img.shape[:2]
        cv2.putText(img, f"SWING: {metrics.get('swing_status', 'N/A')}", (20, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    def _draw_press_overlays(self, img, metrics):
        h, _ = img.shape[:2]
        cv2.putText(img, f"EXT: {metrics.get('extension_status', 'N/A')} | BACK: {metrics.get('back_arch_status', 'N/A')}", (20, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    def _draw_lunge_overlays(self, img, metrics):
        h, _ = img.shape[:2]
        cv2.putText(img, f"BALANCE: {metrics.get('balance_status', 'N/A')}", (20, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    def recv(self, frame):
        try:
            # 1. Capture incoming video frame configuration array
            image = np.asarray(cv2.flip(frame.to_ndarray(format="bgr24"), 1), dtype=np.uint8)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            
            # 2. Advance timestamp tracking loop for video stream calculations
            self._frame_timestamps_ms += 33
            result = self._landmarker.detect_for_video(mp_image, self._frame_timestamps_ms)

            # 3. Securely check inside the result instance array wrapper layout
            if result and hasattr(result, 'pose_landmarks') and result.pose_landmarks and len(result.pose_landmarks) > 0:
                # FIXED: Extracting the inner list explicitly using index [0] to match drawing utilities
                landmarks = result.pose_landmarks[0]
                
                # 4. Render overlay data matrices onto the canvas screen
                self._draw_skeleton(image, landmarks)
                ex_type = self.get_exercise()
                detector = self._detectors.get(ex_type)
                
                if detector:
                    metrics = detector.process(landmarks)
                    metrics["pose_detected"] = True
                    self._draw_overlays(image, metrics, ex_type)
                    self.set_latest_metrics(metrics)
            else:
                # Fallback template to clear state variables cleanly across both processing loops
                self._draw_no_pose_warnings(image)
                empty_metrics = {
                    "pose_detected": False,
                    "knee_angle": 0, "back_angle": 0, "depth_status": "No pose detected",
                    "elbow_angle": 0, "body_alignment": "N/A", "hip_status": "N/A",
                    "shoulder_status": "N/A", "swing_status": "N/A",
                    "extension_status": "N/A", "back_arch_status": "N/A",
                    "front_knee_angle": 0, "torso_angle": 0, "balance_status": "N/A"
                }
                self.set_latest_metrics(empty_metrics)
                
        except Exception as e:
            # Prevent background processing errors from freezing the layout view stream
            print(f"Tracking thread processing exception error: {e}")
            pass

        return av.VideoFrame.from_ndarray(image, format="bgr24")
