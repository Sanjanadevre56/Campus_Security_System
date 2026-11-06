import sqlite3
from contextlib import contextmanager
from werkzeug.security import generate_password_hash
from config import Config

def get_db_connection():
    """Create a new database connection with row factory enabled."""
    conn = sqlite3.connect(Config.DATABASE_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

@contextmanager
def get_db():
    """Context manager for managing SQLite connections safely."""
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def init_db():
    """Initialize database tables using schema.sql and seed default configuration & admin user."""
    with open(Config.BASE_DIR / "schema.sql", "r", encoding="utf-8") as f:
        schema_sql = f.read()
    
    with get_db() as conn:
        conn.executescript(schema_sql)

        # Migration helper: ensure new columns exist in registered_persons
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(registered_persons)")
        columns = [row["name"] for row in cursor.fetchall()]
        if "email" not in columns:
            cursor.execute("ALTER TABLE registered_persons ADD COLUMN email TEXT;")
        if "consent_given" not in columns:
            cursor.execute("ALTER TABLE registered_persons ADD COLUMN consent_given INTEGER DEFAULT 1;")
        cursor.execute("SELECT COUNT(*) FROM admin_users")
        if cursor.fetchone()[0] == 0:
            default_user = Config.DEFAULT_ADMIN_USER
            default_pass = Config.DEFAULT_ADMIN_PASS
            pass_hash = generate_password_hash(default_pass, method="scrypt")
            cursor.execute(
                "INSERT INTO admin_users (username, password_hash) VALUES (?, ?)",
                (default_user, pass_hash)
            )
            print(f"[DB INIT] Created default admin account: '{default_user}'")

        # Seed initial system configuration keys if missing
        default_configs = [
            ("HARDWARE_MODE", Config.HARDWARE_MODE, "Operating mode: VIRTUAL or PHYSICAL"),
            ("ESP32_IP", Config.ESP32_IP, "Local IP address of the ESP32 microcontroller"),
            ("ESP32_PORT", str(Config.ESP32_PORT), "HTTP port of the ESP32 server"),
            ("FACE_MATCH_THRESHOLD", str(Config.FACE_MATCH_THRESHOLD), "Euclidean distance match threshold (0.4 - 0.6)"),
            ("DEBOUNCE_COOLDOWN_SECONDS", str(Config.DEBOUNCE_COOLDOWN_SECONDS), "Cooldown in seconds between repeated alerts"),
            ("SMTP_ENABLED", str(Config.SMTP_ENABLED), "Enable or disable email alert notifications"),
            ("ALERT_RECIPIENT_EMAIL", Config.ALERT_RECIPIENT_EMAIL, "Destination email address for unknown intruder alerts")
        ]

        for key, value, desc in default_configs:
            cursor.execute(
                "INSERT OR IGNORE INTO system_config (config_key, config_value, description) VALUES (?, ?, ?)",
                (key, value, desc)
            )
        print("[DB INIT] Database initialization complete.")

def get_config_value(key: str, default: str = "") -> str:
    """Retrieve a system configuration parameter from SQLite."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT config_value FROM system_config WHERE config_key = ?", (key,))
        row = cursor.fetchone()
        return row["config_value"] if row else default

def set_config_value(key: str, value: str):
    """Set or update a system configuration parameter in SQLite."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO system_config (config_key, config_value) VALUES (?, ?) "
            "ON CONFLICT(config_key) DO UPDATE SET config_value = excluded.config_value",
            (key, str(value))
        )
