from flask import Blueprint, render_template, Response, jsonify, request
from core.utils import login_required
from core.camera_engine import camera_engine

camera_bp = Blueprint("camera", __name__)

@camera_bp.route("/camera")
@login_required
def camera_page():
    """Render the live camera monitoring dashboard."""
    return render_template("camera.html", is_running=camera_engine.is_running)

@camera_bp.route("/camera/video_feed")
@login_required
def video_feed():
    """
    Live MJPEG video stream endpoint.
    Protected by admin authentication.
    """
    # If camera is not currently started by operator, auto-start it when accessing feed
    if not camera_engine.is_running:
        success, msg = camera_engine.start()
        if not success:
            # If camera fails to start, return offline frame stream
            pass

    return Response(
        camera_engine.generate_mjpeg_stream(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )

@camera_bp.route("/camera/start", methods=["POST"])
@login_required
def start_camera():
    """Explicitly start the camera video stream."""
    success, message = camera_engine.start()
    return jsonify({"success": success, "message": message, "is_running": camera_engine.is_running})

@camera_bp.route("/camera/stop", methods=["POST"])
@login_required
def stop_camera():
    """Explicitly stop the camera video stream and release hardware resources."""
    success, message = camera_engine.stop()
    return jsonify({"success": success, "message": message, "is_running": camera_engine.is_running})

@camera_bp.route("/camera/status", methods=["GET"])
@login_required
def camera_status():
    """Return current camera streaming status as JSON."""
    return jsonify({"is_running": camera_engine.is_running})
