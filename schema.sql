-- Admin Authentication Table
CREATE TABLE IF NOT EXISTS admin_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Authorized Personnel Directory (Students & Staff)
CREATE TABLE IF NOT EXISTS registered_persons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id TEXT UNIQUE NOT NULL, -- e.g. STU-2026-101 or FAC-2026-502
    full_name TEXT NOT NULL,
    department TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('Student', 'Faculty', 'Staff', 'Visitor')),
    email TEXT,
    photo_path TEXT NOT NULL,
    consent_given INTEGER DEFAULT 1,
    is_active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Serialized Facial Embedding Vectors (128-dimensional float arrays)
CREATE TABLE IF NOT EXISTS face_encodings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id TEXT NOT NULL,
    encoding_data BLOB NOT NULL, -- Binary numpy float array serialization
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(person_id) REFERENCES registered_persons(person_id) ON DELETE CASCADE
);

-- Known Person Authorized Entry History
CREATE TABLE IF NOT EXISTS entry_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    confidence_score REAL NOT NULL,
    gate_location TEXT DEFAULT 'Main Campus Gate 1',
    FOREIGN KEY(person_id) REFERENCES registered_persons(person_id) ON DELETE CASCADE
);

-- Unknown Person Intrusion Alerts
CREATE TABLE IF NOT EXISTS unknown_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_path TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    gate_location TEXT DEFAULT 'Main Campus Gate 1',
    status TEXT DEFAULT 'UNRESOLVED' CHECK(status IN ('UNRESOLVED', 'RESOLVED', 'FALSE_ALARM')),
    hardware_mode TEXT DEFAULT 'VIRTUAL', -- VIRTUAL or PHYSICAL
    esp32_triggered INTEGER DEFAULT 0,
    email_sent INTEGER DEFAULT 0,
    notes TEXT
);

-- Hardware Buzzer & System Activation Logs (Tracks Virtual & Physical Buzzer Events)
CREATE TABLE IF NOT EXISTS hardware_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mode TEXT NOT NULL CHECK(mode IN ('VIRTUAL', 'PHYSICAL')),
    event_type TEXT NOT NULL, -- e.g. BUZZER_ACTIVATED, ESP32_DISCONNECTED, ESP32_TRIGGERED
    details TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Dynamic System Configuration Parameters
CREATE TABLE IF NOT EXISTS system_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_key TEXT UNIQUE NOT NULL,
    config_value TEXT NOT NULL,
    description TEXT
);
