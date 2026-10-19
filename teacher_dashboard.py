import os
import subprocess
import sys
import tkinter as tk
from datetime import datetime
from tkinter import messagebox

from current_class import show_current_class
from face_registration import face_registration
from manage_timetable import manage_timetable_window
from remove_face_ui import remove_face_window
from teacher_manual import teacher_panel
from teacher_reports import teacher_reports
from theme import (
    COLORS,
    FONTS,
    center_window,
    configure_window,
    create_card,
    create_ttk_button,
)
from timetable import format_entry, get_current_class


def teacher_dashboard():
    try:
        parent = tk._default_root if tk._default_root and tk._default_root.winfo_exists() else None
    except tk.TclError:
        parent = None

    win = tk.Toplevel(parent) if parent else tk.Tk()
    configure_window(win, "Teacher Dashboard", "980x640")
    win.minsize(900, 560)

    header = tk.Frame(win, bg=COLORS["primary_dark"], height=92)
    header.pack(fill=tk.X)
    header.pack_propagate(False)

    title_area = tk.Frame(header, bg=COLORS["primary_dark"])
    title_area.pack(side=tk.LEFT, padx=24, pady=14)
    tk.Label(
        title_area,
        text="Teacher Dashboard",
        bg=COLORS["primary_dark"],
        fg=COLORS["text_light"],
        font=FONTS["title"],
    ).pack(anchor="w")
    tk.Label(
        title_area,
        text="Run attendance, manage schedules, and review records",
        bg=COLORS["primary_dark"],
        fg="#dce6f2",
        font=FONTS["small"],
    ).pack(anchor="w", pady=(4, 0))

    header_status = tk.Frame(header, bg=COLORS["primary_dark"])
    header_status.pack(side=tk.RIGHT, padx=24, pady=16)

    time_label = tk.Label(
        header_status,
        text="",
        bg=COLORS["primary_dark"],
        fg="#dce6f2",
        font=FONTS["small"],
        anchor="e",
    )
    time_label.pack(anchor="e")
    class_label = tk.Label(
        header_status,
        text="",
        bg=COLORS["primary_dark"],
        fg=COLORS["text_light"],
        font=FONTS["subheading"],
        anchor="e",
    )
    class_label.pack(anchor="e", pady=(6, 0))

    body = tk.Frame(win, bg=COLORS["bg_primary"], padx=18, pady=16)
    body.pack(fill=tk.BOTH, expand=True)

    actions_card, actions_content = create_card(body, "Teacher Actions")
    actions_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    actions_grid = tk.Frame(actions_content, bg=COLORS["surface"], padx=14, pady=14)
    actions_grid.pack(fill=tk.BOTH, expand=True)
    for col in range(2):
        actions_grid.columnconfigure(col, weight=1)
    for row in range(5):
        actions_grid.rowconfigure(row, weight=1)

    live_card, live_content = create_card(body, "Live Class")
    live_card.pack(side=tk.RIGHT, fill=tk.Y, padx=(14, 0))
    live = tk.Frame(live_content, bg=COLORS["surface"], padx=18, pady=18, width=280)
    live.pack(fill=tk.BOTH, expand=True)
    live.pack_propagate(False)

    live_subject = tk.Label(
        live,
        text="",
        font=("Segoe UI", 17, "bold"),
        bg=COLORS["surface"],
        fg=COLORS["success"],
        wraplength=235,
        justify=tk.LEFT,
        anchor="w",
    )
    live_subject.pack(anchor="w", fill=tk.X, pady=(2, 10))

    live_detail = tk.Label(
        live,
        text="",
        font=FONTS["normal"],
        bg=COLORS["surface"],
        fg=COLORS["text_secondary"],
        wraplength=235,
        justify=tk.LEFT,
        anchor="w",
    )
    live_detail.pack(anchor="w", fill=tk.X)

    tk.Frame(live, bg=COLORS["surface"]).pack(fill=tk.BOTH, expand=True)
    tk.Label(
        live,
        text="Automatic attendance follows the currently active timetable class.",
        font=FONTS["small"],
        bg=COLORS["surface"],
        fg=COLORS["text_muted"],
        wraplength=235,
        justify=tk.LEFT,
        anchor="w",
    ).pack(anchor="w", fill=tk.X)

    def start_attendance():
        try:
            subprocess.Popen(
                [sys.executable, "main.py"],
                cwd=os.path.dirname(os.path.abspath(__file__)),
            )
        except Exception as exc:
            messagebox.showerror("Attendance Error", str(exc), parent=win)

    def coming_soon(title):
        messagebox.showinfo(
            title,
            "This placeholder is ready for project extension.",
            parent=win,
        )

    actions = [
        ("Start Facial Attendance", start_attendance, "primary"),
        ("Manual Attendance", teacher_panel, "secondary"),
        ("Timetable Management", manage_timetable_window, "warning"),
        ("View Current Class", show_current_class, "ghost"),
        ("Attendance Reports", teacher_reports, "success"),
        ("Face Re-registration", face_registration, "primary"),
        ("Remove Student Face", remove_face_window, "danger"),
        ("Search Student Attendance", teacher_reports, "ghost"),
        ("Low Attendance Students", teacher_reports, "ghost"),
        ("Email Notification Placeholder", lambda: coming_soon("Email Notifications"), "outline"),
    ]

    for index, (text, command, style) in enumerate(actions):
        row = index // 2
        column = index % 2
        create_ttk_button(actions_grid, text, command, style).grid(
            row=row,
            column=column,
            sticky="nsew",
            padx=7,
            pady=7,
        )

    def refresh_header():
        active = get_current_class()
        time_label.config(text=datetime.now().strftime("%A, %d %B %Y  %I:%M:%S %p"))
        if active:
            class_label.config(text=f"Current: {format_entry(active)}")
            live_subject.config(text=active.subject, fg=COLORS["success"])
            live_detail.config(
                text=(
                    f"Day: {active.day}\n"
                    f"Time: {active.start_time} - {active.end_time}\n"
                    f"Teacher: {active.teacher_id or 'N/A'}"
                )
            )
        else:
            class_label.config(text="Current: No active class")
            live_subject.config(text="No active class", fg=COLORS["error"])
            live_detail.config(text="Open Timetable Management to add or view today's classes.")
        win.after(1000, refresh_header)

    refresh_header()
    center_window(win)

    if parent is None:
        win.mainloop()


if __name__ == "__main__":
    teacher_dashboard()
