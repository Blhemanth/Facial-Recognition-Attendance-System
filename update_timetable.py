from timetable import DAYS, TimetableConflictError, save_timetable_entry


def add_or_update_class():
    subject = input("Enter Subject Name: ").strip()
    print("Days:", ", ".join(DAYS))
    day = input("Enter Day (or Daily): ").strip() or "Daily"
    start_time = input("Enter Start Time (HH:MM): ").strip()
    end_time = input("Enter End Time (HH:MM): ").strip()
    teacher_id = input("Enter Teacher ID: ").strip()

    try:
        save_timetable_entry(subject, day, start_time, end_time, teacher_id)
    except TimetableConflictError as exc:
        print(f"Conflict: {exc}")
        return
    except ValueError as exc:
        print(exc)
        return

    print("Class schedule saved successfully")


if __name__ == "__main__":
    add_or_update_class()
