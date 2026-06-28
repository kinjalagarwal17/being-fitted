from core.Base_exer import BaseExercise

class SquatDetector(BaseExercise):
    DOWN_THRESHOLD = 100   
    UP_THRESHOLD = 160     
    MIN_VISIBILITY = 0.7

    LEFT_HIP = 23
    LEFT_KNEE = 25
    LEFT_ANKLE = 27
    RIGHT_HIP = 24
    RIGHT_KNEE = 26
    RIGHT_ANKLE = 28
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12

    def __init__(self):
        super().__init__()

    def reset(self):
        self.reps = 0
        self.stage = None

    def process(self, landmarks):
        # Default safety fallback payload structure
        fallback_data = {
            "reps": self.reps,
            "knee_angle": 0,
            "back_angle": 0,
            "depth_status": "VISIBILITY LOW"
        }

        try:
            # Calculate geometric joint orientations for both profiles
            left_knee_angle = self.calculate_angle(
                self.get_point(landmarks, self.LEFT_HIP),
                self.get_point(landmarks, self.LEFT_KNEE),
                self.get_point(landmarks, self.LEFT_ANKLE)
            )

            right_knee_angle = self.calculate_angle(
                self.get_point(landmarks, self.RIGHT_HIP),
                self.get_point(landmarks, self.RIGHT_KNEE),
                self.get_point(landmarks, self.RIGHT_ANKLE)
            )

            # Safely query structural tracking reliability thresholds
            left_vis = landmarks[self.LEFT_KNEE].visibility if hasattr(landmarks[self.LEFT_KNEE], 'visibility') else 1.0
            right_vis = landmarks[self.RIGHT_KNEE].visibility if hasattr(landmarks[self.RIGHT_KNEE], 'visibility') else 1.0

            # Isolate cleaner visibility side for perspective measurement
            if left_vis >= right_vis:
                knee_angle = left_knee_angle
                hip_idx, knee_idx, ankle_idx, shoulder_idx = self.LEFT_HIP, self.LEFT_KNEE, self.LEFT_ANKLE, self.LEFT_SHOULDER
            else:
                knee_angle = right_knee_angle
                hip_idx, knee_idx, ankle_idx, shoulder_idx = self.RIGHT_HIP, self.RIGHT_KNEE, self.RIGHT_ANKLE, self.RIGHT_SHOULDER

            # Extract alignment profiles
            back_angle = self.calculate_angle(
                self.get_point(landmarks, shoulder_idx),
                self.get_point(landmarks, hip_idx),
                self.get_point(landmarks, knee_idx)
            )

            # Ensure tracking landmarks meet clarity guidelines before making evaluation updates
            key_landmark_visible = (
                landmarks[hip_idx].visibility >= self.MIN_VISIBILITY and 
                landmarks[knee_idx].visibility >= self.MIN_VISIBILITY and 
                landmarks[ankle_idx].visibility >= self.MIN_VISIBILITY
            )

            if key_landmark_visible:
                if knee_angle < self.DOWN_THRESHOLD:
                    self.stage = "down"
                
                # Baseline standing registration logic fix
                elif knee_angle >= self.UP_THRESHOLD:
                    if self.stage == "down":
                        self.reps += 1
                    self.stage = "up"

            # Fallback handling for text UI state display systems
            if self.stage == "down":
                depth_status = "GOOD DEPTH" if knee_angle <= self.DOWN_THRESHOLD else "TOO HIGH"
            elif self.stage == "up":
                depth_status = "STANDING"
            else:
                depth_status = "READY"

            return {
                "reps": self.reps,
                "knee_angle": int(knee_angle),
                "back_angle": int(back_angle),
                "depth_status": depth_status
            }

        except (IndexError, AttributeError, TypeError):
            # Gracefully handle frames where points disappear from camera tracking field
            return fallback_data
