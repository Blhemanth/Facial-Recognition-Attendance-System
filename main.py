import logging
import pickle
import sys
from tkinter import Tk, messagebox

import cv2
import face_recognition

from attendance_service import mark_attendance
from database import ensure_schema, get_students_with_faces
from face_engine import FACE_MATCH_THRESHOLD, match_face
from timetable import get_attendance_context

logging.basicConfig(
    filename="attendance.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


def load_known_faces():
    ensure_schema()
    known_encodings = []
    student_ids = []
    student_names = []

    for row in get_students_with_faces():
        try:
            known_encodings.append(pickle.loads(row["face_encoding"]))
            student_ids.append(row["student_id"])
            student_names.append(row["name"])
        except Exception:
            logging.exception("Skipping invalid face encoding for %s", row["student_id"])

    return known_encodings, student_ids, student_names


def draw_status(frame, text, color=(255, 255, 255), y=30):
    cv2.putText(
        frame,
        text,
        (20, y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        color,
        2,
        cv2.LINE_AA,
    )


def preprocess_frame(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    equalized = cv2.equalizeHist(gray)
    return cv2.cvtColor(equalized, cv2.COLOR_GRAY2RGB)


def show_success_popup(result, popup_root):
    popup_root.withdraw()
    messagebox.showinfo(
        "Attendance Marked",
        f"{result.status}: {result.name}\n"
        f"Subject: {result.subject}\n"
        f"Time: {result.time}",
        parent=popup_root,
    )


def start_facial_attendance():
    known_encodings, student_ids, student_names = load_known_faces()
    if not known_encodings:
        messagebox.showerror(
            "No Registered Faces",
            "No student face encodings are registered yet.",
        )
        return

    video = cv2.VideoCapture(0)
    if not video.isOpened():
        messagebox.showerror("Camera Error", "Unable to open camera.")
        return

    popup_root = Tk()
    popup_root.withdraw()
    popup_shown_for = set()

    logging.info("Facial attendance started")
    print("Facial Attendance Started. Press ESC or Q to stop.")

    while True:
        ret, frame = video.read()
        if not ret:
            continue

        context = get_attendance_context()
        if context.can_mark:
            color = (0, 180, 0) if context.status == "Present" else (0, 165, 255)
            draw_status(frame, context.message, color, 30)
            draw_status(frame, f"Status: {context.status}", color, 60)
        else:
            draw_status(frame, context.message, (0, 0, 255), 30)

        rgb_frame = preprocess_frame(frame)
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            if not context.can_mark:
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
                cv2.putText(
                    frame,
                    "No active class",
                    (left, max(20, top - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (0, 0, 255),
                    2,
                )
                continue

            index, is_match, distance, confidence = match_face(
                known_encodings,
                face_encoding,
                threshold=FACE_MATCH_THRESHOLD,
            )

            if not is_match or index is None:
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
                cv2.putText(
                    frame,
                    "Unknown Face",
                    (left, max(20, top - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (0, 0, 255),
                    2,
                )
                logging.warning("Unknown face detected. Distance: %.3f", distance)
                continue

            student_id = student_ids[index]
            name = student_names[index]
            result = mark_attendance(
                student_id=student_id,
                status=context.status,
                confidence=confidence,
                class_info=context.current_class,
            )

            if result.success:
                color = (0, 255, 0)
                label = f"{result.status}: {name} ({confidence:.1f}%)"
                logging.info(
                    "Attendance marked: %s %s %s %.2f",
                    student_id,
                    result.subject,
                    result.status,
                    confidence,
                )
                popup_key = (result.student_id, result.date, result.subject)
                if popup_key not in popup_shown_for:
                    popup_shown_for.add(popup_key)
                    show_success_popup(result, popup_root)
            elif result.duplicate:
                color = (0, 165, 255)
                label = f"Already marked: {name}"
            else:
                color = (0, 0, 255)
                label = result.message

            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            cv2.putText(
                frame,
                label,
                (left, max(20, top - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                color,
                2,
            )

        cv2.imshow("Facial Recognition Attendance System", frame)

        key = cv2.waitKey(1) & 0xFF
        if key in (27, ord("q")):
            break

    video.release()
    cv2.destroyAllWindows()
    popup_root.destroy()
    logging.info("Facial attendance stopped")


if __name__ == "__main__":
    try:
        start_facial_attendance()
    except KeyboardInterrupt:
        sys.exit(0)
