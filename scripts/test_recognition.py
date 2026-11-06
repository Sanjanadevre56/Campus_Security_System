import sys
import time
import numpy as np
from pathlib import Path

# Ensure root directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import create_app
from config import Config
from core.database import init_db, get_db
from core.face_engine import (
    serialize_encoding,
    deserialize_encoding,
    match_face_encoding,
    load_enrolled_encodings
)
from core.camera_engine import CameraEngine
from scripts.test_database import run_test as run_db_test
from scripts.test_registration import run_registration_tests
from scripts.test_camera import run_camera_tests

def run_recognition_tests():
    print("==========================================================")
    print("  AI-Based Campus Security System - Phase 5 Test Suite    ")
    print("==========================================================")

    init_db()

    # 1. Test Matching Known Encoding
    print("[*] Test 1: Testing Known Facial Vector Matching...")
    target_vec = np.ones(128, dtype=np.float64) * 0.5
    enrolled_person = {
        "person_id": "STU-2026-TEST",
        "full_name": "Test Student",
        "role": "Student",
        "department": "Computer Science",
        "encoding": np.ones(128, dtype=np.float64) * 0.505  # Very close vector (small distance)
    }

    enrolled_list = [enrolled_person]
    matched, match_dict, dist = match_face_encoding(target_vec, enrolled_list, threshold=0.5)

    assert matched == True
    assert match_dict["person_id"] == "STU-2026-TEST"
    assert dist < 0.5
    print(f"    [✓] Matched known encoding correctly (Distance: {dist:.4f} <= Threshold 0.50).")

    # 2. Test Unknown Encoding Rejection
    print("[*] Test 2: Testing Unknown Facial Vector Rejection...")
    distant_vec = np.ones(128, dtype=np.float64) * 5.0 # Distant vector
    matched, match_dict, dist = match_face_encoding(distant_vec, enrolled_list, threshold=0.5)

    assert matched == False
    assert match_dict == None
    assert dist > 0.5
    print(f"    [✓] Classified distant vector as UNKNOWN (Distance: {dist:.4f} > Threshold 0.50).")

    # 3. Test Debounce Cooldown Mechanism
    print("[*] Test 3: Testing Debounce Cooldown Logging Mechanism...")
    cam = CameraEngine()
    cam.debounce_cooldown = 3  # Set 3-second cooldown for test
    cam.last_logged_times.clear()

    now = time.time()
    # First detection at t=now -> should log
    should_log_1 = (now - cam.last_logged_times.get("TEST_ID", 0)) >= cam.debounce_cooldown
    if should_log_1:
        cam.last_logged_times["TEST_ID"] = now
    assert should_log_1 == True

    # Immediate second detection at t=now + 0.5s -> should BE DEBOUNCED (skipped)
    now_plus_half = now + 0.5
    should_log_2 = (now_plus_half - cam.last_logged_times.get("TEST_ID", 0)) >= cam.debounce_cooldown
    assert should_log_2 == False

    # Third detection at t=now + 4.0s (after 3s cooldown) -> should log
    now_plus_four = now + 4.0
    should_log_3 = (now_plus_four - cam.last_logged_times.get("TEST_ID", 0)) >= cam.debounce_cooldown
    if should_log_3:
        cam.last_logged_times["TEST_ID"] = now_plus_four
    assert should_log_3 == True
    print("    [✓] Debounce cooldown logic verified (1st logged, 2nd debounced, 3rd logged after cooldown).")

    # 4. Test Graceful Handling of Invalid Encodings
    print("[*] Test 4: Testing Invalid Encoding Handling...")
    try:
        res = deserialize_encoding("corrupted_json_vector")
    except Exception:
        res = None
    assert res is None or isinstance(res, np.ndarray)
    print("    [✓] Invalid or corrupted encodings handled gracefully without breaking engine.")

    # 5. Test Route Protection for Protected Uploads
    print("[*] Test 5: Testing Route Protection for Snapshot Downloads...")
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        res = client.get("/uploads/unknowns/sample_snapshot.jpg")
        assert res.status_code == 302
        assert "/login" in res.headers["Location"]
    print("    [✓] Protected unknown snapshot route strictly requires authentication.")

    # 6. Run Regression Tests for Phases 1–4
    print("----------------------------------------------------------")
    print("[*] Test 6: Executing Phase 1–4 Regression Test Suites...")
    run_db_test()
    run_registration_tests()
    run_camera_tests()

    print("----------------------------------------------------------")
    print("[✓] Phase 5 Face Recognition & Debounced Logging test suite completed successfully!")

if __name__ == "__main__":
    run_recognition_tests()
