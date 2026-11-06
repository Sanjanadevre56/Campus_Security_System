import sys
from pathlib import Path

# Ensure root directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config import Config
from core.database import init_db, get_db, get_config_value

def run_test():
    print("==========================================================")
    print("  AI-Based Campus Security System - Phase 1 Database Test ")
    print("==========================================================")
    print(f"[*] Base Directory    : {Config.BASE_DIR}")
    print(f"[*] Database Path     : {Config.DATABASE_PATH}")
    print(f"[*] Hardware Mode     : {Config.HARDWARE_MODE}")
    print(f"[*] Registered Uploads: {Config.REGISTERED_UPLOADS_DIR}")
    print(f"[*] Unknown Uploads   : {Config.UNKNOWN_UPLOADS_DIR}")
    print("----------------------------------------------------------")

    # Initialize Database Schema & Default Seeds
    print("[*] Initializing database schema and default seeds...")
    init_db()

    # Verify tables in database
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = [row['name'] for row in cursor.fetchall()]
        print(f"[+] Found {len(tables)} tables: {', '.join(tables)}")

        # Check default admin user
        cursor.execute("SELECT username, created_at FROM admin_users;")
        admins = cursor.fetchall()
        print(f"[+] Admin accounts count: {len(admins)}")
        for admin in admins:
            print(f"    - Username: {admin['username']} (Created: {admin['created_at']})")

        # Check seeded system configurations
        cursor.execute("SELECT config_key, config_value FROM system_config;")
        configs = cursor.fetchall()
        print(f"[+] System configurations count: {len(configs)}")
        for cfg in configs:
            print(f"    - {cfg['config_key']} = '{cfg['config_value']}'")

    print("----------------------------------------------------------")
    print("[✓] Phase 1 Database setup test executed successfully!")

if __name__ == "__main__":
    run_test()
