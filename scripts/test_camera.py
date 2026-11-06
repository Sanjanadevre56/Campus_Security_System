import sys
import unittest
from pathlib import Path
import numpy as np
from unittest.mock import MagicMock

# Ensure root directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import create_app
from core.camera_engine import CameraEngine
from scripts.test_database import run_test as run_db_test
from scripts.test_registration import run_registration_tests

def run_camera_tests():
    print("==========================================================")
    print("  AI-Based Campus Security System - Phase 4 Test Suite    ")
    print("==========================================================")

    # 1. Test Camera Engine Initialization
    print("[*] Test 1: Verifying CameraEngine Manager Initialization...")
    cam = CameraEngine(camera_index=0)
    assert cam.is_running == False
    assert cam.cap == None
    print("    [✓] CameraEngine initial state verified (stopped, cap=None).")

    # 2. Test Camera Unavailable Handling (Non-existent device index 9999)
    print("[*] Test 2: Testing Unavailable Camera Device Graceful Failure...")
    success, msg = cam.start(camera_index=9999)
    assert success == False
    assert cam.is_running == False
    assert "Unable to access camera device" in msg or "Failed" in msg
    print(f"    [✓] Caught unavailable camera gracefully: '{msg}'")

    # 3. Test Camera Stop & Resource Release Logic
    print("[*] Test 3: Verifying Stop & Release Logic with Mocked Cap...")
    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = True
    cam.cap = mock_cap
    cam.is_running = True

    stop_success, stop_msg = cam.stop()
    assert stop_success == True
    assert cam.is_running == False
    assert cam.cap == None
    mock_cap.release.assert_called_once()
    print("    [✓] Stop and resource release logic verified.")

    # 4. Test Face Detection Overlay Helper on Blank Synthetic Frame
    print("[*] Test 4: Testing OpenCV Face Detection Helper on Synthetic Frame...")
    blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    processed_frame, detected_count = cam.process_and_draw_faces(blank_frame)

    assert processed_frame is not None
    assert processed_frame.shape == (480, 640, 3)
    assert detected_count == 0
    print("    [✓] Face detection helper executed cleanly (0 faces detected on blank frame).")

    # 5. Test Camera Route Authentication Protection
    print("[*] Test 5: Testing Flask Camera Route Authentication Protection...")
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        # GET /camera
        res_page = client.get("/camera")
        assert res_page.status_code == 302
        assert "/login" in res_page.headers["Location"]

        # GET /camera/video_feed
        res_feed = client.get("/camera/video_feed")
        assert res_feed.status_code == 302
        assert "/login" in res_feed.headers["Location"]

        # POST /camera/start
        res_start = client.post("/camera/start")
        assert res_start.status_code == 302
        assert "/login" in res_start.headers["Location"]

        # POST /camera/stop
        res_stop = client.post("/camera/stop")
        assert res_stop.status_code == 302
        assert "/login" in res_stop.headers["Location"]
    print("    [✓] All camera routes strictly protected by @login_required decorator.")

    # 6. Run Previous Test Suites (Regression Check)
    print("----------------------------------------------------------")
    print("[*] Test 6: Running Database & Registration Regression Tests...")
    run_db_test()
    run_registration_tests()

    print("----------------------------------------------------------")
    print("[✓] Phase 4 Camera Engine & Route test suite completed successfully!")

if __name__ == "__main__":
    run_camera_tests()
