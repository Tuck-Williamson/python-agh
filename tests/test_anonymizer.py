# Python
import unittest

import agh.anonimizer as anonimizer


class TestAnonymize(unittest.TestCase):
    def test_deterministic(self):
        out1 = anonimizer.anonymize(
            submission_file_name="alice.txt",
            assignment_name="HW1",
            assignment_year="2025",
            assignment_semester="Fall",
            assignment_course="CS101",
        )
        out2 = anonimizer.anonymize(
            submission_file_name="alice.txt",
            assignment_name="HW1",
            assignment_year="2025",
            assignment_semester="Fall",
            assignment_course="CS101",
        )
        self.assertTrue(out1 == out2, "anonymize should be deterministic for identical inputs")

    def test_changes_with_inputs(self):
        base = anonimizer.anonymize(
            submission_file_name="alice.txt",
            assignment_name="HW1",
            assignment_year="2025",
            assignment_semester="Fall",
            assignment_course="CS101",
        )

        changed_file = anonimizer.anonymize(
            submission_file_name="alice2.txt",
            assignment_name="HW1",
            assignment_year="2025",
            assignment_semester="Fall",
            assignment_course="CS101",
        )
        self.assertNotEqual(base, changed_file, "changing submission_file_name should change output")

        changed_course = anonimizer.anonymize(
            submission_file_name="alice.txt",
            assignment_name="HW1",
            assignment_year="2025",
            assignment_semester="Fall",
            assignment_course="CS102",
        )
        self.assertNotEqual(base, changed_course, "changing assignment_course should change output")

        changed_prefix = anonimizer.anonymize(
            submission_file_name="alice.txt",
            assignment_name="HW1",
            assignment_year="2025",
            assignment_semester="Fall",
            assignment_course="CS101",
            prefix="com.example",
        )
        self.assertNotEqual(base, changed_prefix, "changing prefix should change output")

    def test_output_format(self):
        out = anonimizer.anonymize(
            submission_file_name="alice.txt",
            assignment_name="HW1",
            assignment_year="2025",
            assignment_semester="Fall",
            assignment_course="CS101",
        )
        self.assertIsInstance(out, str)
        self.assertGreater(len(out), 0)
        # Human-friendly hashes are typically hyphen-separated words
        parts = out.split("-")
        self.assertTrue(all(part.isalpha() for part in parts), "output should be hyphen-separated words")


if __name__ == "__main__":
    unittest.main()
