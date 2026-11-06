import os
import time
import uuid
import threading
from pathlib import Path
import cv2
import numpy as np
import face_recognition

from config import Config
from core.database import get_db, get_config_value
from core.face_engine import load_enrolled_encodings, match_face_encoding

class CameraEngine:
    """
    Thread-safe OpenCV Camera Engine for live streaming, real-time face recognition,
    and debounced entrance event logging.
    """
    def __init__(self, camera_index=None):
        self.camera_index = camera_index if camera_index is not None else Config.CAMERA_INDEX
        self.cap = None
        self.is_running = False
        self.lock = threading.Lock()
        
        # Enrolled encodings cache and debounce state
        self.enrolled_cache = []
        self.last_logged_times = {}
        self.face_threshold = Config.FACE_MATCH_THRESHOLD
        self.debounce_cooldown = Config.DEBOUNCE_COOLDOWN_SECONDS

        # Fallback Haar Cascade detector for fast location detection
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)

    def reload_enrolled_cache(self):
        """Reload enrolled facial vector encodings and dynamic system parameters from SQLite."""
        self.enrolled_cache = load_enrolled_encodings()
        try:
            thresh_str = get_config_value("FACE_MATCH_THRESHOLD", str(Config.FACE_MATCH_THRESHOLD))
            self.face_threshold = float(thresh_str)
            cooldown_str = get_config_value("DEBOUNCE_COOLDOWN_SECONDS", str(Config.DEBOUNCE_COOLDOWN_SECONDS))
            self.debounce_cooldown = int(cooldown_str)
        except Exception:
            self.face_threshold = Config.FACE_MATCH_THRESHOLD
            self.debounce_cooldown = Config.DEBOUNCE_COOLDOWN_SECONDS
        print(f"[CAMERA ENGINE] Loaded {len(self.enrolled_cache)} enrolled encodings (Threshold: {self.face_threshold}, Cooldown: {self.debounce_cooldown}s)")

    def start(self, camera_index=None) -> tuple[bool, str]:
        """Explicitly open and start the OpenCV webcam video stream with recognition enabled."""
        with self.lock:
            if self.is_running and self.cap is not None and self.cap.isOpened():
                return True, "Camera is already running."

            target_index = camera_index if camera_index is not None else self.camera_index

            try:
                # Reload enrolled face encodings from SQLite
                self.reload_enrolled_cache()
                self.last_logged_times.clear()

                # Use CAP_DSHOW on Windows if available for faster device binding
                self.cap = cv2.VideoCapture(target_index, cv2.CAP_DSHOW) if hasattr(cv2, 'CAP_DSHOW') else cv2.VideoCapture(target_index)

                if not self.cap.isOpened():
                    self.cap = cv2.VideoCapture(target_index)

                if not self.cap.isOpened():
                    self.is_running = False
                    self.cap = None
                    return False, f"Unable to access camera device at index {target_index}. Please verify webcam connection."

                # Configure optimal stream dimensions
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

                self.is_running = True
                self.camera_index = target_index
                return True, "Camera recognition stream started successfully."

            except Exception as e:
                self.is_running = False
                self.cap = None
                return False, f"Failed to initialize camera recognition engine: {str(e)}"

    def stop(self):
        """Safely stop the video stream and release hardware camera resources."""
        with self.lock:
            self.is_running = False
            if self.cap is not None:
                try:
                    self.cap.release()
                except Exception as e:
                    print(f"[WARN] Error releasing camera: {e}")
                finally:
                    self.cap = None
            return True, "Camera video stream stopped."

    def get_frame(self) -> tuple[bool, np.ndarray | None]:
        """Read a single raw frame from the active camera stream."""
        with self.lock:
            if not self.is_running or self.cap is None or not self.cap.isOpened():
                return False, None
            
            ret, frame = self.cap.read()
            if not ret or frame is None:
                return False, None
            return True, frame

    def process_and_draw_faces(self, frame: np.ndarray) -> tuple[np.ndarray, int]:
        """
        Detect faces in frame, extract 128-d encodings, match against enrolled database,
        render identity bounding boxes, and log debounced events into SQLite.
        """
        if frame is None:
            return frame, 0

        h_frame, w_frame = frame.shape[:2]

        # Convert BGR frame to RGB for face_recognition library
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Detect face bounding box locations
        # Convert Haar Cascade locations to (top, right, bottom, left) format for fast execution
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        haar_faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40))

        face_locations = []
        for (x, y, w, h) in haar_faces:
            face_locations.append((y, x + w, y + h, x))

        face_count = len(face_locations)
        now = time.time()

        if face_count > 0:
            # Extract 128-d facial encodings for detected face bounding boxes
            try:
                encodings = face_recognition.face_encodings(rgb_frame, known_face_locations=face_locations)
            except Exception as e:
                print(f"[WARN] Face encoding extraction error: {e}")
                encodings = []

            for i, (top, right, bottom, left) in enumerate(face_locations):
                encoding = encodings[i] if i < len(encodings) else None
                
                matched = False
                matched_person = None
                distance = 1.0

                if encoding is not None and len(encoding) == 128:
                    matched, matched_person, distance = match_face_encoding(
                        encoding, self.enrolled_cache, self.face_threshold
                    )

                if matched and matched_person:
                    # KNOWN PERSON MATCHED
                    person_id = matched_person["person_id"]
                    full_name = matched_person["full_name"]
                    role = matched_person["role"]

                    # Draw Cyan/Green bounding box (BGR: 128, 255, 0)
                    box_color = (128, 255, 0)
                    cv2.rectangle(frame, (left, top), (right, bottom), box_color, 2)

                    # Label box
                    label = f"MATCH: {full_name} ({person_id})"
                    dist_text = f"Dist: {distance:.2f} | Role: {role}"

                    # Background box for label text readability
                    cv2.rectangle(frame, (left, max(top - 36, 0)), (right, top), box_color, -1)
                    cv2.putText(frame, label, (left + 4, max(top - 20, 12)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
                    cv2.putText(frame, dist_text, (left + 4, max(top - 6, 22)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (20, 20, 20), 1, cv2.LINE_AA)

                    # Debounced Known Entry Logging
                    last_time = self.last_logged_times.get(person_id, 0)
                    if now - last_time >= self.debounce_cooldown:
                        self.last_logged_times[person_id] = now
                        self._log_known_entry(person_id, distance)

                else:
                    # UNKNOWN PERSON (NO ENROLLED MATCH FOUND)
                    # Draw Amber/Orange bounding box (BGR: 0, 165, 255)
                    box_color = (0, 165, 255)
                    cv2.rectangle(frame, (left, top), (right, bottom), box_color, 2)

                    label = "UNKNOWN (No Enrolled Match)"
                    dist_text = f"Dist: {distance:.2f}"

                    cv2.rectangle(frame, (left, max(top - 36, 0)), (right, top), box_color, -1)
                    cv2.putText(frame, label, (left + 4, max(top - 20, 12)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
                    cv2.putText(frame, dist_text, (left + 4, max(top - 6, 22)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (20, 20, 20), 1, cv2.LINE_AA)

                    # Debounced Unknown Alert & Snapshot Logging
                    last_time = self.last_logged_times.get("UNKNOWN", 0)
                    if now - last_time >= self.debounce_cooldown:
                        self.last_logged_times["UNKNOWN"] = now
                        
                        # Crop face with margin
                        pad_h = int((bottom - top) * 0.3)
                        pad_w = int((right - left) * 0.3)
                        crop_y1 = max(0, top - pad_h)
                        crop_y2 = min(h_frame, bottom + pad_h)
                        crop_x1 = max(0, left - pad_w)
                        crop_x2 = min(w_frame, right + pad_w)

                        face_crop = frame[crop_y1:crop_y2, crop_x1:crop_x2]
                        if face_crop.size > 0:
                            snapshot_rel_path = self._save_unknown_snapshot(face_crop)
                            if snapshot_rel_path:
                                self._log_unknown_alert(snapshot_rel_path)

        # Top overlay status header banner
        banner_color = (25, 25, 25) # Dark background
        cv2.rectangle(frame, (0, 0), (frame.shape[1], 36), banner_color, -1)

        status_text = f"LIVE MONITOR | Enrolled Encodings: {len(self.enrolled_cache)} | Mode: REAL-TIME RECOGNITION"
        cv2.putText(frame, status_text, (10, 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1, cv2.LINE_AA)

        return frame, face_count

    def generate_mjpeg_stream(self):
        """Generator yielding MJPEG multipart image frame stream for browser rendering."""
        while self.is_running:
            success, frame = self.get_frame()
            if not success or frame is None:
                placeholder = self._create_offline_frame("Camera Stream Paused or Unavailable")
                _, jpeg_bytes = cv2.imencode('.jpg', placeholder)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg_bytes.tobytes() + b'\r\n')
                time.sleep(0.5)
                continue

            # Process frame with face recognition and debounced event logging
            processed_frame, _ = self.process_and_draw_faces(frame)

            # Encode frame to JPEG
            ret, buffer = cv2.imencode('.jpg', processed_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not ret:
                continue

            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            time.sleep(0.033)

    def _save_unknown_snapshot(self, face_crop: np.ndarray) -> str | None:
        """Save a cropped snapshot of an unknown face detection to unknowns upload directory."""
        try:
            timestamp_str = time.strftime("%Y%m%d_%H%M%S")
            filename = f"unknown_{timestamp_str}_{uuid.uuid4().hex[:6]}.jpg"
            save_path = Path(Config.UNKNOWN_UPLOADS_DIR) / filename
            
            cv2.imwrite(str(save_path), face_crop)
            return f"unknowns/{filename}"
        except Exception as e:
            print(f"[ERROR] Failed to save unknown face snapshot: {e}")
            return None

    def _log_known_entry(self, person_id: str, distance: float):
        """Thread-safe recording of a recognized entry event into SQLite entry_logs."""
        try:
            confidence_score = round(float(distance), 3)
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO entry_logs (person_id, confidence_score, gate_location)
                    VALUES (?, ?, 'Main Campus Gate 1')
                """, (person_id, confidence_score))
            print(f"[RECOGNITION LOG] Recorded entrance log for '{person_id}' (Match Distance: {distance:.2f})")
        except Exception as e:
            print(f"[ERROR] Database error logging known entry for {person_id}: {e}")

    def _log_unknown_alert(self, snapshot_path: str):
        """Thread-safe recording of an unknown intruder detection event into SQLite unknown_alerts."""
        try:
            hardware_mode = get_config_value("HARDWARE_MODE", "VIRTUAL")
            timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S")
            alert_id = None

            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO unknown_alerts (snapshot_path, gate_location, status, hardware_mode, esp32_triggered, email_sent)
                    VALUES (?, 'Main Campus Gate 1', 'UNRESOLVED', ?, 0, 0)
                """, (snapshot_path, hardware_mode))
                alert_id = cursor.lastrowid

            print(f"[RECOGNITION LOG] Recorded unknown alert #{alert_id} snapshot: {snapshot_path}")

            if alert_id:
                # Dispatch async email alert and hardware buzzer trigger (runs off main camera thread)
                from core.alert_engine import trigger_unknown_event_alerts
                trigger_unknown_event_alerts(alert_id, snapshot_path, timestamp_str, "Main Campus Gate 1")

        except Exception as e:
            print(f"[ERROR] Database error logging unknown alert: {e}")

    def _create_offline_frame(self, message: str) -> np.ndarray:
        """Create a dark styled placeholder frame when camera is offline."""
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        img[:] = (25, 17, 11)
        
        cv2.putText(img, "SECURITY CAMERA FEED OFFLINE", (140, 220),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2, cv2.LINE_AA)
        cv2.putText(img, message, (160, 260),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1, cv2.LINE_AA)
        return img

# Global singleton camera engine instance
camera_engine = CameraEngine()
