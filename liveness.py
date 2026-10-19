from scipy.spatial import distance
import dlib

EYE_AR_THRESH = 0.25
EYE_AR_CONSEC_FRAMES = 2

def eye_aspect_ratio(eye):
    A = distance.euclidean(eye[1], eye[5])
    B = distance.euclidean(eye[2], eye[4])
    C = distance.euclidean(eye[0], eye[3])
    return (A + B) / (2.0 * C)
