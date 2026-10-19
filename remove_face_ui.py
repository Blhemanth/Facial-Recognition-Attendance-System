import sqlite3
import tkinter as tk
from tkinter import messagebox

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

DB = "students.db"


def remove_face_window():
    parent = tk._default_root
    win = tk.Toplevel(parent) if parent else tk.Tk()
    configure_window(win, "Remove Registered Face", "460x420")
    win.resizable(False, False)

    create_header(win, "Remove Face", "Clear a saved face encoding for a student")

    body = tk.Frame(win, bg=COLORS["bg_primary"], padx=26, pady=22)
    body.pack(fill=tk.BOTH, expand=True)

    card, content = create_card(body, "Student Lookup")
    card.pack(fill=tk.X)
    form = tk.Frame(content, bg=COLORS["surface"], padx=18, pady=18)
    form.pack(fill=tk.X)

    sid_frame, sid_entry = create_entry(
        form,
        label_text="Student ID",
        placeholder="Example: 01",
        width=24,
    )
    sid_frame.pack(fill=tk.X, pady=(0, 12))

    error_label = create_error_label(form)
    error_label.pack(fill=tk.X, pady=(0, 12))

    def remove_face():
        sid = sid_entry.get().strip()
        error_label.config(text="")

        if not sid:
            error_label.config(text="Student ID is required.")
            return

        conn = sqlite3.connect(DB)
        cur = conn.cursor()

        cur.execute(
            """
            SELECT face_encoding FROM students WHERE student_id=?
            """,
            (sid,),
        )
        row = cur.fetchone()

        if not row:
            messagebox.showerror("Error", "Student not found", parent=win)
            conn.close()
            return

        if row[0] is None:
            messagebox.showinfo("Info", "No face is registered for this student", parent=win)
            conn.close()
            return

        if not messagebox.askyesno("Confirm", "Remove the registered face for this student?", parent=win):
            conn.close()
            return

        cur.execute(
            """
            UPDATE students
            SET face_encoding = NULL
            WHERE student_id=?
            """,
            (sid,),
        )

        conn.commit()
        conn.close()

        messagebox.showinfo("Success", "Registered face removed successfully", parent=win)
        sid_entry.delete(0, tk.END)
        sid_entry.focus_set()

    buttons = tk.Frame(body, bg=COLORS["bg_primary"])
    buttons.pack(fill=tk.X, pady=(18, 0))
    create_button(buttons, "Remove Face", remove_face, "danger").pack(fill=tk.X, pady=(0, 8))
    create_button(buttons, "Close", win.destroy, "outline").pack(fill=tk.X)

    create_status_strip(
        body,
        "This only removes the face encoding. The student record and attendance history remain intact.",
        "warning",
    ).pack(fill=tk.X, pady=(16, 0))

    sid_entry.focus_set()
    center_window(win)

    if parent is None:
        win.mainloop()
