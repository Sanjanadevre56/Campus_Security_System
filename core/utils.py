from functools import wraps
from flask import session, redirect, url_for, flash, request
from werkzeug.security import generate_password_hash, check_password_hash
from core.database import get_db

def hash_password(password: str) -> str:
    """Generate a secure Werkzeug hash for a plain text password."""
    return generate_password_hash(password, method="scrypt")

def verify_password(password_hash: str, password: str) -> bool:
    """Verify a plain text password against a stored Werkzeug hash."""
    if not password_hash or not password:
        return False
    return check_password_hash(password_hash, password)

def login_required(f):
    """View decorator to protect routes that require security admin authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to access the security administration system.", "warning")
            return redirect(url_for("auth.login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """Retrieve the currently logged-in administrator from session state."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, created_at FROM admin_users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        return dict(user) if user else None
