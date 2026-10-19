import pickle
import tkinter as tk
from tkinter import messagebox, ttk

import cv2
import face_recognition
import numpy as np

from database import ensure_schema, get_connection, get_student, get_students_with_faces

DB = "students.db"
BLUR_THRESHOLD = 80.0
BRIGHTNESS_THRESHOLD = 45.0
DUPLICATE_FACE_THRESHOLD = 0.5
STABLE_FACE_FRAMES = 5


def frame_quality(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    brightness = float(np.mean(gray))
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    if brightness < BRIGHTNESS_THRESHOLD:
        return False, "Image too dark"
    if sharpness < BLUR_THRESHOLD:
        return False, "Image too blurry"
    return True, "Quality OK"


def find_duplicate_face(new_encoding, current_student_id):
    if new_encoding is None:
        return None
        
    for row in get_students_with_faces():
        if row["student_id"] == current_student_id:
            continue
        try:
            known_encoding = pickle.loads(row["face_encoding"])
        except Exception as e:
            print(f"[DEBUG] Could not load face encoding for {row['student_id']}: {e}")
            continue
        try:
            distance = face_recognition.face_distance([known_encoding], new_encoding)[0]
            print(f"[DEBUG] Face distance for {row['student_id']}: {distance}")
            if distance <= DUPLICATE_FACE_THRESHOLD:
                return row["student_id"], row["name"], distance
        except Exception as e:
            print(f"[DEBUG] Error comparing faces: {e}")
            continue
    return None


def capture_face_encoding():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        messagebox.showerror("Camera Error", "Unable to open camera.")
        return None

    messagebox.showinfo(
        "Face Capture",
        "Camera will open.\n"
        "Keep your face clear and well lit.\n"
        "Press SPACE to save after the quality check passes (green box).\n"
        "Press ESC or Q to cancel.",
    )

    stable_frames = 0
    best_encoding = None

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            quality_ok, quality_text = frame_quality(frame)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            faces = face_recognition.face_locations(rgb)
            encodings = face_recognition.face_encodings(rgb, faces)

            if quality_ok and len(faces) == 1 and encodings:
                stable_frames += 1
                best_encoding = encodings[0]
                status_text = f"{quality_text} | Stability {stable_frames}/{STABLE_FACE_FRAMES}"
                color = (0, 180, 0) if stable_frames >= STABLE_FACE_FRAMES else (0, 165, 255)
                ready_text = "READY - Press SPACE" if stable_frames >= STABLE_FACE_FRAMES else "Stabilizing..."
            elif len(faces) > 1:
                stable_frames = 0
                status_text = "Only one face allowed"
                color = (0, 0, 255)
                ready_text = ""
            else:
                stable_frames = 0
                status_text = quality_text if not quality_ok else "No face detected"
                color = (0, 0, 255)
                ready_text = ""

            # Draw face rectangles
            for top, right, bottom, left in faces:
                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)

            # Draw status text
            cv2.putText(
                frame,
                status_text,
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                color,
                2,
                cv2.LINE_AA,
            )
            
            # Draw ready text if applicable
            if ready_text:
                cv2.putText(
                    frame,
                    ready_text,
                    (20, 80),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 180, 0),
                    3,
                    cv2.LINE_AA,
                )

            cv2.imshow("Face Registration", frame)

            key = cv2.waitKey(30) & 0xFF
            if key == 32:  # SPACE
                if best_encoding is not None and stable_frames >= STABLE_FACE_FRAMES:
                    break
                else:
                    continue  # Just keep going, don't show popup
            elif key == 27 or key == ord("q") or key == ord("Q"):  # ESC or Q
                best_encoding = None
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()

    return best_encoding


def save_student_face(student_id, name, department, encoding):
    ensure_schema()
    existing = get_student(student_id)
    auto_password = "STU" + student_id[-4:]
    enc_blob = pickle.dumps(encoding)

    conn = get_connection()
    try:
        if existing:
            print(f"[DEBUG] Updating existing student: {student_id}")
            conn.execute(
                """
                UPDATE students
                SET name=?, department=?, face_encoding=?,
                    password=COALESCE(password, ?)
                WHERE student_id=?
                """,
                (name, department, enc_blob, auto_password, student_id),
            )
            conn.commit()
            print(f"[DEBUG] Student updated successfully")
        else:
            print(f"[DEBUG] Creating new student: {student_id}")
            conn.execute(
                """
                INSERT INTO students
                (student_id, name, department, face_encoding, password)
                VALUES (?, ?, ?, ?, ?)
                """,
                (student_id, name, department, enc_blob, auto_password),
            )
            conn.commit()
            print(f"[DEBUG] Student created successfully")
        
        # Verify the data was saved
        verify = get_student(student_id)
        print(f"[DEBUG] Verification after save: {verify}")
    except Exception as e:
        conn.rollback()
        print(f"[DEBUG] Error during save: {e}")
        raise
    finally:
        conn.close()

    return auto_password, bool(existing)


