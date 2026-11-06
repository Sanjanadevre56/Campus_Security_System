import os
import smtplib
import threading
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from pathlib import Path

from config import Config
from core.database import get_db, get_config_value

def dispatch_email_alert(alert_id: int, snapshot_path: str, timestamp_str: str, location: str):
    """
    Send an HTML email notification for a newly logged unknown intruder alert using Python smtplib.
    Runs safely in a background worker thread.
    """
    try:
        smtp_enabled = get_config_value("SMTP_ENABLED", str(Config.SMTP_ENABLED)).lower() in ("true", "1", "yes")
        if not smtp_enabled:
            print(f"[ALERT ENGINE] SMTP email alerts disabled in system configuration.")
            return False, "SMTP Disabled"

        smtp_server = get_config_value("SMTP_SERVER", Config.SMTP_SERVER)
        smtp_port = int(get_config_value("SMTP_PORT", str(Config.SMTP_PORT)))
        smtp_user = get_config_value("SMTP_USERNAME", Config.SMTP_USERNAME)
        smtp_pass = get_config_value("SMTP_PASSWORD", Config.SMTP_PASSWORD)
        recipient = get_config_value("ALERT_RECIPIENT_EMAIL", Config.ALERT_RECIPIENT_EMAIL)

        if not smtp_server or not smtp_user or not smtp_pass or not recipient:
            print("[ALERT ENGINE] Incomplete SMTP credentials. Skipping email dispatch.")
            return False, "Incomplete SMTP Credentials"

        # Create multipart HTML message
        msg = MIMEMultipart()
        msg["From"] = smtp_user
        msg["To"] = recipient
        msg["Subject"] = f"🚨 [CAMPUS SECURITY ALERT] Unknown Person Detected - Event #{alert_id}"

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #0b0f19; color: #f3f4f6; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: #111827; border: 1px solid #ef4444; border-radius: 10px; padding: 25px;">
                <h2 style="color: #ef4444; margin-top: 0;">⚠️ Security Intruder Alert</h2>
                <p>An unregistered/unknown person has been detected at the campus entrance monitor.</p>
                <hr style="border-color: #374151;">
                <table style="width: 100%; color: #f3f4f6; font-size: 14px;">
                    <tr><td><strong>Event ID:</strong></td><td>#{alert_id}</td></tr>
                    <tr><td><strong>Location:</strong></td><td>{location}</td></tr>
                    <tr><td><strong>Timestamp:</strong></td><td>{timestamp_str}</td></tr>
                    <tr><td><strong>Status:</strong></td><td><span style="color: #fca5a5;">UNRESOLVED</span></td></tr>
                </table>
                <hr style="border-color: #374151;">
                <p style="font-size: 12px; color: #9ca3af;">AI-Based Campus Security System | Automated Control Center Notification</p>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(html_body, "html"))

        # Attach snapshot image if present
        if snapshot_path:
            full_img_path = Config.BASE_DIR / "static" / snapshot_path
            if full_img_path.exists():
                with open(full_img_path, "rb") as img_file:
                    img_data = img_file.read()
                    image_attachment = MIMEImage(img_data)
                    image_attachment.add_header("Content-Disposition", "attachment", filename=os.path.basename(snapshot_path))
                    msg.attach(image_attachment)

        # Connect to SMTP server and deliver message
        with smtplib.SMTP(smtp_server, smtp_port, timeout=5.0) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        # Update database alert record
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE unknown_alerts SET email_sent = 1 WHERE id = ?", (alert_id,))

        print(f"[ALERT ENGINE] Email notification delivered to {recipient} for alert #{alert_id}.")
        return True, "Email Delivered"

    except Exception as e:
        print(f"[WARN] Failed to deliver email alert for #{alert_id}: {e}")
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE unknown_alerts SET email_sent = 0, notes = ? WHERE id = ?", (f"Email Error: {str(e)[:100]}", alert_id))
        except Exception:
            pass
        return False, str(e)

