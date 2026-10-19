import os
import tempfile
import unittest

import database
from timetable import (
    TimetableConflictError,
    get_all_timetable,
    save_timetable_entry,
    time_ranges_overlap,
    validate_timetable_entry,
)


class TimetableConflictTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.tmp.close()
        self.original_db = database.DB_NAME
        database.DB_NAME = self.tmp.name
        database._schema_ready = False
        database.ensure_schema()

    def tearDown(self):
        database.DB_NAME = self.original_db
        database._schema_ready = False
        if os.path.exists(self.tmp.name):
            os.remove(self.tmp.name)

    def test_overlap_formula_blocks_only_real_overlap(self):
        self.assertTrue(time_ranges_overlap("09:00", "10:00", "09:30", "10:30"))
        self.assertFalse(time_ranges_overlap("09:00", "10:00", "10:00", "11:00"))

    def test_same_day_overlap_is_rejected(self):
        save_timetable_entry("Mathematics", "Monday", "09:00", "10:00", "")

        with self.assertRaises(TimetableConflictError) as context:
            save_timetable_entry("Physics", "Monday", "09:30", "10:30", "")

        self.assertIn("Mathematics", str(context.exception))
        self.assertEqual(len(get_all_timetable()), 1)

    def test_back_to_back_class_is_allowed(self):
        save_timetable_entry("Mathematics", "Monday", "09:00", "10:00", "")
        save_timetable_entry("Physics", "Monday", "10:00", "11:00", "")

        self.assertEqual(len(get_all_timetable()), 2)

    def test_different_day_overlap_is_allowed(self):
        save_timetable_entry("Mathematics", "Monday", "09:00", "10:00", "")
        save_timetable_entry("Physics", "Tuesday", "09:30", "10:30", "")

        self.assertEqual(len(get_all_timetable()), 2)

    def test_daily_class_conflicts_with_specific_day(self):
        save_timetable_entry("Assembly", "Daily", "08:45", "09:15", "")

        with self.assertRaises(TimetableConflictError):
            validate_timetable_entry("Chemistry", "Wednesday", "09:00", "10:00", "")

    def test_update_excludes_the_same_class_but_blocks_other_conflicts(self):
        math_id = save_timetable_entry("Mathematics", "Monday", "09:00", "10:00", "")
        save_timetable_entry("Physics", "Monday", "10:00", "11:00", "")

        save_timetable_entry("Mathematics", "Monday", "09:00", "10:00", "", class_id=math_id)

        with self.assertRaises(TimetableConflictError):
            save_timetable_entry("Mathematics", "Monday", "10:30", "11:30", "", class_id=math_id)


if __name__ == "__main__":
    unittest.main(verbosity=2)
