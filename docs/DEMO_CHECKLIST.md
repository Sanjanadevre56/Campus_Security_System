# Presentation Demonstration Checklist & Viva Guide

**Project Title**: AI-Based Campus Security System Using Facial Recognition  
**System URL**: `http://127.0.0.1:5000`  
**Default Credentials**: `admin` / `admin123`  

---

## Pre-Demonstration Setup Checklist

- [ ] Ensure Python virtual environment is activated (`.\venv\Scripts\Activate.ps1`).
- [ ] Confirm webcam is plugged in and accessible by Windows.
- [ ] Ensure `.env` is configured with:
  ```ini
  HARDWARE_MODE=VIRTUAL
  SMTP_ENABLED=False
  ```
- [ ] Have 1 clear test photo ready for registration containing **exactly one face**.
- [ ] Have 1 test image ready containing **no faces** (e.g. background/landscape photo) to demonstrate error handling.

---

## Step-by-Step Demonstration Sequence

### Step 1: Launch Application & Verify Setup
1. Open PowerShell and run:
   ```powershell
   cd C:\Users\Samsung\.gemini\antigravity\scratch\campus_security_system
   .\venv\Scripts\Activate.ps1
   python app.py
   ```
2. Point out console output showing database path, tables initialized, and Flask web server listening on `http://127.0.0.1:5000`.

### Step 2: Demonstrate Route Protection (Unauthenticated Access)
1. Open browser and attempt to navigate directly to `http://127.0.0.1:5000/dashboard`.
2. **Demonstrate Result**: System automatically redirects to `http://127.0.0.1:5000/login` with warning alert:  
   *"Please log in to access the security administration system."*

### Step 3: Admin Authentication & Dashboard Overview
1. Enter credentials:
   - **Username**: `admin`
   - **Password**: `admin123`
2. Click **Authenticate & Access Dashboard**.
3. **Point out Dashboard Features**:
   - Status Badge: `MODE: VIRTUAL SIMULATOR`
   - Metric Cards: Registered Personnel, Authorized Entries, Unknown Intruder Alerts, Hardware Logs.
   - Active System Parameters: `HARDWARE_MODE = VIRTUAL`, `FACE_MATCH_THRESHOLD = 0.5`, `SMTP_ENABLED = False`.

### Step 4: Biometric Person Registration & Single-Face Enforcement
1. Click **Register Person** in the navbar (`http://127.0.0.1:5000/register`).
2. **Demonstrate Error Handling (No-Face Photo)**:
   - Fill in details and select the **no-face test photo**. Check consent box.
   - Click **Process Image, Extract Encodings & Save Person**.
   - **Demonstrate Result**: Red alert error displayed: *"No face detected in the photo. Please upload a clear photo of a single person's face."* (Uploaded image is deleted immediately).
3. **Demonstrate Successful Registration**:
   - Fill in details:
     - **Full Name**: *Dr. Sarah Jenkins*
     - **Student/Staff ID**: *FAC-2026-101*
     - **Role**: *Faculty*
     - **Department**: *Computer Science*
     - **Email**: *s.jenkins@campus.edu*
     - **Photo**: Select the valid single-face photo.
     - **Consent**: Check the mandatory **Biometric Consent Confirmation** checkbox.
   - Click **Process Image, Extract Encodings & Save Person**.
   - **Demonstrate Result**: Success message displayed, 128-dimensional facial vector generated, and redirected to Personnel Directory.

### Step 5: Personnel Directory Overview
1. View `http://127.0.0.1:5000/persons`.
2. **Point out Features**:
   - Person ID, Full Name, Department, Role Badge (*Faculty*), Email.
   - Enrollment photo thumbnail (served securely via authenticated endpoint `/uploads/registered/...`).
   - Biometric status badge: `✓ 128-d Vector Enrolled`.

### Step 6: Live Camera Stream & Real-Time Face Recognition
1. Click **Camera** in the navbar (`http://127.0.0.1:5000/camera`).
2. Click **Start Live Camera**:
   - Stream status changes to `RUNNING` (Green badge).
   - Look into the webcam.
