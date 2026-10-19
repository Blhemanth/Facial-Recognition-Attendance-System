import csv
import logging
import os
import sqlite3
from contextlib import contextmanager

DB_NAME = "students.db"

logger = logging.getLogger(__name__)
_schema_ready = False


def get_connection():
    """Return a SQLite connection configured for this project."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db_cursor(commit=False):
    conn = get_connection()
    try:
        cur = conn.cursor()
        yield cur
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("Database operation failed")
        raise
    finally:
        conn.close()


def _table_columns(conn, table_name):
    cur = conn.execute(f"PRAGMA table_info({table_name})")
    return {row["name"] for row in cur.fetchall()}


def _ensure_column(conn, table_name, column_name, ddl):
    if column_name not in _table_columns(conn, table_name):
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {ddl}")


def ensure_schema():
    """
    Create missing tables and add missing columns without deleting existing data.
    This keeps old demo databases compatible while allowing the improved modules
    to store subject, name, time, confidence, timetable day, and class metadata.
    """
    global _schema_ready
    if _schema_ready:
        return

    conn = get_connection()
    try:
        cur = conn.cursor()

        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS students (
                student_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                parent_phone TEXT,
                face_encoding BLOB,
                department TEXT,
                password TEXT
            );

            CREATE TABLE IF NOT EXISTS teachers (
                teacher_id TEXT PRIMARY KEY,
                name TEXT,
                username TEXT UNIQUE,
                password TEXT
            );

            CREATE TABLE IF NOT EXISTS timetable (
                class_id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                teacher_id TEXT,
                day TEXT NOT NULL DEFAULT 'Daily',
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id)
                    ON UPDATE CASCADE ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                name TEXT,
                date TEXT NOT NULL,
                time_in TEXT,
                time TEXT,
                subject TEXT,
                status TEXT NOT NULL,
                confidence REAL,
                class_id INTEGER,
                created_at TEXT,
                FOREIGN KEY (student_id) REFERENCES students(student_id)
                    ON UPDATE CASCADE ON DELETE CASCADE,
                FOREIGN KEY (class_id) REFERENCES timetable(class_id)
                    ON UPDATE CASCADE ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS attendance_issues (
                issue_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT,
                date TEXT,
                description TEXT,
                proof_path TEXT,
                status TEXT DEFAULT 'Pending',
                FOREIGN KEY (student_id) REFERENCES students(student_id)
                    ON UPDATE CASCADE ON DELETE CASCADE
            );
            """
        )

        student_columns = _table_columns(conn, "students")
        if "parent_phone" not in student_columns:
            conn.execute("ALTER TABLE students ADD COLUMN parent_phone TEXT")
        if "face_encoding" not in student_columns:
            conn.execute("ALTER TABLE students ADD COLUMN face_encoding BLOB")
        if "department" not in student_columns:
            conn.execute("ALTER TABLE students ADD COLUMN department TEXT")
        if "password" not in student_columns:
            conn.execute("ALTER TABLE students ADD COLUMN password TEXT")

        _ensure_column(conn, "timetable", "day", "day TEXT NOT NULL DEFAULT 'Daily'")
        _ensure_column(conn, "timetable", "created_at", "created_at TEXT")
        _ensure_column(conn, "timetable", "updated_at", "updated_at TEXT")

        attendance_columns = _table_columns(conn, "attendance")
        if "name" not in attendance_columns:
            conn.execute("ALTER TABLE attendance ADD COLUMN name TEXT")
        if "time_in" not in attendance_columns:
            conn.execute("ALTER TABLE attendance ADD COLUMN time_in TEXT")
        if "time" not in attendance_columns:
            conn.execute("ALTER TABLE attendance ADD COLUMN time TEXT")
        if "subject" not in attendance_columns:
            conn.execute("ALTER TABLE attendance ADD COLUMN subject TEXT")
        if "confidence" not in attendance_columns:
            conn.execute("ALTER TABLE attendance ADD COLUMN confidence REAL")
        if "class_id" not in attendance_columns:
            conn.execute("ALTER TABLE attendance ADD COLUMN class_id INTEGER")
        if "created_at" not in attendance_columns:
            conn.execute("ALTER TABLE attendance ADD COLUMN created_at TEXT")

        cur.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_timetable_day_time
                ON timetable(day, start_time, end_time);
            CREATE INDEX IF NOT EXISTS idx_timetable_subject_day
                ON timetable(subject, day);
            CREATE INDEX IF NOT EXISTS idx_attendance_student_date_subject
                ON attendance(student_id, date, subject);
            CREATE INDEX IF NOT EXISTS idx_attendance_date_subject
                ON attendance(date, subject);
            """
        )

        conn.commit()
    finally:
        conn.close()

    sync_teachers_from_csv()
    _schema_ready = True


def sync_teachers_from_csv(csv_path="teachers.csv"):
    """Load teacher rows from teachers.csv if it is present."""
    if not os.path.exists(csv_path):
        return

    conn = get_connection()
    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                teacher_id = (row.get("teacher_id") or "").strip()
                if not teacher_id:
                    continue
                conn.execute(
                    """
                    INSERT OR IGNORE INTO teachers
                    (teacher_id, name, username, password)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        teacher_id,
                        (row.get("name") or "").strip(),
                        (row.get("username") or "").strip(),
                        (row.get("password") or "").strip(),
                    ),
                )
        conn.commit()
    except Exception:
        logger.exception("Could not sync teachers.csv")
    finally:
        conn.close()


def get_student(student_id):
    ensure_schema()
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT student_id, name, parent_phone, department, password, face_encoding
            FROM students
            WHERE student_id=?
            """,
            (student_id,),
        )
        return cur.fetchone()


def get_student_name(student_id):
    student = get_student(student_id)
    return student["name"] if student else None


def get_students_with_faces():
    ensure_schema()
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT student_id, name, face_encoding
            FROM students
            WHERE face_encoding IS NOT NULL
            """
        )
        return cur.fetchall()


def attendance_record_exists(student_id, date_value, subject):
    ensure_schema()
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT id, time_in, time, status
            FROM attendance
            WHERE student_id=? AND date=? AND COALESCE(subject, '')=COALESCE(?, '')
              AND status IN ('Present', 'Late')
            ORDER BY id DESC
            LIMIT 1
            """,
            (student_id, date_value, subject),
        )
        return cur.fetchone()


def get_last_attendance_record(student_id):
    ensure_schema()
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT date, time_in, time, subject, status
            FROM attendance
            WHERE student_id=?
            ORDER BY date DESC, COALESCE(time_in, time) DESC, id DESC
            LIMIT 1
            """,
            (student_id,),
        )
        return cur.fetchone()


def insert_attendance_record(
    student_id,
    name,
    date_value,
    time_value,
    subject,
    status,
    confidence=None,
    class_id=None,
):
    ensure_schema()
    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO attendance
            (student_id, name, date, time_in, time, subject, status,
             confidence, class_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
            """,
            (
                student_id,
                name,
                date_value,
                time_value,
                time_value,
                subject,
                status,
                confidence,
                class_id,
            ),
        )
        return cur.lastrowid


def setup_database():
    ensure_schema()
    print("Database initialized successfully.")


if __name__ == "__main__":
    setup_database()
