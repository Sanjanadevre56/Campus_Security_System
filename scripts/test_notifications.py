import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure root directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import create_app
from config import Config
from core.database import init_db, get_db, set_config_value
from core.alert_engine import (
    dispatch_email_alert,
    dispatch_hardware_buzzer,
    trigger_unknown_event_alerts
)
from scripts.test_database import run_test as run_db_test
from scripts.test_registration import run_registration_tests
from scripts.test_camera import run_camera_tests
from scripts.test_recognition import run_recognition_tests

def run_notification_tests():
    print("==========================================================")
    print("  AI-Based Campus Security System - Phase 6 Test Suite    ")
    print("==========================================================")

    init_db()

    # Create dummy unknown_alert record for testing
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO unknown_alerts (snapshot_path, gate_location, status, hardware_mode, esp32_triggered, email_sent)
            VALUES ('unknowns/test_snapshot.jpg', 'Main Campus Gate 1', 'UNRESOLVED', 'VIRTUAL', 0, 0)
        """)
        alert_id = cursor.lastrowid

    # Test 1: Email Disabled Behavior
    print("[*] Test 1: Testing Disabled SMTP Email Alerts...")
    set_config_value("SMTP_ENABLED", "False")
    success, msg = dispatch_email_alert(alert_id, "unknowns/test_snapshot.jpg", "2026-09-26 12:00:00", "Main Gate 1")
    assert success == False
    assert "SMTP Disabled" in msg
    print("    [✓] Disabled SMTP handling verified (no email sent).")

    # Test 2: Incomplete Credentials Handling
    print("[*] Test 2: Testing Incomplete SMTP Credentials Handling...")
    set_config_value("SMTP_ENABLED", "True")
    set_config_value("SMTP_USERNAME", "")
    success, msg = dispatch_email_alert(alert_id, "unknowns/test_snapshot.jpg", "2026-09-26 12:00:00", "Main Gate 1")
    assert success == False
    assert "Incomplete SMTP Credentials" in msg
    print("    [✓] Incomplete credentials handled gracefully.")

    # Test 3: Mocked SMTP Email Dispatch Success
    print("[*] Test 3: Testing Mocked SMTP Success & Database Update...")
    set_config_value("SMTP_ENABLED", "True")
    set_config_value("SMTP_SERVER", "smtp.test.com")
    set_config_value("SMTP_PORT", "587")
    set_config_value("SMTP_USERNAME", "admin@campus.edu")
    set_config_value("SMTP_PASSWORD", "testpass")
    set_config_value("ALERT_RECIPIENT_EMAIL", "recipient@campus.edu")

    with patch("smtplib.SMTP") as mock_smtp_class:
        mock_smtp_instance = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp_instance

        success, msg = dispatch_email_alert(alert_id, "unknowns/test_snapshot.jpg", "2026-09-26 12:00:00", "Main Gate 1")
        assert success == True
        assert msg == "Email Delivered"

        # Verify SMTP interaction
        mock_smtp_instance.starttls.assert_called_once()
        mock_smtp_instance.login.assert_called_once_with("admin@campus.edu", "testpass")
        mock_smtp_instance.send_message.assert_called_once()

        # Verify database record updated email_sent = 1
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT email_sent FROM unknown_alerts WHERE id = ?", (alert_id,))
            assert cursor.fetchone()["email_sent"] == 1
    print("    [✓] Mocked SMTP email dispatch and email_sent = 1 DB update verified.")

    # Test 4: Mocked SMTP Network Exception Handling
    print("[*] Test 4: Testing Mocked SMTP Exception Resiliency...")
    with patch("smtplib.SMTP", side_effect=Exception("Connection timed out")):
        success, msg = dispatch_email_alert(alert_id, "unknowns/test_snapshot.jpg", "2026-09-26 12:00:00", "Main Gate 1")
        assert success == False
        assert "Connection timed out" in msg
    print("    [✓] SMTP network timeout caught gracefully without crashing.")

    # Test 5: Virtual Hardware Mode (Buzzer Simulation)
    print("[*] Test 5: Testing Virtual Hardware Mode Buzzer Simulation...")
    set_config_value("HARDWARE_MODE", "VIRTUAL")
    success, msg = dispatch_hardware_buzzer(alert_id)
    assert success == True
    assert msg == "Virtual Buzzer Activated"

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT mode, event_type FROM hardware_logs ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        assert row["mode"] == "VIRTUAL"
        assert row["event_type"] == "BUZZER_SIMULATED"
    print("    [✓] Virtual buzzer mode recorded simulation in hardware_logs without network call.")

    # Test 6: Physical ESP32 Mode Mock HTTP Success
    print("[*] Test 6: Testing Physical ESP32 Mode Mock HTTP 200 Success...")
    set_config_value("HARDWARE_MODE", "PHYSICAL")
    set_config_value("ESP32_IP", "192.168.1.100")
    set_config_value("ESP32_PORT", "80")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "success", "buzzer": "activated"}

    with patch("requests.post", return_value=mock_response) as mock_post:
        success, msg = dispatch_hardware_buzzer(alert_id)
        assert success == True
        assert msg == "ESP32 Buzzer Triggered"
        
        # Verify HTTP request payload and timeout
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "http://192.168.1.100:80/trigger-buzzer"
        assert kwargs["json"]["alert_id"] == alert_id
        assert kwargs["timeout"] == 1.5

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT mode, event_type FROM hardware_logs ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            assert row["mode"] == "PHYSICAL"
            assert row["event_type"] == "ESP32_BUZZER_TRIGGERED"
    print("    [✓] Mocked physical ESP32 HTTP POST trigger verified.")

    # Test 7: Physical ESP32 Mode Network Timeout/Failure
    print("[*] Test 7: Testing Physical ESP32 Mode Network Timeout Handling...")
    import requests
    with patch("requests.post", side_effect=requests.RequestException("Network timeout")):
        success, msg = dispatch_hardware_buzzer(alert_id)
        assert success == False
        assert "Network timeout" in msg

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT mode, event_type FROM hardware_logs ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            assert row["mode"] == "PHYSICAL"
            assert row["event_type"] == "ESP32_DISCONNECTED"
    print("    [✓] ESP32 network timeout logged safely as ESP32_DISCONNECTED.")

    # Reset Hardware Mode to VIRTUAL for safe local execution
    set_config_value("HARDWARE_MODE", "VIRTUAL")

    # Test 8: Protected Unknown Snapshot Route (Existing File vs Missing File SVG Fallback & Auth)
    print("[*] Test 8: Testing Unknown Snapshot Image Route & SVG Fallback...")
    app = create_app()
    app.config["TESTING"] = True

    # 8a: Unauthenticated access attempt -> MUST redirect to /login
    with app.test_client() as client:
        res_unauth = client.get("/uploads/unknowns/missing_file.jpg")
        assert res_unauth.status_code == 302
        assert "/login" in res_unauth.headers["Location"]
    print("    [✓] Unauthenticated snapshot access correctly redirected to /login.")

    # 8b: Authenticated access with missing snapshot file -> MUST return status 200 with SVG placeholder
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "admin"

        res_missing = client.get("/uploads/unknowns/non_existent_snapshot.jpg")
        assert res_missing.status_code == 200
        assert "image/svg+xml" in res_missing.headers["Content-Type"]
        assert "<svg" in res_missing.get_data(as_text=True)
    print("    [✓] Authenticated missing snapshot correctly served safe inline SVG placeholder.")

    # Test 9: Run Regression Tests for Phases 1–5
    print("----------------------------------------------------------")
    print("[*] Test 9: Executing Phase 1–5 Regression Test Suites...")
    run_db_test()
    run_registration_tests()
    run_camera_tests()
    run_recognition_tests()

    print("----------------------------------------------------------")
    print("[✓] Phase 6 Notification & Dashboard Fix test suite completed successfully!")

if __name__ == "__main__":
    run_notification_tests()
