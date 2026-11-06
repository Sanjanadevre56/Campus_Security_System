from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from core.database import get_db, get_config_value
from core.utils import verify_password, login_required, get_current_user

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Handle security administrator login."""
    # Redirect if user is already authenticated
    if session.get("user_id"):
        return redirect(url_for("auth.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("Please enter both username and password.", "danger")
            return render_template("login.html")

        # Query database using parameterized query
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, password_hash FROM admin_users WHERE username = ?", (username,))
            user = cursor.fetchone()

        # Check user existence and verify Werkzeug password hash
        if user and verify_password(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash(f"Welcome back, {user['username']}! Logged in successfully.", "success")
            
            next_url = request.args.get("next")
            if next_url and next_url.startswith("/"):
                return redirect(next_url)
            return redirect(url_for("auth.dashboard"))
        else:
            flash("Invalid administrator credentials. Please check and try again.", "danger")

    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    """Clear administrator session and log out."""
    session.clear()
    flash("You have been logged out of the campus security system.", "info")
    return redirect(url_for("auth.login"))

@auth_bp.route("/dashboard")
@login_required
def dashboard():
    """Render main security dashboard with real system metrics and table counts."""
    current_user = get_current_user()

    with get_db() as conn:
        cursor = conn.cursor()

        # Real count of active registered personnel
        cursor.execute("SELECT COUNT(*) AS count FROM registered_persons WHERE is_active = 1")
        registered_count = cursor.fetchone()["count"]

        # Real count of total known entry logs
        cursor.execute("SELECT COUNT(*) AS count FROM entry_logs")
        entry_logs_count = cursor.fetchone()["count"]

        # Real count of total unknown intruder alerts
        cursor.execute("SELECT COUNT(*) AS count FROM unknown_alerts")
        unknown_alerts_count = cursor.fetchone()["count"]

        # Real count of unresolved intruder alerts
        cursor.execute("SELECT COUNT(*) AS count FROM unknown_alerts WHERE status = 'UNRESOLVED'")
        unresolved_alerts_count = cursor.fetchone()["count"]

        # Real count of hardware event logs
        cursor.execute("SELECT COUNT(*) AS count FROM hardware_logs")
        hardware_logs_count = cursor.fetchone()["count"]

        # Fetch recent 5 entry logs with person details using parameterized JOIN
        cursor.execute("""
            SELECT e.id, e.timestamp, e.confidence_score, e.gate_location, p.full_name, p.person_id, p.role, p.department
            FROM entry_logs e
            JOIN registered_persons p ON e.person_id = p.person_id
            ORDER BY e.timestamp DESC
            LIMIT 5
        """)
        recent_entries = [dict(row) for row in cursor.fetchall()]

        # Fetch recent 5 unknown alerts
        cursor.execute("""
            SELECT id, snapshot_path, timestamp, gate_location, status, hardware_mode, esp32_triggered, email_sent, notes
            FROM unknown_alerts
            ORDER BY id DESC
            LIMIT 5
        """)
        recent_unknowns = [dict(row) for row in cursor.fetchall()]

    # Retrieve live configuration parameters from system_config table
    hardware_mode = get_config_value("HARDWARE_MODE", "VIRTUAL").upper()
    face_threshold = get_config_value("FACE_MATCH_THRESHOLD", "0.5")
    esp32_ip = get_config_value("ESP32_IP", "192.168.1.100")
    smtp_enabled_str = get_config_value("SMTP_ENABLED", "False")
    smtp_enabled_bool = smtp_enabled_str.lower() in ("true", "1", "yes")

    system_stats = {
        "registered_count": registered_count,
        "entry_logs_count": entry_logs_count,
        "unknown_alerts_count": unknown_alerts_count,
        "unresolved_alerts_count": unresolved_alerts_count,
        "hardware_logs_count": hardware_logs_count,
        "hardware_mode": hardware_mode,
        "face_threshold": face_threshold,
        "esp32_ip": esp32_ip,
        "smtp_enabled": smtp_enabled_str,
        "smtp_enabled_bool": smtp_enabled_bool
    }

    return render_template(
        "dashboard.html",
        user=current_user,
        stats=system_stats,
        recent_entries=recent_entries,
        recent_unknowns=recent_unknowns
    )
