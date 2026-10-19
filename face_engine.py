import face_recognition
import cv2
import numpy as np

FACE_MATCH_THRESHOLD = 0.6

def encode_face(image):
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    encodings = face_recognition.face_encodings(rgb)
    return encodings[0] if encodings else None

def confidence_from_distance(distance, threshold=FACE_MATCH_THRESHOLD):
    if distance is None or np.isinf(distance):
        return 0.0
    confidence = max(0.0, (1.0 - (distance / max(threshold, 0.01))) * 100.0)
    return round(confidence, 2)


def match_face(known_encodings, unknown_encoding, threshold=FACE_MATCH_THRESHOLD):
    if unknown_encoding is None or not known_encodings:
        return None, False, float("inf"), 0.0

    distances = face_recognition.face_distance(known_encodings, unknown_encoding)
    if len(distances) == 0:
        return None, False, float("inf"), 0.0

    min_dist = np.min(distances)
    is_match = min_dist <= threshold
    return np.argmin(distances), is_match, min_dist, confidence_from_distance(min_dist, threshold)
