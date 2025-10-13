import os
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

import pytest

from agh.agh_data import Assignment
from agh.agh_data import Submission
from agh.agh_data import SubmissionData


class TestSubmissionData(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.td = tempfile.TemporaryDirectory()
        self.base = Path(self.td.name)
        self.file_store = self.base / "submission_data.json"
        self.sub_file = self.base / "subfile.tar.gz"
        self.sub_file.touch()

    def new_sub(self, **kwlist) -> SubmissionData:
        if "submission_file" not in kwlist.keys():
            kwlist["submission_file"] = self.sub_file
        if "evaluation_directory" not in kwlist.keys():
            kwlist["evaluation_directory"] = self.base
        if "anon_name" not in kwlist.keys():
            kwlist["anon_name"] = "anon_name"
        if "original_name" not in kwlist.keys():
            kwlist["original_name"] = "original_name.txt"

        return SubmissionData(**kwlist)

    def tearDown(self):
        super().tearDown()
        self.td.cleanup()

    def test_defaults_and_directories(self):
        base = self.base
        file_store = base / "assignment_data.json"

        a = self.new_sub()

        # Defaults
        self.assertIsNotNone(a.anon_name)
        self.assertIsNotNone(a.original_name)
        self.assertEqual(a.compiled_initially, None)
        self.assertEqual(a.initial_missing_files, None)

    def test_eq(self):
        base = self.base
        file_store = self.file_store

        s1 = self.new_sub(
            anon_name="test", original_name="bob.tar.gz", compiled_initially=True, initial_missing_files=["a.c", "b.c", "b.h"]
        )
        s1_dup = self.new_sub(
            anon_name=s1.anon_name,
            original_name=s1.original_name,
            compiled_initially=s1.compiled_initially,
            initial_missing_files=s1.initial_missing_files,
        )
        self.assertEqual(s1, s1_dup)

        s2 = self.new_sub(
            anon_name="test2", original_name="bob.tar.gz", compiled_initially=True, initial_missing_files=["a.c", "b.c", "b.h"]
        )
        self.assertNotEqual(s1, s2)
        self.assertNotEqual(s1, self.new_sub())

        # Make sure we can construct from dicts.
        s1_ch = self.new_sub(**asdict(s1))
        self.assertEqual(s1, s1_ch)

        # Test each attribute individually.
        s1_ch.anon_name = "test3"
        self.assertNotEqual(s1, s1_ch)

        s1_ch = self.new_sub(**asdict(s1))
        s1_ch.compiled_initially = not s1.compiled_initially
        self.assertNotEqual(s1, s1_ch)

        s1_ch = self.new_sub(**asdict(s1))
        s1_ch.original_name = "alice.tar.gz"
        self.assertNotEqual(s1, s1_ch)

        s1_ch = self.new_sub(**asdict(s1))
        s1_ch.initial_missing_files.append("c.c")
        self.assertNotEqual(s1, s1_ch)

    def test_save_load(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            file_store = base / "submission_data.json"

            s1 = self.new_sub(
                anon_name="test", original_name="bob.tar.gz", compiled_initially=True, initial_missing_files=["a.c", "b.c", "b.h"]
            )

            s1.save(file_store)
            s1_loaded = SubmissionData.load(file_store)
            self.assertEqual(s1, s1_loaded)


class TestSubmission(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.td = tempfile.TemporaryDirectory()
        self.base = Path(self.td.name)
        base = self.base
        self.file_store = self.base
        self.assignment = Assignment(base)
        self.assignment.createMissingDirectories()
        self.sub_file = self.assignment.unprocessed_dir / "test_submission.txt"
        self.sub_file.touch()
        self.sub_data = SubmissionData(
            submission_file=self.sub_file, evaluation_directory=self.base, anon_name="test", original_name="bob.tar.gz"
        )

    def test_new(self):
        s1 = Submission.new(self.assignment, self.sub_file)
        self.assertTrue(s1.as_submitted_dir.exists(), "As submitted directory does not exist.")
        self.assertTrue(s1.as_submitted_dir.is_dir(), "As submitted directory is not a directory.")
        self.assertTrue(s1.submission_file.exists(), "Submission file does not exist.")
        self.assertTrue(s1.submission_file.is_file(), "Submission file is not a file.")

    def test_load(self):
        s1 = Submission.new(self.assignment, self.sub_file)
        s1.save()
        s2 = Submission.load(s1.evaluation_directory)
        self.assertEqual(s1, s2)

    def test_failed_load(self):
        with pytest.raises(FileNotFoundError):
            s1 = Submission.load(self.base)

    def tearDown(self):
        self.td.cleanup()


class TestTarSubmission(TestSubmission):
    def setUp(self):
        super().setUp()
        self.sub_file = self.assignment.unprocessed_dir / "subfile.tar.gz"
        f1 = self.base / "inTar.txt"
        f1.write_text("Hi there.")
        f2 = self.base / "inTar2.txt"
        f2.write_text("Hi there.")
        f3 = self.base / "inTar3.txt"
        f3.write_text("Hi there.")
        self.tar_files = [f1, f2, f3]
        os.system(f'cd "{self.base}" && tar -czf "{self.sub_file}" inTar.txt inTar2.txt inTar3.txt')

    def test_new_save_load(self):
        s1 = Submission.new(self.assignment, self.sub_file)
        self.assertTrue(s1.as_submitted_dir.exists(), "As submitted directory does not exist.")
        lbreak = '\n\t'
        for f in self.tar_files:
            self.assertTrue(
                (s1.as_submitted_dir / f.name).exists(),
                f"File in tar not found in as submitted directory.{lbreak.join([str(pth) for pth in s1.as_submitted_dir.iterdir()])}",
            )


if __name__ == "__main__":
    unittest.main()
