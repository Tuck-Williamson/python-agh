# test_assignment.py
import tempfile
import unittest
from pathlib import Path

from agh.agh_data import submission_file_data, Assignment, AssignmentData
from dataclasses import asdict


class TestAssignmentData(unittest.TestCase):
  def test_defaults(self):
    with tempfile.TemporaryDirectory() as td:
      base = Path(td)
      file_store = base / "submission_data.json"

      a = Assignment(base)

      # Defaults
      self.assertEqual(a._name, "assignment")
      self.assertEqual(a._year, 2025)
      self.assertEqual(a._grade_period, "Fall")
      self.assertEqual(a._course, "CSCI-340")
      # self.assertEqual(a._submission_files, [])
      self.assertEqual(a._required_files, {})
      self.assertEqual(a._optional_files, {})
      self.assertEqual(a._options.anonymize_names, True)

  def test_eq(self):
    with tempfile.TemporaryDirectory() as td:
      base = Path(td)
      file_store = base / "assignment_data.json"
      # subm_files = [base / "submission_files.json", base / "submission_files2.json",
      #               base / "submission_files3.json"]
      # for sf in subm_files:
      #   sf.touch()

      a1 = AssignmentData(_name="test", _year=1997, _grade_period='Fall', _course='Tuck-10000',
                          # _submission_files=subm_files,
                          _required_files={'a': submission_file_data(path='a.c'), 'b': submission_file_data(path='b.c'),
                                           'c': submission_file_data(path='b.h')},
                          _optional_files={'a': submission_file_data(path='a.h'),
                                           'b': submission_file_data(path='Makefile')})
      a1_dup = AssignmentData(_name=a1._name, _year=a1._year, _grade_period=a1._grade_period, _course=a1._course,
                              # _submission_files=a1.submission_files,
                              _required_files=a1._required_files,
                              _optional_files=a1._optional_files)
      self.assertEqual(a1, a1_dup)

      a2 = AssignmentData(_name="test2", _year=1997, _grade_period='Fall', _course='Tuck-10000',
                          # _submission_files=subm_files,
                          _required_files={'a': submission_file_data(path='a.c'), 'b': submission_file_data(path='b.c'),
                                           'c': submission_file_data(path='b.h')},
                          _optional_files={'a': submission_file_data(path='a.h'),
                                           'b': submission_file_data(path='Makefile')})
      self.assertNotEqual(a1, a2)
      self.assertNotEqual(a1, AssignmentData())

      # Make sure we can construct from dicts.
      a1_ch = AssignmentData._from_json(a1.asdict())
      self.assertEqual(a1, a1_ch)

      # Test each attribute individually.
      a1_ch._name = "test3"
      self.assertNotEqual(a1, a1_ch)

      a1_ch = AssignmentData._from_json(a1.asdict())
      a1_ch._year = 1998
      self.assertNotEqual(a1, a1_ch)

      a1_ch = AssignmentData._from_json(a1.asdict())
      a1_ch._grade_period = 'Winter'
      self.assertNotEqual(a1, a1_ch)

      a1_ch = AssignmentData._from_json(a1.asdict())
      a1_ch._course = 'Tuck-10001'
      self.assertNotEqual(a1, a1_ch)

      # a1_ch = AssignmentData._from_json(a1.asdict())
      # a1_ch.submission_files.append(base / "submission_files4.json")
      # self.assertNotEqual(a1, a1_ch)

      a1_ch = AssignmentData._from_json(a1.asdict())
      a1_ch._required_files["c.c"] = submission_file_data(path="c.c")
      self.assertNotEqual(a1, a1_ch)

      a1_ch = AssignmentData._from_json(a1.asdict())
      a1_ch._optional_files["c.h"] = submission_file_data(path="c.h")
      self.assertNotEqual(a1, a1_ch)

      a1_ch = AssignmentData._from_json(a1.asdict())
      a1_ch._options.anonymize_names = not a1._options.anonymize_names
      self.assertNotEqual(a1, a1_ch)

  def test_save_load(self):
    with tempfile.TemporaryDirectory() as td:
      base = Path(td)
      file_store = base / "assignment_data.json"
      subm_files = [base / "submission_files.json", base / "submission_files2.json",
                    base / "submission_files3.json"]
      subm_files = [subm_file.relative_to(base) for subm_file in subm_files]
      # for sf in subm_files:
      #     sf.touch()

      a1 = AssignmentData(_name="test", _year=1997, _grade_period='Fall', _course='Tuck-10000',
                          # _submission_files=subm_files,
                          _required_files={'a': submission_file_data(path='a.c'), 'b': submission_file_data(path='b.c'),
                                           'c': submission_file_data(path='b.h')},
                          _optional_files={'a': submission_file_data(path='a.h'),
                                           'b': submission_file_data(path='Makefile')})

      a1.save(file_store)
      a1_loaded = AssignmentData.load(file_store)
      self.assertEqual(a1, a1_loaded)


