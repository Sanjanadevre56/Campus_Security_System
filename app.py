import os
from flask import Flask, redirect, url_for
from config import Config
from core.database import init_db
from routes.auth_routes import auth_bp
from routes.person_routes import person_bp
from routes.camera_routes import camera_bp

def create_app():
    """Application factory for AI-Based Campus Security System."""
    app = Flask(__name__)
    app.config.from_object(Config)
    app.secret_key = Config.SECRET_KEY

    # Initialize SQLite schema and default admin account on startup
    with app.app_context():
        init_db()

    # Register modular blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(person_bp)
    app.register_blueprint(camera_bp)

    @app.route("/")
    def index():
        """Root route redirecting to dashboard."""
        return redirect(url_for("auth.dashboard"))

    return app

app = create_app()

if __name__ == "__main__":
    print("==========================================================")
    print("  AI-Based Campus Security System - Starting Flask Server")
    print("==========================================================")
    print(f"[*] Access URL: http://127.0.0.1:5000")
    print(f"[*] Default Login: admin / admin123")
    print("==========================================================")
    app.run(host="127.0.0.1", port=5000, debug=True)
