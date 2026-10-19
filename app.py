from datetime import datetime
import tkinter as tk

from database import ensure_schema, get_connection
from face_registration import face_registration
from manage_timetable import manage_timetable_window
from student_login import student_login_window
from teacher_login import teacher_login_window
from theme import (
    COLORS,
    FONTS,
    center_window,
    configure_window,
    create_button,
    create_card,
    create_header,
    create_info_label,
)


def system_snapshot():
    ensure_schema()
    conn = get_connection()
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        faces = conn.execute(
            "SELECT COUNT(*) FROM students WHERE face_encoding IS NOT NULL"
        ).fetchone()[0]
        teachers = conn.execute("SELECT COUNT(*) FROM teachers").fetchone()[0]
        classes = conn.execute("SELECT COUNT(*) FROM timetable").fetchone()[0]
        today_records = conn.execute(
            "SELECT COUNT(*) FROM attendance WHERE date=?",
            (today,),
        ).fetchone()[0]
    finally:
        conn.close()

    return {
        "Students": students,
        "Faces": faces,
        "Teachers": teachers,
        "Classes": classes,
        "Today": today_records,
    }


def make_stat(parent, label, value):
    frame = tk.Frame(parent, bg=COLORS["surface"], padx=12, pady=10)
    frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

    tk.Label(
        frame,
        text=str(value),
        font=("Segoe UI", 18, "bold"),
        bg=COLORS["surface"],
        fg=COLORS["primary"],
    ).pack(anchor="w")
    tk.Label(
        frame,
        text=label,
        font=FONTS["small"],
        bg=COLORS["surface"],
        fg=COLORS["text_secondary"],
    ).pack(anchor="w", pady=(2, 0))


def make_action_card(parent, title, description, button_text, command, style):
    card, content = create_card(parent, title)
    card.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

    inner = tk.Frame(content, bg=COLORS["surface"], padx=18, pady=16)
    inner.pack(fill=tk.BOTH, expand=True)

    create_info_label(
        inner,
        description,
        bg=COLORS["surface"],
    ).pack(fill=tk.X, anchor="w")

    tk.Frame(inner, bg=COLORS["surface"]).pack(fill=tk.BOTH, expand=True)
    create_button(inner, button_text, command, style, width=22).pack(fill=tk.X, pady=(14, 0))


def build_app():
    ensure_schema()

    root = tk.Tk()
    configure_window(root, "Facial Recognition Attendance System", "920x640")
    root.minsize(860, 600)

    create_header(
        root,
        "Attendance System",
        "Face recognition, timetable management, and attendance reporting",
        datetime.now().strftime("%d %b %Y"),
    )

    main = tk.Frame(root, bg=COLORS["bg_primary"])
    main.pack(fill=tk.BOTH, expand=True, padx=22, pady=18)

    stats_card, stats_content = create_card(main, "System Overview")
    stats_card.pack(fill=tk.X, pady=(0, 14))

    stats = tk.Frame(stats_content, bg=COLORS["surface"], padx=12, pady=12)
    stats.pack(fill=tk.X)
    for label, value in system_snapshot().items():
        make_stat(stats, label, value)

    actions = tk.Frame(main, bg=COLORS["bg_primary"])
    actions.pack(fill=tk.BOTH, expand=True)
    actions.columnconfigure(0, weight=1)
    actions.columnconfigure(1, weight=1)
    actions.rowconfigure(0, weight=1)
    actions.rowconfigure(1, weight=1)

    student_area = tk.Frame(actions, bg=COLORS["bg_primary"])
    student_area.grid(row=0, column=0, sticky="nsew")
    make_action_card(
        student_area,
        "Student Portal",
        "Students can sign in to review attendance history, filter records, and export their data.",
        "Open Student Login",
        student_login_window,
        "primary",
    )

    teacher_area = tk.Frame(actions, bg=COLORS["bg_primary"])
    teacher_area.grid(row=0, column=1, sticky="nsew")
    make_action_card(
        teacher_area,
        "Teacher Workspace",
        "Teachers can start facial attendance, mark manual attendance, and review reports.",
        "Open Teacher Login",
        teacher_login_window,
        "secondary",
    )

    registration_area = tk.Frame(actions, bg=COLORS["bg_primary"])
    registration_area.grid(row=1, column=0, sticky="nsew")
    make_action_card(
        registration_area,
        "Face Registration",
        "Register new students, update an existing face, and protect against duplicate face records.",
        "Register Student Face",
        face_registration,
        "success",
    )

    timetable_area = tk.Frame(actions, bg=COLORS["bg_primary"])
    timetable_area.grid(row=1, column=1, sticky="nsew")
    make_action_card(
        timetable_area,
        "Class Timetable",
        "Add, update, or remove scheduled classes used by automatic attendance marking.",
        "Manage Timetable",
        manage_timetable_window,
        "warning",
    )

    footer = tk.Frame(root, bg=COLORS["bg_tertiary"], height=42)
    footer.pack(fill=tk.X, side=tk.BOTTOM)
    footer.pack_propagate(False)
    tk.Label(
        footer,
        text="Facial Recognition Attendance System v2.0",
        font=FONTS["small"],
        bg=COLORS["bg_tertiary"],
        fg=COLORS["text_secondary"],
    ).pack(side=tk.LEFT, padx=22)
    tk.Label(
        footer,
        text="Ready",
        font=FONTS["small"],
        bg=COLORS["bg_tertiary"],
        fg=COLORS["success"],
    ).pack(side=tk.RIGHT, padx=22)

    center_window(root)
    return root


if __name__ == "__main__":
    build_app().mainloop()