3. **Demonstrate KNOWN Person Recognition**:
   - System extracts live 128-d vector, compares against enrolled database, and matches your registered face.
   - **Visual Overlay**: **Cyan/Green bounding box** displaying `MATCH: Dr. Sarah Jenkins (FAC-2026-101) | Dist: 0.38`.
   - **Point out Console Log**: `[RECOGNITION LOG] Recorded entrance log for 'FAC-2026-101'`.
4. **Demonstrate Debounce Cooldown (5 Seconds)**:
   - Stay in front of the camera for 10 seconds.
   - Point out that only 1 entry log is written every 5 seconds, preventing database flooding.
5. **Demonstrate UNKNOWN Person Detection**:
   - Have an unregistered person look into the webcam (or obscure face).
   - **Visual Overlay**: **Amber/Orange bounding box** displaying `UNKNOWN (No Enrolled Match) | Dist: 0.68`.
   - **Point out Console Log**: `[RECOGNITION LOG] Recorded unknown alert snapshot` and `[HARDWARE SIMULATOR] Simulated buzzer activated`.
6. Click **Stop Camera Stream**.

### Step 7: Dashboard Event Verification
1. Return to **Dashboard** (`http://127.0.0.1:5000/dashboard`).
2. **Demonstrate Dashboard Records**:
   - **Recent Authorized Entries Table**: Shows `Dr. Sarah Jenkins` with timestamp and match confidence score.
   - **Recent Unknown Alerts Table**:
     - Snapshot thumbnail of the unknown face crop.
     - **Buzzer Outcome**: `✓ Virtual Buzzer` (Purple badge).
     - **Email Outcome**: `SMTP Disabled` (Muted gray badge).

### Step 8: Run Automated Test Suites
1. Open PowerShell and run:
   ```powershell
   python scripts/test_notifications.py
   ```
2. **Demonstrate Result**: Show examiners all 9 automated tests passing cleanly (Database, Registration, Camera Engine, Recognition, Debouncing, Mock SMTP, Virtual Hardware, and Protected Upload Routes).

---

## Examiners Viva Q&A Cheat Sheet

**Q1: How does the facial recognition algorithm work in your system?**  
*Answer*: The system uses a deep neural network model (`dlib`/`face_recognition`) to convert a face into a 128-dimensional floating point vector embedding. When a face is detected in a camera frame, its 128-d vector is compared against all enrolled vectors using Euclidean distance. If the minimum distance is below the threshold (`FACE_MATCH_THRESHOLD=0.5`), identity is confirmed.

**Q2: What is the purpose of debounced logging?**  
*Answer*: Webcams run at ~30 frames per second. Without debouncing, a person standing in front of the camera for 5 seconds would generate 150 duplicate database rows. The debounce engine (`DEBOUNCE_COOLDOWN_SECONDS=5`) enforces a 5-second cooldown window between repeat log entries for the same person or unknown alert event.

**Q3: Is student biometric data safe and private?**  
*Answer*: Yes. All facial recognition and database processing take place 100% offline on the local campus server. Enrolled photos and 128-d vector embeddings are stored locally in SQLite and protected by Flask session authentication (`@login_required`). No data is sent to external cloud APIs.

**Q4: How does the system handle hardware if an ESP32 is not connected?**  
*Answer*: The system features a dual hardware mode. In default `VIRTUAL` mode, buzzer events are simulated and logged safely in SQLite `hardware_logs` without network requests. In `PHYSICAL` mode, non-blocking background threads send HTTP POST requests (`/trigger-buzzer`) to the ESP32 IP address with network timeout protection.

**Q5: What does an UNKNOWN classification mean?**  
*Answer*: An `UNKNOWN` classification means the detected face did not match any enrolled 128-dimensional facial vector below the distance threshold (`0.5`). It indicates that no enrolled match was found, rather than legal proof of an unauthorized intruder.
