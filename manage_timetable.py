import tkinter as tk
from tkinter import messagebox, ttk

from database import ensure_schema, get_connection
from theme import (
    COLORS,
    FONTS,
    center_window,
    configure_window,
    create_card,
    create_ttk_button,
)
from timetable import (
    DAYS,
    TimetableConflictError,
    delete_timetable_entry,
    format_entry,
    get_all_timetable,
    get_current_class,
    get_today_timetable,
    save_timetable_entry,
    today_name,
)


def _teacher_options():
    ensure_schema()
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT teacher_id, COALESCE(name, username, '') AS label
            FROM teachers
            ORDER BY teacher_id
            """
        ).fetchall()
    finally:
        conn.close()

    options = [""]
    for row in rows:
        teacher_id = row["teacher_id"]
        label = row["label"]
        options.append(f"{teacher_id} - {label}" if label else teacher_id)
    return options


def _teacher_id_from_option(value):
    value = (value or "").strip()
    if not value:
        return ""
    return value.split(" - ", 1)[0].strip()


def _teacher_option_for_id(teacher_id, options):
    teacher_id = (teacher_id or "").strip()
    if not teacher_id:
        return ""
    for option in options:
        if _teacher_id_from_option(option) == teacher_id:
            return option
    return teacher_id


def manage_timetable_window():
    parent = tk._default_root
    win = tk.Toplevel(parent) if parent else tk.Tk()
    configure_window(win, "Timetable Management", "1040x650")
    win.minsize(940, 580)

    selected_class_id = tk.StringVar()
    subject_var = tk.StringVar()
    day_var = tk.StringVar(value=today_name())
    start_var = tk.StringVar()
    end_var = tk.StringVar()
    teacher_var = tk.StringVar()
    teacher_options = _teacher_options()

    header = tk.Frame(win, bg=COLORS["primary_dark"], height=88)
    header.pack(fill=tk.X)
    header.pack_propagate(False)

    title_area = tk.Frame(header, bg=COLORS["primary_dark"])
    title_area.pack(side=tk.LEFT, padx=24, pady=14)
    tk.Label(
        title_area,
        text="Timetable Management",
        font=FONTS["title"],
        fg=COLORS["text_light"],
        bg=COLORS["primary_dark"],
    ).pack(anchor="w")
    tk.Label(
        title_area,
        text="Create and maintain class schedules for attendance automation",
        font=FONTS["small"],
        fg="#dce6f2",
        bg=COLORS["primary_dark"],
    ).pack(anchor="w", pady=(4, 0))

    current_label = tk.Label(
        header,
        text="",
        font=FONTS["subheading"],
        fg="#dce6f2",
        bg=COLORS["primary_dark"],
        anchor="e",
    )
    current_label.pack(side=tk.RIGHT, padx=24)

    body = tk.Frame(win, bg=COLORS["bg_primary"], padx=18, pady=16)
    body.pack(fill=tk.BOTH, expand=True)

    form_card, form_content = create_card(body, "Class Details")
    form_card.pack(fill=tk.X, pady=(0, 14))
    form = tk.Frame(form_content, bg=COLORS["surface"], padx=14, pady=14)
    form.pack(fill=tk.X)

    def add_field(label, variable, row, column, widget="entry", values=None):
        tk.Label(
            form,
            text=label,
            bg=COLORS["surface"],
            fg=COLORS["text_primary"],
            font=FONTS["small"],
        ).grid(row=row, column=column, sticky="w", padx=6)
        if widget == "combo":
            entry = ttk.Combobox(form, textvariable=variable, values=values, state="readonly")
        else:
            entry = ttk.Entry(form, textvariable=variable)
        entry.grid(row=row + 1, column=column, sticky="ew", padx=6, pady=(4, 10))
        return entry

    for col in range(5):
        form.columnconfigure(col, weight=1)

    add_field("Subject", subject_var, 0, 0)
    add_field("Day", day_var, 0, 1, widget="combo", values=DAYS)
    add_field("Start Time (HH:MM)", start_var, 0, 2)
    add_field("End Time (HH:MM)", end_var, 0, 3)
    add_field("Teacher", teacher_var, 0, 4, widget="combo", values=teacher_options)

    table_card, table_content = create_card(body, "Scheduled Classes")
    table_card.pack(fill=tk.BOTH, expand=True)
    table_frame = tk.Frame(table_content, bg=COLORS["surface"], padx=12, pady=12)
    table_frame.pack(fill=tk.BOTH, expand=True)

    columns = ("class_id", "day", "subject", "start", "end", "teacher")
    tree = ttk.Treeview(
        table_frame,
        columns=columns,
        show="headings",
        selectmode="browse",
        height=9,
    )
    headings = {
        "class_id": "ID",
        "day": "Day",
        "subject": "Subject",
        "start": "Start",
        "end": "End",
        "teacher": "Teacher",
    }
    widths = {
        "class_id": 70,
        "day": 120,
        "subject": 280,
        "start": 95,
        "end": 95,
        "teacher": 140,
    }
    for column in columns:
        tree.heading(column, text=headings[column])
        tree.column(column, width=widths[column], anchor="center")
    tree.column("subject", anchor="w")

    scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    status_label = tk.Label(
        body,
        text="",
        bg=COLORS["bg_primary"],
        fg=COLORS["text_secondary"],
        font=FONTS["small"],
        anchor="w",
    )
    status_label.pack(fill=tk.X, pady=(8, 0))

    def update_current_label():
        active = get_current_class()
        if active:
            current_label.config(text=f"Active: {format_entry(active)}")
        else:
            current_label.config(text="No active class right now")
        win.after(30000, update_current_label)

    def load_rows(rows=None):
        for item in tree.get_children():
            tree.delete(item)

        rows = rows if rows is not None else get_all_timetable()
        for entry in rows:
            tree.insert(
                "",
                "end",
                values=(
                    entry.class_id,
                    entry.day,
                    entry.subject,
                    entry.start_time,
                    entry.end_time,
                    entry.teacher_id,
                ),
            )
        status_label.config(
            text=f"Showing {len(rows)} timetable entr{'y' if len(rows) == 1 else 'ies'}",
            fg=COLORS["text_secondary"],
        )

    def clear_form():
        selected_class_id.set("")
        subject_var.set("")
        day_var.set(today_name())
        start_var.set("")
        end_var.set("")
        teacher_var.set("")
        tree.selection_remove(tree.selection())

    def save_entry():
        class_id = selected_class_id.get().strip() or None
        try:
            saved_id = save_timetable_entry(
                subject=subject_var.get(),
                day=day_var.get(),
                start_time=start_var.get(),
                end_time=end_var.get(),
                teacher_id=_teacher_id_from_option(teacher_var.get()),
                class_id=class_id,
            )
        except TimetableConflictError as exc:
            status_label.config(text=str(exc), fg=COLORS["error"])
            messagebox.showwarning("Timetable Conflict", str(exc), parent=win)
            return
        except ValueError as exc:
            status_label.config(text=str(exc), fg=COLORS["error"])
            messagebox.showerror("Timetable Validation", str(exc), parent=win)
            return
        except Exception as exc:
            messagebox.showerror("Database Error", str(exc), parent=win)
            return

        selected_class_id.set(str(saved_id))
        load_rows()
        messagebox.showinfo("Success", "Timetable entry saved successfully", parent=win)
        clear_form()

    def delete_entry():
        class_id = selected_class_id.get().strip()
        if not class_id:
            messagebox.showerror("Error", "Select a timetable entry to delete", parent=win)
            return
        if not messagebox.askyesno("Confirm Delete", "Delete selected timetable entry?", parent=win):
            return
        if delete_timetable_entry(class_id):
            load_rows()
            clear_form()
            messagebox.showinfo("Deleted", "Timetable entry deleted successfully", parent=win)
        else:
            messagebox.showerror("Error", "Timetable entry was not found", parent=win)

    def show_today():
        rows = get_today_timetable()
        load_rows(rows)
        if not rows:
            status_label.config(text="No classes are scheduled today.")

    def show_active_class():
        active = get_current_class()
        if active:
            messagebox.showinfo("Current Class", format_entry(active), parent=win)
        else:
            messagebox.showinfo("Current Class", "No active class right now", parent=win)

    def on_select(_event):
        selected = tree.selection()
        if not selected:
            return
        values = tree.item(selected[0], "values")
        selected_class_id.set(values[0])
        day_var.set(values[1])
        subject_var.set(values[2])
        start_var.set(values[3])
        end_var.set(values[4])
        teacher_var.set(_teacher_option_for_id(values[5], teacher_options))

    tree.bind("<<TreeviewSelect>>", on_select)

    buttons = tk.Frame(win, bg=COLORS["bg_tertiary"], padx=18, pady=12)
    buttons.pack(fill=tk.X)

    create_ttk_button(buttons, "Add / Update Class", save_entry, "primary").pack(side=tk.LEFT, padx=(0, 8))
    create_ttk_button(buttons, "Remove Class", delete_entry, "danger").pack(side=tk.LEFT, padx=8)
    create_ttk_button(buttons, "Clear", clear_form, "ghost").pack(side=tk.LEFT, padx=8)
    create_ttk_button(buttons, "View Today", show_today, "ghost").pack(side=tk.LEFT, padx=8)
    create_ttk_button(buttons, "Current Class", show_active_class, "secondary").pack(side=tk.LEFT, padx=8)
    create_ttk_button(buttons, "Refresh All", load_rows, "ghost").pack(side=tk.LEFT, padx=8)
    create_ttk_button(buttons, "Close", win.destroy, "outline").pack(side=tk.RIGHT)

    load_rows()
    update_current_label()
    center_window(win)

    if parent is None:
        win.mainloop()


if __name__ == "__main__":
    manage_timetable_window()
