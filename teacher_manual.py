import tkinter as tk
from tkinter import messagebox, ttk

from attendance_service import mark_manual_attendance
from theme import (
    COLORS,
    FONTS,
    center_window,
    configure_window,
    create_button,
    create_card,
    create_header,
    create_status_strip,
)
from timetable import get_current_class


def teacher_panel():
    parent = tk._default_root
    win = tk.Toplevel(parent) if parent else tk.Tk()
    configure_window(win, "Manual Attendance", "480x430")
    win.resizable(False, False)

    active = get_current_class()

    create_header(win, "Manual Attendance", "Mark a student without camera recognition")

    body = tk.Frame(win, bg=COLORS["bg_primary"], padx=26, pady=22)
    body.pack(fill=tk.BOTH, expand=True)

    card, content = create_card(body, "Attendance Details")
    card.pack(fill=tk.X)
    form = tk.Frame(content, bg=COLORS["surface"], padx=18, pady=18)
    form.pack(fill=tk.X)

    student_var = tk.StringVar()
    subject_var = tk.StringVar(value=active.subject if active else "")
    status_var = tk.StringVar(value="Present")

    def field(label, variable):
        tk.Label(
            form,
            text=label,
            bg=COLORS["surface"],
            fg=COLORS["text_primary"],
            font=FONTS["small"],
        ).pack(anchor="w")
        entry = ttk.Entry(form, textvariable=variable)
        entry.pack(fill=tk.X, pady=(4, 12))
        return entry

    student_entry = field("Student ID", student_var)
    field("Subject", subject_var)

    tk.Label(
        form,
        text="Attendance Status",
        bg=COLORS["surface"],
        fg=COLORS["text_primary"],
        font=FONTS["small"],
    ).pack(anchor="w")
    ttk.Combobox(
        form,
        textvariable=status_var,
        values=("Present", "Late", "Absent"),
        state="readonly",
    ).pack(fill=tk.X, pady=(4, 14))

    if active:
        create_status_strip(
            form,
            f"Active class detected: {active.subject} ({active.start_time}-{active.end_time})",
            "success",
        ).pack(fill=tk.X, pady=(0, 12))

    def submit():
        result = mark_manual_attendance(
            student_id=student_var.get(),
            subject=subject_var.get(),
            status=status_var.get(),
        )
        if result.success:
            messagebox.showinfo("Success", result.message, parent=win)
            student_var.set("")
            student_entry.focus_set()
        else:
            messagebox.showerror("Attendance Error", result.message, parent=win)

    buttons = tk.Frame(body, bg=COLORS["bg_primary"])
    buttons.pack(fill=tk.X, pady=(18, 0))
    create_button(buttons, "Mark Attendance", submit, "primary").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
    create_button(buttons, "Close", win.destroy, "outline").pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(6, 0))

    student_entry.focus_set()
    center_window(win)

    if parent is None:
        win.mainloop()


if __name__ == "__main__":
    teacher_panel()
