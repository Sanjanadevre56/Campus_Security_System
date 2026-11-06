import os
import uuid
from pathlib import Path
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory, Response
from werkzeug.utils import secure_filename
from PIL import Image

from config import Config
from core.database import get_db
from core.utils import login_required
from core.face_engine import extract_face_encoding, serialize_encoding

person_bp = Blueprint("person", __name__)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB limit

def is_allowed_file(filename: str) -> bool:
    """Check if uploaded file has a valid image extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@person_bp.route("/register", methods=["GET", "POST"])
@login_required
def register_person():
    """Register a new student or staff member with consent confirmation and face encoding."""
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        person_id = request.form.get("person_id", "").strip().upper()
        role = request.form.get("role", "").strip()
        department = request.form.get("department", "").strip()
        email = request.form.get("email", "").strip()
        consent = request.form.get("consent")

        # 1. Consent Verification
        if not consent:
            flash("Biometric consent confirmation is required to proceed with registration.", "danger")
            return render_template("register.html", form_data=request.form)

        # 2. Form Input Validation
        if not full_name or not person_id or not role or not department:
            flash("Please complete all required fields (Full Name, ID, Role, Department).", "danger")
            return render_template("register.html", form_data=request.form)

        if role not in ("Student", "Faculty", "Staff", "Visitor"):
            flash("Invalid role selected. Please choose Student, Faculty, Staff, or Visitor.", "danger")
            return render_template("register.html", form_data=request.form)

        # 3. Prevent Duplicate Person ID in Database
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM registered_persons WHERE person_id = ?", (person_id,))
            if cursor.fetchone():
                flash(f"Person ID '{person_id}' is already registered in the system.", "danger")
                return render_template("register.html", form_data=request.form)

        # 4. Uploaded File Validation
        if "photo" not in request.files:
            flash("Please select an enrollment photo to upload.", "danger")
            return render_template("register.html", form_data=request.form)

        file = request.files["photo"]
        if not file or file.filename == "":
            flash("No file selected for upload.", "danger")
            return render_template("register.html", form_data=request.form)

        if not is_allowed_file(file.filename):
            flash("Invalid file format. Only JPG, JPEG, and PNG images are allowed.", "danger")
            return render_template("register.html", form_data=request.form)

        # Verify image file using PIL
        try:
            image_obj = Image.open(file.stream)
            image_obj.verify()
            file.stream.seek(0) # Reset stream pointer after verification
        except Exception:
            flash("Uploaded file is corrupted or not a valid image.", "danger")
            return render_template("register.html", form_data=request.form)

        # Save image with secure filename
        ext = file.filename.rsplit(".", 1)[1].lower()
        unique_filename = f"{secure_filename(person_id)}_{uuid.uuid4().hex[:8]}.{ext}"
        save_path = Path(Config.REGISTERED_UPLOADS_DIR) / unique_filename
        file.save(str(save_path))

        # 5. Extract Face Encoding Vector & Enforce Single-Face Rule
        success, encoding_vector, error_msg = extract_face_encoding(str(save_path))

        if not success:
            # Delete uploaded photo if face detection fails
            if save_path.exists():
                save_path.unlink()
            flash(error_msg, "danger")
            return render_template("register.html", form_data=request.form)

        # 6. Transactional Database Save
        try:
            serialized_vector = serialize_encoding(encoding_vector)
            relative_photo_path = f"registered/{unique_filename}"

            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO registered_persons (person_id, full_name, department, role, email, photo_path, consent_given, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, 1, 1)
                """, (person_id, full_name, department, role, email, relative_photo_path))

                cursor.execute("""
                    INSERT INTO face_encodings (person_id, encoding_data)
                    VALUES (?, ?)
                """, (person_id, serialized_vector))

            flash(f"Successfully registered {full_name} ({person_id}) with 128-d facial vector encoding!", "success")
            return redirect(url_for("person.list_persons"))

        except Exception as e:
            if save_path.exists():
                save_path.unlink()
            flash(f"Database error during registration: {str(e)}", "danger")
            return render_template("register.html", form_data=request.form)

    return render_template("register.html")

@person_bp.route("/persons")
@login_required
def list_persons():
    """Display registered students and staff personnel directory."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.id, p.person_id, p.full_name, p.department, p.role, p.email, p.photo_path, p.created_at, p.is_active,
                   (SELECT COUNT(*) FROM face_encodings fe WHERE fe.person_id = p.person_id) AS encoding_count
            FROM registered_persons p
            ORDER BY p.created_at DESC
        """)
        persons = [dict(row) for row in cursor.fetchall()]

    return render_template("persons.html", persons=persons)

@person_bp.route("/persons/delete/<person_id>", methods=["POST"])
@login_required
def delete_person(person_id):
    """Delete a registered person record and clean up associated enrollment photo."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT photo_path FROM registered_persons WHERE person_id = ?", (person_id,))
        row = cursor.fetchone()

        if not row:
            flash(f"Person ID '{person_id}' not found.", "warning")
            return redirect(url_for("person.list_persons"))

        photo_relative_path = row["photo_path"]
        
        # Delete record from database (cascades to face_encodings and entry_logs)
        cursor.execute("DELETE FROM registered_persons WHERE person_id = ?", (person_id,))
        cursor.execute("DELETE FROM face_encodings WHERE person_id = ?", (person_id,))

        # Remove image file from uploads folder
        if photo_relative_path:
            filename = os.path.basename(photo_relative_path)
            file_path = Path(Config.REGISTERED_UPLOADS_DIR) / filename
            if file_path.exists():
                try:
                    file_path.unlink()
                except Exception as e:
                    print(f"[WARN] Failed to delete photo file {file_path}: {e}")

    flash(f"Person ID '{person_id}' and facial encodings removed successfully.", "success")
    return redirect(url_for("person.list_persons"))

@person_bp.route("/uploads/registered/<filename>")
@login_required
def serve_registered_photo(filename):
    """Protected route to serve enrollment photos only to authenticated administrators."""
    return send_from_directory(Config.REGISTERED_UPLOADS_DIR, filename)

@person_bp.route("/uploads/unknowns/<filename>")
@login_required
def serve_unknown_photo(filename):
    """Protected route to serve unknown intruder alert snapshots to authenticated administrators."""
    safe_filename = secure_filename(filename)
    file_path = Path(Config.UNKNOWN_UPLOADS_DIR) / safe_filename
    if not file_path.exists():
        # Return a safe inline SVG placeholder if snapshot file is missing or deleted
        svg_placeholder = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" stroke-width="2">'
            '<rect x="3" y="3" width="18" height="18" rx="2"/>'
            '<circle cx="8.5" cy="8.5" r="1.5"/>'
            '<path d="M21 15l-5-5L5 21"/>'
            '</svg>'
        )
        return Response(svg_placeholder, mimetype="image/svg+xml", status=200)
    return send_from_directory(Config.UNKNOWN_UPLOADS_DIR, safe_filename)