def dispatch_hardware_buzzer(alert_id: int):
    """
    Trigger physical ESP32 buzzer hardware or record virtual simulated buzzer activation.
    Runs safely in a background worker thread.
    """
    try:
        hardware_mode = get_config_value("HARDWARE_MODE", Config.HARDWARE_MODE).upper()

        if hardware_mode == "VIRTUAL":
            # Virtual Hardware Simulator Mode
            details = f"Virtual buzzer activated for UNKNOWN alert #{alert_id}"
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO hardware_logs (mode, event_type, details)
                    VALUES ('VIRTUAL', 'BUZZER_SIMULATED', ?)
                """, (details,))
                cursor.execute("UPDATE unknown_alerts SET esp32_triggered = 1 WHERE id = ?", (alert_id,))

            print(f"[HARDWARE SIMULATOR] Simulated buzzer activated for alert #{alert_id}.")
            return True, "Virtual Buzzer Activated"

        elif hardware_mode == "PHYSICAL":
            # Physical ESP32 Microcontroller Mode
            esp32_ip = get_config_value("ESP32_IP", Config.ESP32_IP)
            esp32_port = get_config_value("ESP32_PORT", str(Config.ESP32_PORT))
            timeout = float(get_config_value("ESP32_TIMEOUT", str(Config.ESP32_TIMEOUT)))

            url = f"http://{esp32_ip}:{esp32_port}/trigger-buzzer"
            payload = {
                "event": "UNKNOWN_DETECTION",
                "alert_id": alert_id,
                "duration_ms": 3000
            }

            try:
                response = requests.post(url, json=payload, timeout=timeout)
                if response.status_code == 200:
                    with get_db() as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO hardware_logs (mode, event_type, details)
                            VALUES ('PHYSICAL', 'ESP32_BUZZER_TRIGGERED', ?)
                        """, (f"ESP32 200 OK for alert #{alert_id}",))
                        cursor.execute("UPDATE unknown_alerts SET esp32_triggered = 1 WHERE id = ?", (alert_id,))

                    print(f"[HARDWARE ESP32] Successfully triggered physical buzzer on ESP32 ({esp32_ip}) for alert #{alert_id}.")
                    return True, "ESP32 Buzzer Triggered"
                else:
                    details = f"ESP32 returned status code {response.status_code}"
                    with get_db() as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO hardware_logs (mode, event_type, details)
                            VALUES ('PHYSICAL', 'ESP32_ERROR', ?)
                        """, (details,))
                        cursor.execute("UPDATE unknown_alerts SET esp32_triggered = 0 WHERE id = ?", (alert_id,))
                    return False, details

            except Exception as req_err:
                details = f"ESP32 Network Timeout/Unreachable ({esp32_ip}): {str(req_err)[:100]}"
                with get_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO hardware_logs (mode, event_type, details)
                        VALUES ('PHYSICAL', 'ESP32_DISCONNECTED', ?)
                    """, (details,))
                    cursor.execute("UPDATE unknown_alerts SET esp32_triggered = 0 WHERE id = ?", (alert_id,))

                print(f"[WARN] ESP32 hardware unreachable: {details}")
                return False, details

    except Exception as e:
        print(f"[ERROR] Hardware dispatcher error: {e}")
        return False, str(e)

def trigger_unknown_event_alerts(alert_id: int, snapshot_path: str, timestamp_str: str = "", location: str = "Main Campus Gate 1"):
    """
    Main alert orchestration handler. Spawns non-blocking background threads for email
    and hardware buzzer dispatch so video streaming frame rate is never blocked.
    """
    def _async_worker():
        # 1. Dispatch hardware buzzer trigger (Virtual or Physical)
        dispatch_hardware_buzzer(alert_id)
        # 2. Dispatch SMTP Email alert
        dispatch_email_alert(alert_id, snapshot_path, timestamp_str, location)

    worker_thread = threading.Thread(target=_async_worker, daemon=True)
    worker_thread.start()
