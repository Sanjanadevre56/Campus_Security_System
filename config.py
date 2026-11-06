import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
STATIC_DIR = BASE_DIR / "static"
UPLOAD_DIR = STATIC_DIR / "uploads"

# Ensure runtime directories exist
INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
(UPLOAD_DIR / "registered").mkdir(parents=True, exist_ok=True)
(UPLOAD_DIR / "unknowns").mkdir(parents=True, exist_ok=True)

class Config:
    """Base application configuration."""
    BASE_DIR = BASE_DIR
    INSTANCE_DIR = INSTANCE_DIR
    SECRET_KEY = os.getenv("SECRET_KEY", "campus_security_default_secret_key_2026")
    DATABASE_PATH = str(INSTANCE_DIR / "campus_security.db")
    
    # Upload Directories
    REGISTERED_UPLOADS_DIR = str(UPLOAD_DIR / "registered")
    UNKNOWN_UPLOADS_DIR = str(UPLOAD_DIR / "unknowns")

    # Hardware Mode Configuration ('VIRTUAL' or 'PHYSICAL')
    HARDWARE_MODE = os.getenv("HARDWARE_MODE", "VIRTUAL").upper()
    ESP32_IP = os.getenv("ESP32_IP", "192.168.1.100")
    ESP32_PORT = int(os.getenv("ESP32_PORT", 80))
    ESP32_TIMEOUT = float(os.getenv("ESP32_TIMEOUT", 1.5))

    # Camera Stream Configuration
    CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", 0))

    # Facial Recognition Parameters
    # Euclidean distance threshold: lower = stricter, higher = looser (0.5 is optimal for dlib/face_recognition)
    FACE_MATCH_THRESHOLD = float(os.getenv("FACE_MATCH_THRESHOLD", 0.5))
    DEBOUNCE_COOLDOWN_SECONDS = int(os.getenv("DEBOUNCE_COOLDOWN_SECONDS", 5))

    # Email Alert Credentials (SMTP)
    SMTP_ENABLED = os.getenv("SMTP_ENABLED", "False").lower() in ("true", "1", "yes")
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    ALERT_RECIPIENT_EMAIL = os.getenv("ALERT_RECIPIENT_EMAIL", "")

    # Security Admin Default Credentials (used on initial database setup)
    DEFAULT_ADMIN_USER = os.getenv("DEFAULT_ADMIN_USER", "admin")
    DEFAULT_ADMIN_PASS = os.getenv("DEFAULT_ADMIN_PASS", "admin123")