def face_registration():
    ensure_schema()
    parent = tk._default_root
    win = tk.Toplevel(parent) if parent else tk.Tk()

    from theme import (
        COLORS,
        FONTS,
        center_window,
        configure_window,
        create_button,
        create_card,
        create_entry,
        create_error_label,
        create_header,
        create_info_label,
        create_separator,
        create_status_strip,
        create_toggle_button,
    )

    configure_window(win, "Face Registration", "620x720")
    win.resizable(False, False)

    create_header(win, "Face Registration", "Register a new student or update an existing face")

    body = tk.Frame(win, bg=COLORS["bg_primary"], padx=28, pady=22)
    body.pack(fill=tk.BOTH, expand=True)

    card, content = create_card(body, "Registration Details")
    card.pack(fill=tk.X)

    form = tk.Frame(content, bg=COLORS["surface"], padx=20, pady=18)
    form.pack(fill=tk.X)

    tk.Label(
        form,
        text="Registration Mode",
        font=FONTS["subheading"],
        bg=COLORS["surface"],
        fg=COLORS["text_primary"],
    ).pack(anchor="w", pady=(0, 8))

    mode_frame, mode_var = create_toggle_button(
        form,
        "New Student",
        "Re-register Existing",
    )
    mode_frame.pack(fill=tk.X, pady=(0, 14))

    create_separator(form)

    sid_frame, sid_entry = create_entry(
        form,
        label_text="Student ID *",
        placeholder="Example: 01",
        width=32,
    )
    sid_frame.pack(fill=tk.X, pady=(0, 12))

    name_frame, name_entry = create_entry(
        form,
        label_text="Student Name *",
        placeholder="Enter full name",
        width=32,
    )
    name_frame.pack(fill=tk.X, pady=(0, 12))

    dept_frame, dept_entry = create_entry(
        form,
        label_text="Department *",
        placeholder="Example: CSE",
        width=32,
    )
    dept_frame.pack(fill=tk.X, pady=(0, 12))

    error_label = create_error_label(form)
    error_label.pack(fill=tk.X, pady=(0, 12))

    create_info_label(
        form,
        "Use New Student for first-time registrations. Use Re-register Existing when a saved face needs to be replaced.",
        bg=COLORS["surface"],
    ).pack(fill=tk.X, pady=(0, 2))

    def register_face():
        sid = sid_entry.get().strip()
        name = name_entry.get().strip()
        dept = dept_entry.get().strip()
        mode = mode_var.get()
        is_new_student = mode == "New Student"

        if not sid or not name or not dept:
            error_label.config(text="All fields are required.")
            return

        error_label.config(text="")

        print(f"[DEBUG] Registration Mode: {mode} | Is New: {is_new_student}")
        print(f"[DEBUG] Attempting to register: SID={sid}, Name={name}, Dept={dept}")

        existing = get_student(sid)
        print(f"[DEBUG] Existing student check: {existing}")

        if is_new_student and existing:
            proceed = messagebox.askyesno(
                "Student Already Exists",
                f"Student ID '{sid}' is already registered as '{existing['name']}'.\n\n"
                "Do you want to update their face instead?",
                parent=win,
            )
            if not proceed:
                error_label.config(
                    text="Cancelled. Use a different Student ID or switch to Re-register Existing."
                )
                return

        if not is_new_student and not existing:
            proceed = messagebox.askyesno(
                "Student Not Found",
                f"Student ID '{sid}' is not registered yet.\n\n"
                "Do you want to create a new student record?",
                parent=win,
            )
            if not proceed:
                error_label.config(text="Cancelled. Switch to New Student to create a record.")
                return

        print("[DEBUG] Starting face capture...")
        encoding = capture_face_encoding()

        if encoding is None:
            print("[DEBUG] Face capture cancelled or failed")
            error_label.config(text="Face registration was cancelled.")
            return

        print("[DEBUG] Face captured successfully. Checking for duplicates...")
        duplicate = find_duplicate_face(encoding, sid)
        if duplicate:
            dup_id, dup_name, distance = duplicate
            messagebox.showerror(
                "Duplicate Face",
                f"This face is already registered for {dup_name} ({dup_id}).\n"
                f"Distance: {distance:.3f}\n\n"
                "Please verify you are registering the correct person.",
                parent=win,
            )
            return

        print("[DEBUG] Saving face to database...")
        try:
            password, updated = save_student_face(sid, name, dept, encoding)
            print(f"[DEBUG] Save successful: Password={password}, Updated={updated}")

            if updated:
                title = "Face Updated Successfully"
                message = (
                    "Student face has been updated.\n\n"
                    f"Student ID: {sid}\n"
                    f"Name: {name}\n"
                    f"Password: {password}"
                )
            else:
                title = "Student Registered Successfully"
                message = (
                    "New student registered successfully.\n\n"
                    f"Student ID: {sid}\n"
                    f"Name: {name}\n"
                    f"Password: {password}\n\n"
                    "Share this password with the student securely."
                )

            messagebox.showinfo(title, message, parent=win)

            sid_entry.delete(0, tk.END)
            name_entry.delete(0, tk.END)
            dept_entry.delete(0, tk.END)
            error_label.config(text="")
            sid_entry.focus_set()
        except Exception as e:
            print(f"[DEBUG] Error saving face: {e}")
            error_label.config(text=f"Error: {e}")

    button_frame = tk.Frame(body, bg=COLORS["bg_primary"])
    button_frame.pack(fill=tk.X, pady=(18, 0))

    create_button(
        button_frame,
        "Capture Face and Register",
        register_face,
        "primary",
        width=30,
    ).pack(fill=tk.X, pady=(0, 8))

    create_button(
        button_frame,
        "Close",
        win.destroy,
        "outline",
        width=30,
    ).pack(fill=tk.X)

    create_status_strip(
        body,
        "Camera capture opens in a separate window. Keep one face centered, clear, and well lit before saving.",
        "primary",
    ).pack(fill=tk.X, pady=(16, 0))

    sid_entry.focus_set()
    center_window(win)

    if parent is None:
        win.mainloop()


if __name__ == "__main__":
    face_registration()
