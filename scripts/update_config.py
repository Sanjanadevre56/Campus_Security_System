import sys
from pathlib import Path

# Ensure root directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.database import init_db, set_config_value, get_config_value

def apply_config():
    """Update HARDWARE_MODE to VIRTUAL and SMTP_ENABLED to False in SQLite system_config."""
    init_db()
    set_config_value("HARDWARE_MODE", "VIRTUAL")
    set_config_value("SMTP_ENABLED", "False")
    
    print("==========================================================")
    print("  System Configuration Updated Successfully              ")
    print("==========================================================")
    print(f"[✓] HARDWARE_MODE = '{get_config_value('HARDWARE_MODE')}'")
    print(f"[✓] SMTP_ENABLED  = '{get_config_value('SMTP_ENABLED')}'")
    print("----------------------------------------------------------")

if __name__ == "__main__":
    apply_config()
