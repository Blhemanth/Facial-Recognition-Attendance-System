import csv
import os
import tkinter as tk
from tkinter import messagebox, ttk

from attendance_service import attendance_percentage
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


def _valid_parent():
    try:
        root = tk._default_root
        return root if root and root.winfo_exists() else None
    except tk.TclError:
        return None


def _fetch_records(student_id, subject="", date_value=""):
    ensure_schema()
    clauses = ["student_id=?"]
    params = [student_id]
    if subject:
        clauses.append("COALESCE(subject, '') LIKE ?")
        params.append(f"%{subject}%")
    if date_value:
        clauses.append("date=?")
        params.append(date_value)

    conn = get_connection()
    try:
        return conn.execute(
            f"""
            SELECT date, COALESCE(time_in, time, '') AS time_value,
                   COALESCE(subject, '') AS subject, status,
                   COALESCE(confidence, '') AS confidence
            FROM attendance
            WHERE {' AND '.join(clauses)}
            ORDER BY date DESC, time_value DESC
            """,
            params,
        ).fetchall()
    finally:
        conn.close()


def open_student_dashboard(student_id, name):
    parent = _valid_parent()
    win = tk.Toplevel(parent) if parent else tk.Tk()
    configure_window(win, "Student Dashboard", "980x640")
    win.minsize(900, 560)

    records = []
    columns = ("date", "time", "subject", "status", "confidence")
    headers = {
        "date": "Date",
        "time": "Time",
        "subject": "Subject",
        "status": "Status",
        "confidence": "Confidence",
    }

    header = tk.Frame(win, bg=COLORS["primary_dark"], height=88)
    header.pack(fill=tk.X)
    header.pack_propagate(False)

    title_area = tk.Frame(header, bg=COLORS["primary_dark"])
    title_area.pack(side=tk.LEFT, padx=24, pady=14)
    tk.Label(
        title_area,
        text=f"Student Dashboard",
        bg=COLORS["primary_dark"],
        fg=COLORS["text_light"],
        font=FONTS["title"],
    ).pack(anchor="w")
    tk.Label(
        title_area,
        text=f"{name}  |  ID: {student_id}",
        bg=COLORS["primary_dark"],
        fg="#dce6f2",
        font=FONTS["small"],
    ).pack(anchor="w", pady=(4, 0))

    percentage_var = tk.StringVar(value="Attendance: --")
    tk.Label(
        header,
        textvariable=percentage_var,
        bg=COLORS["primary_dark"],
        fg="#dce6f2",
        font=FONTS["subtitle"],
    ).pack(side=tk.RIGHT, padx=24)

    body = tk.Frame(win, bg=COLORS["bg_primary"], padx=18, pady=16)
    body.pack(fill=tk.BOTH, expand=True)

    filters_card, filters_content = create_card(body, "Filters")
    filters_card.pack(fill=tk.X, pady=(0, 14))
    filters = tk.Frame(filters_content, bg=COLORS["surface"], padx=14, pady=14)
    filters.pack(fill=tk.X)

    subject_var = tk.StringVar()
    date_var = tk.StringVar()

    def add_filter(label, variable, column):
        tk.Label(
            filters,
            text=label,
            bg=COLORS["surface"],
            fg=COLORS["text_primary"],
            font=FONTS["small"],
        ).grid(row=0, column=column, sticky="w", padx=6)
        ttk.Entry(filters, textvariable=variable).grid(
            row=1,
            column=column,
            sticky="ew",
            padx=6,
            pady=(4, 0),
        )

    filters.columnconfigure(0, weight=1)
    filters.columnconfigure(1, weight=1)
    add_filter("Subject", subject_var, 0)
    add_filter("Date (YYYY-MM-DD)", date_var, 1)

    content = tk.Frame(body, bg=COLORS["bg_primary"])
    content.pack(fill=tk.BOTH, expand=True)

    table_card, table_content = create_card(content, "Attendance Records")
    table_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    table_wrap = tk.Frame(table_content, bg=COLORS["surface"], padx=12, pady=12)
    table_wrap.pack(fill=tk.BOTH, expand=True)

    tree = ttk.Treeview(table_wrap, columns=columns, show="headings")
    for column in columns:
        tree.heading(column, text=headers[column])
        tree.column(column, width=130, anchor="center")
    tree.column("subject", width=220, anchor="w")
    tree.tag_configure("Present", foreground=COLORS["success"])
    tree.tag_configure("Late", foreground=COLORS["warning"])
    tree.tag_configure("Absent", foreground=COLORS["error"])

    scrollbar = ttk.Scrollbar(table_wrap, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    summary_card, summary_content = create_card(content, "Statistics")
    summary_card.pack(side=tk.RIGHT, fill=tk.Y, padx=(14, 0))
    summary_wrap = tk.Frame(summary_content, bg=COLORS["surface"], padx=14, pady=14, width=250)
    summary_wrap.pack(fill=tk.BOTH, expand=True)
    summary_wrap.pack_propagate(False)

    chart = tk.Canvas(
        summary_wrap,
        width=220,
        height=220,
        bg=COLORS["surface"],
        highlightthickness=1,
        highlightbackground=COLORS["border"],
    )
    chart.pack(pady=(0, 12))

    summary_label = tk.Label(
        summary_wrap,
        text="",
        bg=COLORS["surface"],
        fg=COLORS["text_secondary"],
        font=FONTS["normal"],
        justify=tk.LEFT,
        anchor="w",
    )
    summary_label.pack(fill=tk.X)

    status_label = tk.Label(
        body,
        text="",
        bg=COLORS["bg_primary"],
        fg=COLORS["text_secondary"],
        font=FONTS["small"],
        anchor="w",
    )
    status_label.pack(fill=tk.X, pady=(8, 0))

    def draw_chart():
        chart.delete("all")
        counts = {"Present": 0, "Late": 0, "Absent": 0}
        for row in records:
            status = row[3]
            if status in counts:
                counts[status] += 1

        max_count = max(counts.values()) if counts else 0
        colors = {
            "Present": COLORS["success"],
            "Late": COLORS["warning"],
            "Absent": COLORS["error"],
        }
        x = 28
        for status, count in counts.items():
            height = 0 if max_count == 0 else int((count / max_count) * 132)
            chart.create_rectangle(x, 166 - height, x + 42, 166, fill=colors[status], outline="")
            chart.create_text(x + 21, 184, text=status, fill=COLORS["text_primary"], font=FONTS["small"])
            chart.create_text(x + 21, 158 - height, text=str(count), fill=COLORS["text_primary"], font=FONTS["small"])
            x += 66

        total = len(records)
        present = counts["Present"] + counts["Late"]
        summary_label.config(
            text=f"Total records: {total}\nAttended: {present}\nAbsent: {counts['Absent']}"
        )

    def populate(rows):
        nonlocal records
        records = [tuple(row) for row in rows]
        for item in tree.get_children():
            tree.delete(item)
        for row in records:
            tree.insert("", "end", values=row, tags=(row[3],))
        percentage = attendance_percentage(student_id, subject_var.get().strip() or None)
        percentage_var.set(f"Attendance: {percentage:.2f}%")
        status_label.config(text=f"{len(records)} record{'s' if len(records) != 1 else ''} loaded")
        draw_chart()

    def load_records():
        rows = _fetch_records(
            student_id,
            subject=subject_var.get().strip(),
            date_value=date_var.get().strip(),
        )
        populate(rows)
        if not rows:
            status_label.config(text="No attendance records matched the current filters.")

    def clear_filters():
        subject_var.set("")
        date_var.set("")
        load_records()

    def export_csv():
        if not records:
            messagebox.showerror("Error", "No attendance records found", parent=win)
            return
        os.makedirs(EXPORT_DIR, exist_ok=True)
        file_path = os.path.join(EXPORT_DIR, f"{student_id}_attendance.csv")
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([headers[column] for column in columns])
            writer.writerows(records)
        messagebox.showinfo("Export Successful", f"CSV exported: {file_path}", parent=win)

    def export_excel():
        if Workbook is None:
            messagebox.showerror("Error", "openpyxl is not installed", parent=win)
            return
        if not records:
            messagebox.showerror("Error", "No attendance records found", parent=win)
            return
        os.makedirs(EXPORT_DIR, exist_ok=True)
        file_path = os.path.join(EXPORT_DIR, f"{student_id}_attendance.xlsx")
        wb = Workbook()
        ws = wb.active
        ws.title = "Attendance"
        ws.append([headers[column] for column in columns])
        for row in records:
            ws.append(list(row))
        wb.save(file_path)
        messagebox.showinfo("Export Successful", f"Excel exported: {file_path}", parent=win)

    buttons = tk.Frame(win, bg=COLORS["bg_tertiary"], padx=18, pady=12)
    buttons.pack(fill=tk.X)

    create_ttk_button(buttons, "Apply Filter", load_records, "primary").pack(side=tk.LEFT, padx=(0, 8))
    create_ttk_button(buttons, "Clear", clear_filters, "ghost").pack(side=tk.LEFT, padx=8)
    create_ttk_button(buttons, "Export CSV", export_csv, "success").pack(side=tk.LEFT, padx=8)
    create_ttk_button(buttons, "Export Excel", export_excel, "success").pack(side=tk.LEFT, padx=8)
    create_ttk_button(buttons, "Close", win.destroy, "outline").pack(side=tk.RIGHT)

    load_records()
    center_window(win)

    if parent is None:
        win.mainloop()
