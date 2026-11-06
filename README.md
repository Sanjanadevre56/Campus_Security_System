# AI-Based Campus Security System Using Facial Recognition

An offline-first, controlled campus security access monitoring system built with Python, Flask, SQLite, OpenCV, and `face_recognition`. Designed for authorized campus access control and security management.

---

## Project Overview & Objectives

The **AI-Based Campus Security System** provides real-time automated entrance monitoring using computer vision and 128-dimensional facial vector embeddings. The system compares faces detected at a campus entrance against an offline database of authorized students and staff.

### Key Objectives
- **Automated Entrance Monitoring**: Continuously detect faces from a webcam video stream at gate checkpoints.
- **Identity Verification**: Match detected faces against locally registered 128-dimensional facial embeddings.
- **Authorized Entry Logging**: Automatically log date, time, person ID, and match confidence into SQLite when an authorized individual enters.
- **Intruder Alert & Snapshot Capture**: Classify unmatched faces as `UNKNOWN`, capture a cropped face snapshot, log an intruder alert record, and trigger visual alert indicators on the security dashboard.
- **Hardware & Notification Integration**: Provide flexible execution modes (**Virtual Hardware Simulator Mode** for offline PC testing and **Physical ESP32 Mode** for external hardware buzzer activation over local Wi-Fi) alongside optional SMTP email notifications.
- **Privacy & Compliance**: Ensure 100% offline biometric processing without third-party cloud APIs, requiring explicit administrative confirmation of biometric enrollment consent.

---

## Features Implemented

1. **Admin Authentication & Control Center**
   - Session-based administrator login and logout using Werkzeug `scrypt` password hashing.
   - Protected security dashboard displaying genuine SQLite database metric counts, active settings, recent entrance history, and alert outcome badges.

2. **Consent-Aware Biometric Person Registration**
   - Student and staff enrollment module with 128-dimensional facial vector extraction using `face_recognition`.
   - Single-face enforcement (rejects 0-face or multi-face photos), image file format validation (JPG/PNG), size limit enforcement (5 MB), and duplicate ID prevention.
   - Mandatory biometric consent confirmation check.

3. **Authorized Personnel Directory**
   - Protected administrative directory listing registered individuals, enrollment photo thumbnails, vector status, and cascading record deletion capability.

4. **Live OpenCV Camera Stream Monitor**
   - Operator-controlled live MJPEG video stream using OpenCV (`cv2.VideoCapture`).
   - Real-time 128-dimensional facial recognition with custom bounding box overlays:
     - **KNOWN Person**: **Cyan/Green bounding box** displaying `MATCH: Name (ID) | Dist: 0.38`.
     - **UNKNOWN Person**: **Amber/Orange bounding box** displaying `UNKNOWN (No Enrolled Match) | Dist: 0.68`.

5. **Debounced Event Logging**
   - Configurable cooldown buffer (`DEBOUNCE_COOLDOWN_SECONDS=5`) preventing frame flooding by enforcing a time delay between repeated logs for the same person or intruder snapshot events.

6. **Dual Hardware Mode & Notification Engine**
   - **Virtual Mode**: Simulates hardware buzzer activations and logs records in `hardware_logs` without network requests.
   - **Physical ESP32 Mode**: Sends HTTP `POST` requests to `http://<ESP32_IP>:80/trigger-buzzer` with network timeout protection.
   - **SMTP Email Notifications**: Dispatches HTML email alerts with snapshot attachments when enabled (`SMTP_ENABLED=True`).

---

## Technologies Used

- **Programming Language**: Python 3.11
- **Web Framework**: Flask 3.0.3 (Jinja2 Templates, Werkzeug Security, Blueprints)
- **Database**: SQLite 3 (Thread-safe context managers, Foreign Keys)
- **Computer Vision**: OpenCV (`opencv-python` 4.9)
- **Facial Recognition**: `face_recognition` 1.3, `dlib` 19.24, `NumPy` 1.26
- **Image Processing**: Pillow (`PIL`) 10.3
- **Frontend**: HTML5, Vanilla JavaScript (ES6+), Vanilla CSS3 (Custom Glassmorphism Dark Theme, Google Fonts `Inter`)
- **Hardware Integration**: ESP32 Microcontroller (Arduino C++ Firmware)

---

## Project Folder Structure

