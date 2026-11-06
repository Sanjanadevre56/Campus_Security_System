import sys
import os
import json
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw

# Ensure root directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config import Config
from core.database import init_db, get_db
from core.face_engine import extract_face_encoding, serialize_encoding, deserialize_encoding, calculate_face_distance
from routes.person_routes import is_allowed_file

def run_registration_tests():
    print("==========================================================")
    print("  AI-Based Campus Security System - Phase 3 Test Suite    ")
    print("==========================================================")
    
    init_db()
    temp_dir = BASE_DIR / "instance" / "test_temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Test 1: File Extension Validation
    print("[*] Test 1: Validating file extension checker...")
    assert is_allowed_file("student.jpg") == True
    assert is_allowed_file("staff.png") == True
    assert is_allowed_file("document.pdf") == False
    assert is_allowed_file("script.py") == False
    print("    [✓] File extension rules verified.")

    # Test 2: No-Face Image Detection Test
    print("[*] Test 2: Testing 0-Face Image Detection...")
    blank_img_path = temp_dir / "no_face_blank.jpg"
    blank_img = Image.new("RGB", (300, 300), color=(128, 128, 128))
    blank_img.save(str(blank_img_path))

    success, encoding, err_msg = extract_face_encoding(str(blank_img_path))
    assert success == False
    assert "No face detected" in err_msg
    print(f"    [✓] Successfully caught 0-face image: '{err_msg}'")

    # Test 3: Facial Vector Serialization & Deserialization Test
    print("[*] Test 3: Testing 128-d Vector Serialization...")
    dummy_vector = np.random.rand(128).astype(np.float64)
    json_serialized = serialize_encoding(dummy_vector)
    deserialized_vector = deserialize_encoding(json_serialized)

    assert isinstance(json_serialized, str)
    assert len(deserialized_vector) == 128
    assert np.allclose(dummy_vector, deserialized_vector)
    print("    [✓] 128-dimensional vector JSON serialization verified.")

    # Test 4: Distance Metric Calculation
    print("[*] Test 4: Testing Euclidean Distance Calculation...")
    vec1 = np.ones(128, dtype=np.float64)
    vec2 = np.ones(128, dtype=np.float64)
    dist_same = calculate_face_distance(vec1, vec2)
    assert dist_same == 0.0
    print(f"    [✓] Zero distance for identical vectors verified (distance = {dist_same}).")

    # Clean up temp files
    if blank_img_path.exists():
        blank_img_path.unlink()
    if temp_dir.exists():
        try:
            temp_dir.rmdir()
        except Exception:
            pass

    print("----------------------------------------------------------")
    print("[✓] Phase 3 Person Registration & Facial Engine tests passed!")

if __name__ == "__main__":
    run_registration_tests()
