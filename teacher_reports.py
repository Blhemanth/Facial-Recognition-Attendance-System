import csv
import os
import tkinter as tk
from datetime import datetime
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

try:
    from openpyxl import Workbook
except ImportError:
    Workbook = None

EXPORT_DIR = "exports"


def _fetch_attendance(date_value="", subject="", student_id=""):
    ensure_schema()
    clauses = []
    params = []

    if date_value:
        clauses.append("a.date=?")
        params.append(date_value)
    if subject:
        clauses.append("COALESCE(a.subject, '') LIKE ?")
        params.append(f"%{subject}%")
    if student_id:
        clauses.append("a.student_id LIKE ?")
        params.append(f"%{student_id}%")

    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    conn = get_connection()
    try:
        return conn.execute(
            f"""
            SELECT
                a.student_id,
                COALESCE(a.name, s.name, '') AS name,
                a.date,
                COALESCE(a.time_in, a.time, '') AS time_value,
                COALESCE(a.subject, '') AS subject,
                a.status,
                COALESCE(a.confidence, '') AS confidence
            FROM attendance a
            LEFT JOIN students s ON s.student_id = a.student_id
            {where}
            ORDER BY a.date DESC, time_value DESC, a.student_id
            """,
            params,
        ).fetchall()
    finally:
        conn.close()


def _low_attendance_rows(threshold):
    ensure_schema()
    conn = get_connection()
    try:
        students = conn.execute("SELECT student_id, name FROM students ORDER BY student_id").fetchall()
        rows = []
        for student in students:
            attendance = conn.execute(
                """
                SELECT status
                FROM attendance
                WHERE student_id=?
                """,
                (student["student_id"],),
            ).fetchall()
            total = len(attendance)
            if total == 0:
                percent = 0.0
            else:
                attended = sum(1 for row in attendance if row["status"] in {"Present", "Late"})
                percent = (attended / total) * 100
            if percent < threshold:
                rows.append(
                    (
                        student["student_id"],
                        student["name"],
                        "",
                        "",
                        "All Subjects",
                        f"Low Attendance ({percent:.1f}%)",
                        "",
                    )
                )
        return rows
    finally:
        conn.close()