class TestAssignment(unittest.TestCase):

  def setUp(self):
    super().setUp()
    self.td = tempfile.TemporaryDirectory()
    self.base = Path(self.td.name)

  def create_test_files(self):
    self.assignment = Assignment(self.base)
    self.assignment.create_missing_directories()
    test_base = self.assignment.tests_dir
    # Create test files
    self.test_files = [test_base / "test_1.py", test_base / "test_2.py", test_base / "test_3.py",
                       test_base / "test_4.py", ]
    for idx, cur_file in enumerate(self.test_files):
      cur_file.touch()
      with open(cur_file, "w") as f:
        for func_idx in range(idx + 1):
          f.write(f"def test_{idx}_{func_idx}():\n  assert True\n")
          # f.write(f"def test_{idx}_{func_idx}(json_report_data):\n  json_report_data('test_{idx}_{func_idx}', {idx})\n  assert True\n")
      # print(cur_file.read_text())
    return self.test_files

  def tearDown(self):
    super().tearDown()
    self.td.cleanup()

  def test_post_load_sets_directories(self):
    base = self.base
    a = Assignment(assignment_directory=base)
    a.directory = base

    # Ensure attributes exist and point under base
    for cur_dir in a._directories:
      self.assertTrue(str(base) in str(cur_dir))

    # None of them should exist yet
    missing = a.get_missing_directories()
    self.assertTrue(all(not p.exists() for p in missing))
    # Sanity: expect some dirs to be missing
    self.assertGreater(len(missing), 0)

  def test_to_dict_and_save(self):
    base = self.base
    a = Assignment(assignment_directory=base)
    a.name = "HW1"
    a.year = 2024
    a.grade_period = "Fall"
    a.course = "CS101"
    a.directory = base
    a._optional_files = ["notes.md"]
    a1 = Assignment(assignment_directory=base)
    a1.add_required_file(submission_file_data(path="main.py"))
    a1.add_required_file(submission_file_data(path="README.md"))

    a1.save()
    self.assertTrue(str(base) in str(a1._do_file))

    self.assertTrue(a1._do_file.exists())
    a2 = Assignment.load(a1._do_file)
    self.assertEqual(a2, a1)

    a2 = Assignment(base, _name="HW1", _year=2024, _grade_period="Fall", _course="CS101")
    a2.save()
    a3 = Assignment.load(a2._do_file.parent)
    self.assertEqual(a3, a2)

  def test_load(self):
    base = self.base
    a = Assignment(assignment_directory=base)
    a.name = "HW1"
    a.year = 2024
    a.save()
    a1 = Assignment.load(base)
    self.assertEqual(a1, a)
    a2 = Assignment.load(a1._do_file)
    self.assertEqual(a2, a)

  def test_missing_directories(self):
    base = self.base
    a = Assignment(assignment_directory=base)
    self.assertGreater(len(a.get_missing_directories()), 0)
    self.assertTrue(False not in [cur_dir in a._directories for cur_dir in a.get_missing_directories()])

  def test_create_missing_directories_and_readmes(self):
    base = self.base
    a = Assignment(assignment_directory=base)

    # Initially, none should exist
    self.assertGreater(len(a.get_missing_directories()), 0)

    a.create_missing_directories()

    # All required directories should now exist
    self.assertEqual(a.get_missing_directories(), [])

  def test_submissions(self):
    # self.td = tempfile.TemporaryDirectory(delete=False)
    # self.base = Path(self.td.name)
    base = self.base
    a = Assignment(assignment_directory=base)
    a.create_missing_directories()
    unproc = [(a.unprocessed_dir / f'{idx}.txt') for idx in range(4)]
    cur_num_subm = 0
    for cur_file in unproc:
      cur_file.touch()
      self.assertEqual(cur_num_subm, len([*a.Submissions]))
      a.AddSubmission(cur_file).save()
      cur_num_subm += 1
      a.save()
      a1 = Assignment.load(base)
      self.assertEqual(a1, a)

    # def test_run_tests(self):
    # base = Path(td)
    a = Assignment(assignment_directory=base)
    a.create_missing_directories()
    tf_list = self.create_test_files()
    a.RunTests()
    # self.td.cleanup = lambda: None

if __name__ == "__main__":
  unittest.main()
