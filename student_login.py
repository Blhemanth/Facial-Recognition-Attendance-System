import sqlite3
import tkinter as tk

from database import ensure_schema
from student_dashboard import open_student_dashboard
from theme import (
    COLORS,
    center_window,
    configure_window,
    create_button,
    create_card,
    create_entry,
    create_error_label,
    create_header,
    create_status_strip,
)


def _valid_parent():
    try:
        parent = tk._default_root
        return parent if parent and parent.winfo_exists() else None
    except tk.TclError:
        return None


def student_login_window():
    ensure_schema()

    parent = _valid_parent()
    win = tk.Toplevel(parent) if parent else tk.Tk()
    configure_window(win, "Student Login", "520x560")
    win.resizable(False, False)

    create_header(win, "Student Login", "Open your attendance dashboard")

    body = tk.Frame(win, bg=COLORS["bg_primary"], padx=28, pady=24)
    body.pack(fill=tk.BOTH, expand=True)

    card, content = create_card(body, "Account Details")
    card.pack(fill=tk.X)

    form = tk.Frame(content, bg=COLORS["surface"], padx=20, pady=20)
    form.pack(fill=tk.X)

    sid_frame, sid_entry = create_entry(
        form,
        label_text="Student ID",
        placeholder="Example: 01",
        width=28,
    )
    sid_frame.pack(fill=tk.X, pady=(0, 16))

    pwd_frame, pwd_entry = create_entry(
        form,
        label_text="Password",
        placeholder="Enter password",
        width=28,
        is_password=True,
    )
    pwd_frame.pack(fill=tk.X, pady=(0, 12))

    error_label = create_error_label(form)
    error_label.pack(fill=tk.X, pady=(0, 14))

    def login():
        student_id = sid_entry.get().strip()
        password = pwd_entry.get().strip()

        if not student_id or not password:
            error_label.config(text="All fields are required.")
            return

        conn = sqlite3.connect("students.db")
        cur = conn.cursor()
        cur.execute(
            "SELECT name FROM students WHERE student_id=? AND password=?",
            (student_id, password),
        )
        row = cur.fetchone()
        conn.close()

        if row:
            win.destroy()
            open_student_dashboard(student_id, row[0])
        else:
            error_label.config(text="Invalid Student ID or password.")

    buttons = tk.Frame(form, bg=COLORS["surface"])
    buttons.pack(fill=tk.X)
    create_button(buttons, "Login to Dashboard", login, "primary").pack(fill=tk.X, pady=(0, 8))
    create_button(buttons, "Cancel", win.destroy, "outline").pack(fill=tk.X)

    create_status_strip(
        body,
        "Default password format: STU + last 4 digits of the student ID. Example: ID 0001 uses STU0001.",
        "primary",
    ).pack(fill=tk.X, pady=(18, 0))

    sid_entry.bind("<Return>", lambda _event: login())
    pwd_entry.bind("<Return>", lambda _event: login())
    sid_entry.focus_set()

    center_window(win)

    if parent is None:
        win.mainloop()
