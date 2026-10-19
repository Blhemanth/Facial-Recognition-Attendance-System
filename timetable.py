from dataclasses import dataclass
from datetime import datetime, timedelta
import re
from typing import Optional

from database import ensure_schema, get_connection

ATTENDANCE_WINDOW_MIN = 15
DAILY = "Daily"
DAYS = [
    DAILY,
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

_TIME_PATTERN = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")


@dataclass
class TimetableEntry:
    class_id: int
    subject: str
    start_time: str
    end_time: str
    teacher_id: str
    day: str = DAILY


@dataclass
class AttendanceContext:
    can_mark: bool
    message: str
    status: Optional[str] = None
    current_class: Optional[TimetableEntry] = None
    is_late: bool = False


class TimetableValidationError(ValueError):
    """Raised when timetable data is missing or has an invalid format."""


class TimetableConflictError(TimetableValidationError):
    """Raised when a new timetable entry overlaps an existing class."""

    def __init__(self, conflict):
        self.conflict = conflict
        super().__init__(
            "Time conflict detected. Existing class: "
            f"{format_entry(conflict)}. Please choose a non-overlapping time."
        )


def normalize_time(value):
    value = (value or "").strip()
    match = _TIME_PATTERN.match(value)
    if not match:
        raise TimetableValidationError("Time must be in HH:MM format")
    hour = int(match.group(1))
    minute = int(match.group(2))
    return f"{hour:02d}:{minute:02d}"


def time_to_minutes(value):
    normalized = normalize_time(value)
    hour, minute = normalized.split(":")
    return int(hour) * 60 + int(minute)


def normalize_day(value):
    value = (value or DAILY).strip().title()
    if value in {"All", "Everyday", "Every Day"}:
        value = DAILY
    if value not in DAYS:
        raise TimetableValidationError("Select a valid day")
    return value


def today_name(now=None):
    return (now or datetime.now()).strftime("%A")


def _row_to_entry(row):
    return TimetableEntry(
        class_id=row["class_id"],
        subject=row["subject"],
        start_time=row["start_time"],
        end_time=row["end_time"],
        teacher_id=row["teacher_id"] or "",
        day=row["day"] or DAILY,
    )


def _day_matches(schedule_day, required_day):
    schedule_day = normalize_day(schedule_day)
    required_day = normalize_day(required_day)
    return schedule_day == DAILY or schedule_day == required_day


def _days_conflict(first_day, second_day):
    first_day = normalize_day(first_day)
    second_day = normalize_day(second_day)
    return first_day == DAILY or second_day == DAILY or first_day == second_day


def _normalize_optional_class_id(value):
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise TimetableValidationError("Invalid timetable class identifier")


def time_ranges_overlap(start_a, end_a, start_b, end_b):
    # Overlap rule: two classes conflict when each one starts before the
    # other one ends. Back-to-back classes such as 09:00-10:00 and
    # 10:00-11:00 are allowed.
    start_a = time_to_minutes(start_a)
    end_a = time_to_minutes(end_a)
    start_b = time_to_minutes(start_b)
    end_b = time_to_minutes(end_b)
    return start_a < end_b and start_b < end_a


def _validate_basic_fields(subject, day, start_time, end_time, teacher_id):
    subject = (subject or "").strip()
    teacher_id = (teacher_id or "").strip() or None
    day = normalize_day(day)
    start_time = normalize_time(start_time)
    end_time = normalize_time(end_time)

    if not subject:
        raise TimetableValidationError("Subject is required")
    if time_to_minutes(end_time) <= time_to_minutes(start_time):
        raise TimetableValidationError("End time must be after start time")

    return subject, day, start_time, end_time, teacher_id


def get_all_timetable(day=None):
    ensure_schema()
    conn = get_connection()
    try:
        if day:
            day = normalize_day(day)
            rows = conn.execute(
                """
                SELECT class_id, subject, start_time, end_time, teacher_id, day
                FROM timetable
                ORDER BY start_time, end_time, subject
                """
            ).fetchall()
            return [_row_to_entry(row) for row in rows if _day_matches(row["day"], day)]

        rows = conn.execute(
            """
            SELECT class_id, subject, start_time, end_time, teacher_id, day
            FROM timetable
            ORDER BY
                CASE day
                    WHEN 'Daily' THEN 0
                    WHEN 'Monday' THEN 1
                    WHEN 'Tuesday' THEN 2
                    WHEN 'Wednesday' THEN 3
                    WHEN 'Thursday' THEN 4
                    WHEN 'Friday' THEN 5
                    WHEN 'Saturday' THEN 6
                    WHEN 'Sunday' THEN 7
                    ELSE 8
                END,
                start_time,
                subject
            """
        ).fetchall()
        return [_row_to_entry(row) for row in rows]
    finally:
        conn.close()


def get_today_timetable(now=None):
    return get_all_timetable(today_name(now))


def get_current_class(now=None):
    ensure_schema()
    now = now or datetime.now()
    current_minutes = now.hour * 60 + now.minute
    today = today_name(now)

    for entry in get_today_timetable(now):
        start_minutes = time_to_minutes(entry.start_time)
        end_minutes = time_to_minutes(entry.end_time)
        if start_minutes <= current_minutes < end_minutes:
            return entry
    return None


def get_attendance_context(now=None):
    now = now or datetime.now()
    entry = get_current_class(now)
    if not entry:
        return AttendanceContext(
            can_mark=False,
            message="No active class is scheduled right now",
        )

    start_dt = datetime.combine(now.date(), datetime.strptime(entry.start_time, "%H:%M").time())
    window_end = start_dt + timedelta(minutes=ATTENDANCE_WINDOW_MIN)
    status = "Present" if now <= window_end else "Late"
    is_late = status == "Late"

    return AttendanceContext(
        can_mark=True,
        message=f"Active class: {entry.subject} ({entry.start_time}-{entry.end_time})",
        status=status,
        current_class=entry,
        is_late=is_late,
    )


def find_conflicting_class(day, start_time, end_time, exclude_class_id=None):
    day = normalize_day(day)
    start_time = normalize_time(start_time)
    end_time = normalize_time(end_time)
    exclude_class_id = _normalize_optional_class_id(exclude_class_id)

    for entry in get_all_timetable():
        if exclude_class_id and entry.class_id == exclude_class_id:
            continue
        if not _days_conflict(day, entry.day):
            continue
        if time_ranges_overlap(start_time, end_time, entry.start_time, entry.end_time):
            return entry
    return None


def find_duplicate_schedule(day, subject, start_time, end_time, teacher_id, exclude_class_id=None):
    day = normalize_day(day)
    subject = (subject or "").strip().casefold()
    start_time = normalize_time(start_time)
    end_time = normalize_time(end_time)
    teacher_id = (teacher_id or "").strip().casefold()
    exclude_class_id = _normalize_optional_class_id(exclude_class_id)

    for entry in get_all_timetable():
        if exclude_class_id and entry.class_id == exclude_class_id:
            continue
        if normalize_day(entry.day) != day:
            continue
        if (
            entry.subject.casefold() == subject
            and entry.start_time == start_time
            and entry.end_time == end_time
            and (entry.teacher_id or "").casefold() == teacher_id
        ):
            return entry
    return None


def validate_timetable_entry(subject, day, start_time, end_time, teacher_id, class_id=None):
    """
    Central validation point for every timetable save.

    GUI screens, CLI helpers, and future admin tools should call
    save_timetable_entry() or this function instead of duplicating time logic.
    """
    class_id = _normalize_optional_class_id(class_id)
    subject, day, start_time, end_time, teacher_id = _validate_basic_fields(
        subject, day, start_time, end_time, teacher_id
    )

    duplicate = find_duplicate_schedule(
        day, subject, start_time, end_time, teacher_id, exclude_class_id=class_id
    )
    if duplicate:
        raise TimetableValidationError("Duplicate timetable entry already exists")

    conflict = find_conflicting_class(day, start_time, end_time, exclude_class_id=class_id)
    if conflict:
        raise TimetableConflictError(conflict)

    return subject, day, start_time, end_time, teacher_id


def save_timetable_entry(subject, day, start_time, end_time, teacher_id, class_id=None):
    class_id = _normalize_optional_class_id(class_id)
    subject, day, start_time, end_time, teacher_id = validate_timetable_entry(
        subject, day, start_time, end_time, teacher_id, class_id=class_id
    )

    ensure_schema()
    conn = get_connection()
    try:
        if class_id:
            conn.execute(
                """
                UPDATE timetable
                SET subject=?, day=?, start_time=?, end_time=?, teacher_id=?,
                    updated_at=datetime('now', 'localtime')
                WHERE class_id=?
                """,
                (subject, day, start_time, end_time, teacher_id, class_id),
            )
            saved_id = int(class_id)
        else:
            cur = conn.execute(
                """
                INSERT INTO timetable
                (subject, day, start_time, end_time, teacher_id,
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'),
                        datetime('now', 'localtime'))
                """,
                (subject, day, start_time, end_time, teacher_id),
            )
            saved_id = cur.lastrowid

        conn.commit()
        return saved_id
    finally:
        conn.close()


def delete_timetable_entry(class_id):
    ensure_schema()
    conn = get_connection()
    try:
        cur = conn.execute("DELETE FROM timetable WHERE class_id=?", (class_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def format_entry(entry):
    return f"{entry.day} {entry.subject} {entry.start_time}-{entry.end_time}"


def get_attendance_status(start_time):
    """Backward-compatible helper used by older modules."""
    now = datetime.now()
    start_dt = datetime.combine(now.date(), datetime.strptime(normalize_time(start_time), "%H:%M").time())
    if now <= start_dt + timedelta(minutes=ATTENDANCE_WINDOW_MIN):
        return "Present"
    return "Late"


def is_within_attendance_window(start_time):
    """Backward-compatible helper used by older modules."""
    now = datetime.now()
    start_dt = datetime.combine(now.date(), datetime.strptime(normalize_time(start_time), "%H:%M").time())
    return start_dt <= now <= start_dt + timedelta(minutes=ATTENDANCE_WINDOW_MIN)