def teacher_reports():
    parent = tk._default_root
    win = tk.Toplevel(parent) if parent else tk.Tk()
    configure_window(win, "Attendance Reports", "1040x650")
    win.minsize(940, 580)

    records = []
    columns = ("student_id", "name", "date", "time", "subject", "status", "confidence")
    headers = {
        "student_id": "Student ID",
        "name": "Name",
        "date": "Date",
        "time": "Time",
        "subject": "Subject",
        "status": "Status",
        "confidence": "Confidence",
    }

    header = tk.Frame(win, bg=COLORS["primary_dark"], height=88)
    header.pack(fill=tk.X)
    header.pack_propagate(False)
    tk.Label(
        header,
        text="Attendance Reports",
        bg=COLORS["primary_dark"],
        fg=COLORS["text_light"],
        font=FONTS["title"],
    ).pack(side=tk.LEFT, padx=24)
    tk.Label(
        header,
        text="Filter, review, and export attendance records",
        bg=COLORS["primary_dark"],
        fg="#dce6f2",
        font=FONTS["small"],
    ).pack(side=tk.RIGHT, padx=24)

    body = tk.Frame(win, bg=COLORS["bg_primary"], padx=18, pady=16)
    body.pack(fill=tk.BOTH, expand=True)

    filter_card, filter_content = create_card(body, "Filters")
    filter_card.pack(fill=tk.X, pady=(0, 14))
    filter_frame = tk.Frame(filter_content, bg=COLORS["surface"], padx=14, pady=14)
    filter_frame.pack(fill=tk.X)

    date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
    subject_var = tk.StringVar()
    student_var = tk.StringVar()
    threshold_var = tk.StringVar(value="75")

    def add_filter(label, variable, column):
        tk.Label(
            filter_frame,
            text=label,
            bg=COLORS["surface"],
            fg=COLORS["text_primary"],
            font=FONTS["small"],
        ).grid(row=0, column=column, sticky="w", padx=6)
        ttk.Entry(filter_frame, textvariable=variable).grid(
            row=1,
            column=column,
            sticky="ew",
            padx=6,
            pady=(4, 0),
        )

    for col in range(4):
        filter_frame.columnconfigure(col, weight=1)

    add_filter("Date (blank for all)", date_var, 0)
    add_filter("Subject", subject_var, 1)
    add_filter("Student ID", student_var, 2)
    add_filter("Low Attendance Below %", threshold_var, 3)

    table_card, table_content = create_card(body, "Report Results")
    table_card.pack(fill=tk.BOTH, expand=True)
    table_frame = tk.Frame(table_content, bg=COLORS["surface"], padx=12, pady=12)
    table_frame.pack(fill=tk.BOTH, expand=True)

    tree = ttk.Treeview(table_frame, columns=columns, show="headings")
    for column in columns:
        tree.heading(column, text=headers[column])
        tree.column(column, width=125, anchor="center")
    tree.column("name", width=170, anchor="w")
    tree.column("subject", width=170, anchor="w")
    tree.tag_configure("Present", foreground=COLORS["success"])
    tree.tag_configure("Late", foreground=COLORS["warning"])
    tree.tag_configure("Absent", foreground=COLORS["error"])
    tree.tag_configure("Low", foreground=COLORS["error"])

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

    def populate(rows):
        nonlocal records
        records = [tuple(row) for row in rows]
        for item in tree.get_children():
            tree.delete(item)
        for row in records:
            status = row[5]
            tag = "Low" if str(status).startswith("Low Attendance") else status
            tree.insert("", "end", values=row, tags=(tag,))
        status_label.config(text=f"{len(records)} record{'s' if len(records) != 1 else ''} loaded")

    def load_report():
        rows = _fetch_attendance(
            date_value=date_var.get().strip(),
            subject=subject_var.get().strip(),
            student_id=student_var.get().strip(),
        )
        populate(rows)
        if not rows:
            status_label.config(text="No attendance records matched the current filters.")

    def load_all():
        date_var.set("")
        subject_var.set("")
        student_var.set("")
        populate(_fetch_attendance())

    def load_low_attendance():
        try:
            threshold = float(threshold_var.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Enter a valid percentage threshold", parent=win)
            return
        rows = _low_attendance_rows(threshold)
        populate(rows)
        if not rows:
            status_label.config(text="No students are below the selected threshold.")

    def export_csv():
        if not records:
            messagebox.showerror("Error", "No data to export", parent=win)
            return
        os.makedirs(EXPORT_DIR, exist_ok=True)
        file_path = os.path.join(EXPORT_DIR, "attendance_report.csv")
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([headers[column] for column in columns])
            writer.writerows(records)
        messagebox.showinfo("Success", f"CSV exported: {file_path}", parent=win)

    def export_excel():
        if Workbook is None:
            messagebox.showerror("Error", "openpyxl is not installed", parent=win)
            return
        if not records:
            messagebox.showerror("Error", "No data to export", parent=win)
            return
        os.makedirs(EXPORT_DIR, exist_ok=True)
        file_path = os.path.join(EXPORT_DIR, "attendance_report.xlsx")
        wb = Workbook()
        ws = wb.active
        ws.title = "Attendance"
        ws.append([headers[column] for column in columns])
        for row in records:
            ws.append(list(row))
        wb.save(file_path)
        messagebox.showinfo("Success", f"Excel exported: {file_path}", parent=win)

    buttons = tk.Frame(win, bg=COLORS["bg_tertiary"], padx=18, pady=12)
    buttons.pack(fill=tk.X)

    create_ttk_button(buttons, "Load Report", load_report, "primary").pack(side=tk.LEFT, padx=(0, 8))
    create_ttk_button(buttons, "Load All", load_all, "ghost").pack(side=tk.LEFT, padx=8)
    create_ttk_button(buttons, "Low Attendance", load_low_attendance, "warning").pack(side=tk.LEFT, padx=8)
    create_ttk_button(buttons, "Export CSV", export_csv, "success").pack(side=tk.LEFT, padx=8)
    create_ttk_button(buttons, "Export Excel", export_excel, "success").pack(side=tk.LEFT, padx=8)
    create_ttk_button(buttons, "Close", win.destroy, "outline").pack(side=tk.RIGHT)

    load_report()
    center_window(win)

    if parent is None:
        win.mainloop()


if __name__ == "__main__":
    teacher_reports()
