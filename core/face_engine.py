import json
import numpy as np
import face_recognition
from PIL import Image

def extract_face_encoding(image_source):
    """
    Extract a 128-dimensional facial encoding vector from an image file path or bytes object.
    
    Returns:
        tuple: (success: bool, encoding: np.ndarray | None, error_message: str)
    """
    try:
        # Load image into numpy RGB array
        if isinstance(image_source, (str, bytes)):
            img = face_recognition.load_image_file(image_source)
        else:
            # If a PIL Image object is passed
            img = np.array(image_source.convert("RGB"))

        # Detect face bounding boxes using HOG (Histogram of Oriented Gradients)
        face_locations = face_recognition.face_locations(img, model="hog")
        face_count = len(face_locations)

        if face_count == 0:
            return False, None, "No face detected in the photo. Please upload a clear photo of a single person's face."
        
        if face_count > 1:
            return False, None, f"Multiple faces ({face_count}) detected. Please upload a photo containing only one person."

        # Extract 128-d face encodings using the detected bounding box
        encodings = face_recognition.face_encodings(img, known_face_locations=face_locations)
        if not encodings or len(encodings[0]) != 128:
            return False, None, "Failed to generate valid 128-dimensional facial vector."

        encoding_vector = encodings[0]
        return True, encoding_vector, ""

    except Exception as e:
        return False, None, f"Image processing error: {str(e)}"

def serialize_encoding(encoding: np.ndarray) -> str:
    """Convert a 128-d numpy array encoding into a JSON string format for SQLite storage."""
    if encoding is None:
        raise ValueError("Encoding vector cannot be None.")
    return json.dumps(encoding.tolist())

def deserialize_encoding(encoding_data) -> np.ndarray:
    """
    Convert stored JSON string or byte buffer back into a 128-d float64 NumPy array.
    """
    if isinstance(encoding_data, (bytes, bytearray)):
        encoding_data = encoding_data.decode("utf-8")
    
    if isinstance(encoding_data, str):
        # Try JSON parsing first
        try:
            float_list = json.loads(encoding_data)
            return np.array(float_list, dtype=np.float64)
        except json.JSONDecodeError:
            # Fallback for binary numpy buffer bytes if stored directly
            return np.frombuffer(encoding_data.encode("latin1"), dtype=np.float64)
            
    elif isinstance(encoding_data, np.ndarray):
        return encoding_data
    else:
        raise TypeError(f"Unsupported encoding data type: {type(encoding_data)}")

def calculate_face_distance(encoding1: np.ndarray, encoding2: np.ndarray) -> float:
    """Calculate Euclidean distance between two 128-d face encodings."""
    if encoding1 is None or encoding2 is None:
        return 1.0
    return float(np.linalg.norm(encoding1 - encoding2))

def load_enrolled_encodings():
    """
    Fetch all active enrolled personnel and their deserialized 128-d facial encodings from SQLite.
    
    Returns:
        list of dict: [{"person_id": str, "full_name": str, "role": str, "department": str, "encoding": np.ndarray}]
    """
    from core.database import get_db

    enrolled = []
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.person_id, p.full_name, p.role, p.department, fe.encoding_data
                FROM registered_persons p
                JOIN face_encodings fe ON p.person_id = fe.person_id
                WHERE p.is_active = 1
            """)
            rows = cursor.fetchall()

            for row in rows:
                try:
                    encoding_vec = deserialize_encoding(row["encoding_data"])
                    if encoding_vec is not None and len(encoding_vec) == 128:
                        enrolled.append({
                            "person_id": row["person_id"],
                            "full_name": row["full_name"],
                            "role": row["role"],
                            "department": row["department"],
                            "encoding": encoding_vec
                        })
                except Exception as ex:
                    print(f"[WARN] Failed to deserialize encoding for {row['person_id']}: {ex}")

    except Exception as e:
        print(f"[ERROR] Error loading enrolled face encodings from DB: {e}")

    return enrolled

def match_face_encoding(target_encoding: np.ndarray, enrolled_list: list, threshold: float = 0.5) -> tuple:
    """
    Compare a target 128-d face encoding against a list of enrolled encodings.
    
    Returns:
        tuple: (matched: bool, matched_person: dict | None, distance: float)
    """
    if target_encoding is None or not enrolled_list:
        return False, None, 1.0

    best_match = None
    min_distance = 1.0

    for item in enrolled_list:
        dist = calculate_face_distance(target_encoding, item["encoding"])
        if dist < min_distance:
            min_distance = dist
            best_match = item

    if best_match is not None and min_distance <= threshold:
        return True, best_match, min_distance
    else:
        return False, None, min_distance

