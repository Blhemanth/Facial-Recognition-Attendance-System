import sqlite3
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

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

DB = "students.db"


def fetch_attendance(student_id):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT date, status FROM attendance
        WHERE student_id=?
        ORDER BY date DESC
        """,
        (student_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def raise_issue(student_id, desc, proof):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO attendance_issues
        (student_id, date, description, proof_path)
        VALUES (?, ?, ?, ?)
        """,
        (
            student_id,
            datetime.now().strftime("%Y-%m-%d"),
            desc,
            proof,
        ),
    )

    conn.commit()
    conn.close()


def student_dashboard(student_id, name):
    win = tk.Tk()
    configure_window(win, f"Student Portal - {name}", "640x560")

    create_header(win, "Student Portal", f"Welcome, {name}")

    body = tk.Frame(win, bg=COLORS["bg_primary"], padx=22, pady=18)
    body.pack(fill=tk.BOTH, expand=True)

    attendance = fetch_attendance(student_id)
    total = len(attendance)
    present = sum(1 for row in attendance if row[1] == "Present")
    percent = (present / total * 100) if total else 0

    create_status_strip(
        body,
        f"Attendance Percentage: {percent:.2f}%  |  Total Records: {total}",
        "primary",
    ).pack(fill=tk.X, pady=(0, 14))

    records_card, records_content = create_card(body, "Attendance History")
    records_card.pack(fill=tk.BOTH, expand=True, pady=(0, 14))
    records_frame = tk.Frame(records_content, bg=COLORS["surface"], padx=12, pady=12)
    records_frame.pack(fill=tk.BOTH, expand=True)

    tree = ttk.Treeview(records_frame, columns=("date", "status"), show="headings", height=8)
    tree.heading("date", text="Date")
    tree.heading("status", text="Status")
    tree.column("date", width=180, anchor="center")
    tree.column("status", width=140, anchor="center")
    tree.tag_configure("Present", foreground=COLORS["success"])
    tree.tag_configure("Late", foreground=COLORS["warning"])
    tree.tag_configure("Absent", foreground=COLORS["error"])
    tree.pack(fill=tk.BOTH, expand=True)

    for row in attendance:
        tree.insert("", tk.END, values=row, tags=(row[1],))

    issue_card, issue_content = create_card(body, "Raise Attendance Issue")
    issue_card.pack(fill=tk.X)
    issue = tk.Frame(issue_content, bg=COLORS["surface"], padx=14, pady=14)
    issue.pack(fill=tk.X)

    tk.Label(
        issue,
        text="Description",
        bg=COLORS["surface"],
        fg=COLORS["text_primary"],
        font=FONTS["small"],
    ).pack(anchor="w")
    issue_text = ttk.Entry(issue)
    issue_text.pack(fill=tk.X, pady=(4, 10))

    proof_path = tk.StringVar()
    proof_label = tk.Label(
        issue,
        textvariable=proof_path,
        bg=COLORS["surface"],
        fg=COLORS["text_secondary"],
        font=FONTS["small"],
        anchor="w",
    )
    proof_label.pack(fill=tk.X, pady=(0, 10))

    def upload_proof():
        path = filedialog.askopenfilename(
            filetypes=[("PDF/Image", "*.pdf *.jpg *.jpeg *.png")]
        )
        if path:
            proof_path.set(path)

    def submit_issue():
        desc = issue_text.get().strip()
        if not desc:
            messagebox.showerror("Issue Required", "Enter an issue description", parent=win)
            return
        raise_issue(student_id, desc, proof_path.get())
        messagebox.showinfo("Submitted", "Issue submitted to teacher for review", parent=win)
        issue_text.delete(0, tk.END)
        proof_path.set("")

    buttons = tk.Frame(issue, bg=COLORS["surface"])
    buttons.pack(fill=tk.X)
    create_button(buttons, "Upload Proof", upload_proof, "outline").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
    create_button(buttons, "Submit Issue", submit_issue, "primary").pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(6, 0))

    center_window(win)
    win.mainloop()
