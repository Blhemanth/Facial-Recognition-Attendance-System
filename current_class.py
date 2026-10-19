import tkinter as tk
from datetime import datetime

from theme import (
    COLORS,
    FONTS,
    center_window,
    configure_window,
    create_button,
    create_card,
    create_header,
)
from timetable import format_entry, get_current_class


def show_current_class():
    parent = tk._default_root
    win = tk.Toplevel(parent) if parent else tk.Tk()
    configure_window(win, "Current Class", "480x330")
    win.resizable(False, False)

    create_header(win, "Current Class", "Live timetable status")

    body = tk.Frame(win, bg=COLORS["bg_primary"], padx=26, pady=22)
    body.pack(fill=tk.BOTH, expand=True)

    card, content = create_card(body, "Now")
    card.pack(fill=tk.BOTH, expand=True)

    panel = tk.Frame(content, bg=COLORS["surface"], padx=18, pady=18)
    panel.pack(fill=tk.BOTH, expand=True)

    time_label = tk.Label(
        panel,
        text="",
        bg=COLORS["surface"],
        fg=COLORS["text_secondary"],
        font=FONTS["small"],
        anchor="w",
    )
    time_label.pack(anchor="w", fill=tk.X)

    subject_label = tk.Label(
        panel,
        text="",
        font=("Segoe UI", 16, "bold"),
        bg=COLORS["surface"],
        fg=COLORS["success"],
        wraplength=390,
        justify=tk.LEFT,
        anchor="w",
    )
    subject_label.pack(anchor="w", fill=tk.X, pady=(16, 8))

    details_label = tk.Label(
        panel,
        text="",
        font=FONTS["normal"],
        bg=COLORS["surface"],
        fg=COLORS["text_secondary"],
        wraplength=390,
        justify=tk.LEFT,
        anchor="w",
    )
    details_label.pack(anchor="w", fill=tk.X)

    def refresh():
        active = get_current_class()
        time_label.config(text=datetime.now().strftime("%A, %d %B %Y  %I:%M:%S %p"))
        if active:
            subject_label.config(text=active.subject, fg=COLORS["success"])
            details_label.config(
                text=f"{format_entry(active)}\nTeacher: {active.teacher_id or 'N/A'}"
            )
        else:
            subject_label.config(text="No class is scheduled right now", fg=COLORS["error"])
            details_label.config(text="Open Timetable Management to add or review today's classes.")
        win.after(1000, refresh)

    create_button(body, "Close", win.destroy, "outline").pack(fill=tk.X, pady=(16, 0))

    refresh()
    center_window(win)

    if parent is None:
        win.mainloop()


if __name__ == "__main__":
    show_current_class()
