from timetable import format_entry, get_all_timetable


print("\nCURRENT TIMETABLE:\n")
for entry in get_all_timetable():
    print(format_entry(entry), f"| Teacher: {entry.teacher_id or 'N/A'}")
