import csv
import os
import tkinter as tk

from database import ensure_schema, get_connection
from teacher_dashboard import teacher_dashboard
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


def _teacher_from_csv(username, password):
    if not os.path.exists("teachers.csv"):
        return None
    with open("teachers.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if (
                (row.get("username") or "").strip() == username
                and (row.get("password") or "").strip() == password
            ):
                return row
    return None


def _teacher_from_database(username, password):
    conn = get_connection()
    try:
        return conn.execute(
            """
            SELECT teacher_id, name, username
            FROM teachers
            WHERE username=? AND password=?
            """,
            (username, password),
        ).fetchone()
    finally:
        conn.close()


def _valid_parent():
    try:
        parent = tk._default_root
        return parent if parent and parent.winfo_exists() else None
    except tk.TclError:
        return None


def teacher_login_window():
    ensure_schema()

    parent = _valid_parent()
    win = tk.Toplevel(parent) if parent else tk.Tk()
    configure_window(win, "Teacher Login", "520x560")
    win.resizable(False, False)

    create_header(win, "Teacher Login", "Manage attendance, classes, and reports")

    body = tk.Frame(win, bg=COLORS["bg_primary"], padx=28, pady=24)
    body.pack(fill=tk.BOTH, expand=True)

    card, content = create_card(body, "Teacher Credentials")
    card.pack(fill=tk.X)

    form = tk.Frame(content, bg=COLORS["surface"], padx=20, pady=20)
    form.pack(fill=tk.X)

    uid_frame, uid_entry = create_entry(
        form,
        label_text="Username",
        placeholder="Enter username",
        width=28,
    )
    uid_frame.pack(fill=tk.X, pady=(0, 16))

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
        username = uid_entry.get().strip()
        password = pwd_entry.get().strip()

        if not username or not password:
            error_label.config(text="All fields are required.")
            return

        try:
            teacher = _teacher_from_csv(username, password) or _teacher_from_database(
                username,
                password,
            )
        except Exception as exc:
            error_label.config(text=f"Login error: {exc}")
            return

        if teacher:
            win.destroy()
            teacher_dashboard()
        else:
            error_label.config(text="Invalid username or password.")

    buttons = tk.Frame(form, bg=COLORS["surface"])
    buttons.pack(fill=tk.X)
    create_button(buttons, "Login to Dashboard", login, "primary").pack(fill=tk.X, pady=(0, 8))
    create_button(buttons, "Cancel", win.destroy, "outline").pack(fill=tk.X)

    create_status_strip(
        body,
        "Use the teacher credentials saved in the database or teachers.csv.",
        "primary",
    ).pack(fill=tk.X, pady=(18, 0))

    uid_entry.bind("<Return>", lambda _event: login())
    pwd_entry.bind("<Return>", lambda _event: login())
    uid_entry.focus_set()

    center_window(win)

    if parent is None:
        win.mainloop()