```text
campus_security_system/
├── app.py                      # Main Flask application entrypoint & factory
├── config.py                   # Central configuration & absolute path manager
├── schema.sql                  # SQLite database table definitions
├── requirements.txt            # Python dependencies specification
├── .env                        # Active environment configuration
├── .env.example                # Environment variables template
├── README.md                   # System documentation & setup guide
├── core/                       # Core system logic modules
│   ├── __init__.py
│   ├── database.py             # SQLite connection manager & system_config helpers
│   ├── face_engine.py          # 128-d vector extraction, serialization & matching
│   ├── camera_engine.py        # OpenCV camera capture, recognition & debounced logging
│   ├── alert_engine.py         # Async background email & ESP32 hardware dispatchers
│   └── utils.py                # Password hashing, session helpers & @login_required
├── routes/                     # Flask API & Web Route Blueprints
│   ├── __init__.py
│   ├── auth_routes.py          # Admin login, logout & dashboard views
│   ├── person_routes.py        # Registration, directory CRUD & protected image serving
│   └── camera_routes.py       # Camera control panel & live MJPEG video feed
├── static/                     # Web static assets
│   ├── css/
│   │   ├── main.css            # Dark glassmorphism layout & global styles
│   │   └── forms.css           # Auth & registration form styles
│   └── uploads/                # Local runtime upload directories
│       ├── registered/         # Authorized personnel enrollment photos
│       └── unknowns/           # Captured intruder alert snapshot crops
├── templates/                  # Jinja2 HTML templates
│   ├── base.html               # Shared layout shell with header navigation
│   ├── login.html              # Admin login page
│   ├── dashboard.html          # Security control center dashboard
│   ├── register.html           # Biometric person registration form
│   ├── persons.html            # Authorized personnel directory
│   └── camera.html             # Live camera monitor panel
├── esp32/                      # Microcontroller firmware source
│   └── buzzer_controller/
│       └── buzzer_controller.ino # ESP32 Arduino C++ HTTP buzzer server sketch
├── scripts/                    # Automated test & utility scripts
│   ├── test_database.py        # Phase 1 SQLite schema & admin test
│   ├── test_registration.py    # Phase 3 face extraction & single-face test
│   ├── test_camera.py          # Phase 4 camera manager & route protection test
│   ├── test_recognition.py     # Phase 5 recognition & debounce test
│   ├── test_notifications.py   # Phase 6 alert engine & mock hardware test
│   └── update_config.py       # Configuration parameter update utility
├── docs/                       # Project documentation & presentation guides
│   ├── PROJECT_REPORT.md       # Comprehensive academic project report
│   └── DEMO_CHECKLIST.md       # Step-by-step presentation demonstration checklist
└── instance/                   # Database runtime folder
    └── campus_security.db      # Production SQLite database file
```

---

## Installation & Setup on Windows PowerShell

### Step 1: Open PowerShell and Navigate to Workspace
```powershell
cd C:\Users\Samsung\.gemini\antigravity\scratch\campus_security_system
```

### Step 2: Create & Activate Python Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Step 3: Install Backend Dependencies
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Verify Database & Configuration
```powershell
python scripts/update_config.py
```

### Step 5: Start the Flask Application
```powershell
python app.py
```

---

## Security Warning: Default Login & Password Change

> [!WARNING]
> **Development Credentials**: The system seeds a default administrator account upon database initialization:
> - **Username**: `admin`
> - **Password**: `admin123`

To change the default admin password in a production environment:
1. Generate a new password hash using Python:
   ```python
   from werkzeug.security import generate_password_hash
   print(generate_password_hash("your_new_password", method="scrypt"))
   ```
2. Update the `password_hash` column in SQLite `admin_users` table for `username = 'admin'`.

---

## Running Automated Test Suites

The project includes isolated, deterministic test scripts that do **not** require a physical webcam, real SMTP server, or external ESP32 hardware:

```powershell
# Phase 1: Test Database & Admin Seeding
python scripts/test_database.py

# Phase 3: Test Face Engine & Single-Face Enrollment
python scripts/test_registration.py

# Phase 4: Test Camera Manager & Route Protection
python scripts/test_camera.py

# Phase 5: Test Face Recognition & Debounce Cooldown
python scripts/test_recognition.py

# Phase 6: Test Notifications, Mock SMTP & Virtual Buzzer
python scripts/test_notifications.py
```

---

## Current Configuration Status

- **`HARDWARE_MODE = VIRTUAL`**: Hardware buzzer activations are simulated and logged safely in SQLite `hardware_logs` without network requests.
- **`SMTP_ENABLED = False`**: Automated email alerts are disabled by default until real SMTP credentials are provided in `.env`.

---

## System Scope & Limitations

1. **Virtual Hardware Default**: Physical ESP32 hardware buzzer activation requires setting `HARDWARE_MODE=PHYSICAL`, flashing the ESP32 sketch, and configuring `ESP32_IP`. In default `VIRTUAL` mode, buzzer events are simulated.
2. **"UNKNOWN" Classification Meaning**: An `UNKNOWN` classification simply indicates that the detected face does not match any enrolled facial vector in the registered database below the configured distance threshold (`0.5`). It does **not** constitute legal proof of an unauthorized intruder.
3. **Lighting & Camera Angle Sensitivity**: Face recognition accuracy depends on clear frontal lighting and un-obscured facial features.

---

## Privacy, Biometric Consent & Data Retention

- **Offline Local Storage**: All facial encodings (128-d float vectors) and enrollment images are stored locally (`instance/campus_security.db` and `/static/uploads/registered/`). No biometric data is sent to cloud APIs.
- **Mandatory Biometric Consent**: Person registration requires explicit administrative confirmation that biometric enrollment consent was obtained.
- **Protected Image & Stream Routes**: Video streams (`/camera/video_feed`) and snapshot images (`/uploads/unknowns/<filename>`) are protected by `@login_required` session authentication.
- **No Continuous Video Recording**: Live video frames are processed strictly in-memory. Only single event crop snapshots are saved upon detecting an unknown face.
