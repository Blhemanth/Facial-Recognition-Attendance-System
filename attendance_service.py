from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from typing import Optional

from database import (
    attendance_record_exists,
    ensure_schema,
    get_connection,
    get_last_attendance_record,
    get_student,
    insert_attendance_record,
)
from timetable import get_attendance_context

ATTENDANCE_COOLDOWN_SECONDS = 30

logger = logging.getLogger(__name__)


@dataclass
class AttendanceResult:
    success: bool
    message: str
    student_id: Optional[str] = None
    name: Optional[str] = None
    subject: Optional[str] = None
    status: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    duplicate: bool = False
    confidence: Optional[float] = None


def _parse_attendance_datetime(record):
    if not record:
        return None

    date_value = record["date"]
    time_value = record["time_in"] or record["time"]
    if not date_value or not time_value:
        return None

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(f"{date_value} {time_value}", fmt)
        except ValueError:
            continue
    return None


def _is_in_cooldown(student_id, now):
    last_record = get_last_attendance_record(student_id)
    last_dt = _parse_attendance_datetime(last_record)
    if not last_dt:
        return False
    return now - last_dt < timedelta(seconds=ATTENDANCE_COOLDOWN_SECONDS)


def _any_attendance_for_subject(student_id, date_value, subject):
    ensure_schema()
    conn = get_connection()
    try:
        return conn.execute(
            """
            SELECT id, status, time_in, time
            FROM attendance
            WHERE student_id=? AND date=? AND COALESCE(subject, '')=COALESCE(?, '')
            ORDER BY id DESC
            LIMIT 1
            """,
            (student_id, date_value, subject),
        ).fetchone()
    finally:
        conn.close()


def mark_attendance(
    student_id,
    subject=None,
    status=None,
    confidence=None,
    class_info=None,
    manual=False,
):
    """
    Mark attendance once per student/date/subject.
    Camera attendance uses the active timetable class. Manual attendance can
    pass subject/status directly and bypass the active-class check.
    """
    ensure_schema()
    now = datetime.now()
    date_value = now.strftime("%Y-%m-%d")
    time_value = now.strftime("%H:%M:%S")
    student_id = (student_id or "").strip()

    if not student_id:
        return AttendanceResult(False, "Student ID is required")

    student = get_student(student_id)
    if not student:
        return AttendanceResult(False, "Student not found", student_id=student_id)

    if not manual:
        context = get_attendance_context(now)
        if not context.can_mark:
            return AttendanceResult(False, context.message, student_id=student_id)
        class_info = class_info or context.current_class
        subject = subject or class_info.subject
        status = status or context.status
    else:
        subject = (subject or "").strip()
        status = (status or "").strip() or "Present"
        if not subject:
            return AttendanceResult(False, "Subject is required", student_id=student_id)

    if status not in {"Present", "Late", "Absent"}:
        return AttendanceResult(False, "Invalid attendance status", student_id=student_id)

    subject = (subject or "").strip()
    name = student["name"]

    existing = _any_attendance_for_subject(student_id, date_value, subject)
    if existing:
        return AttendanceResult(
            False,
            f"Attendance already marked for {subject}",
            student_id=student_id,
            name=name,
            subject=subject,
            status=existing["status"],
            date=date_value,
            time=existing["time_in"] or existing["time"],
            duplicate=True,
            confidence=confidence,
        )

    if not manual and _is_in_cooldown(student_id, now):
        return AttendanceResult(
            False,
            "Attendance cooldown active",
            student_id=student_id,
            name=name,
            subject=subject,
            status=status,
            date=date_value,
            time=time_value,
            duplicate=True,
            confidence=confidence,
        )

    class_id = class_info.class_id if class_info else None
    insert_attendance_record(
        student_id=student_id,
        name=name,
        date_value=date_value,
        time_value=time_value,
        subject=subject,
        status=status,
        confidence=confidence,
        class_id=class_id,
    )

    return AttendanceResult(
        True,
        f"{status} attendance marked for {name}",
        student_id=student_id,
        name=name,
        subject=subject,
        status=status,
        date=date_value,
        time=time_value,
        duplicate=False,
        confidence=confidence,
    )


def mark_manual_attendance(student_id, subject, status):
    return mark_attendance(
        student_id=student_id,
        subject=subject,
        status=status,
        manual=True,
    )


def attendance_percentage(student_id, subject=None):
    ensure_schema()
    conn = get_connection()
    try:
        params = [student_id]
        subject_clause = ""
        if subject:
            subject_clause = "AND subject=?"
            params.append(subject)

        rows = conn.execute(
            f"""
            SELECT status
            FROM attendance
            WHERE student_id=? {subject_clause}
            """,
            params,
        ).fetchall()
    finally:
        conn.close()

    total = len(rows)
    if total == 0:
        return 0.0
    attended = sum(1 for row in rows if row["status"] in {"Present", "Late"})
    return (attended / total) * 100


def mark_absent_for_subject(subject, class_id=None, date_value=None):
    """Placeholder-ready automatic absent marking for the selected class."""
    ensure_schema()
    date_value = date_value or datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    try:
        students = conn.execute("SELECT student_id, name FROM students").fetchall()
    finally:
        conn.close()

    marked = 0
    for student in students:
        if attendance_record_exists(student["student_id"], date_value, subject):
            continue
        existing = _any_attendance_for_subject(student["student_id"], date_value, subject)
        if existing:
            continue
        insert_attendance_record(
            student_id=student["student_id"],
            name=student["name"],
            date_value=date_value,
            time_value=datetime.now().strftime("%H:%M:%S"),
            subject=subject,
            status="Absent",
            confidence=None,
            class_id=class_id,
        )
        marked += 1
    return marked
