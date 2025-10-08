# test_assignment.py
import tempfile
import unittest
from email.mime import base
from pathlib import Path
import pytest
from pytest import LineMatcher

from agh.agh_data import Assignment
from agh.agh_data import Submission
from agh.agh_data import AssignmentData
from agh.agh_data import SubmissionFileData


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

            a1 = AssignmentData(
                _name="test",
                _year=1997,
                _grade_period="Fall",
                _course="Tuck-10000",
                # _submission_files=subm_files,
                _required_files={
                    "a": SubmissionFileData(path="a.c"),
                    "b": SubmissionFileData(path="b.c"),
                    "c": SubmissionFileData(path="b.h"),
                },
                _optional_files={"a": SubmissionFileData(path="a.h"), "b": SubmissionFileData(path="Makefile")},
            )
            a1_dup = AssignmentData(
                _name=a1._name,
                _year=a1._year,
                _grade_period=a1._grade_period,
                _course=a1._course,
                # _submission_files=a1.submission_files,
                _required_files=a1._required_files,
                _optional_files=a1._optional_files,
            )
            self.assertEqual(a1, a1_dup)

            a2 = AssignmentData(
                _name="test2",
                _year=1997,
                _grade_period="Fall",
                _course="Tuck-10000",
                # _submission_files=subm_files,
                _required_files={
                    "a": SubmissionFileData(path="a.c"),
                    "b": SubmissionFileData(path="b.c"),
                    "c": SubmissionFileData(path="b.h"),
                },
                _optional_files={"a": SubmissionFileData(path="a.h"), "b": SubmissionFileData(path="Makefile")},
            )
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
            a1_ch._grade_period = "Winter"
            self.assertNotEqual(a1, a1_ch)

            a1_ch = AssignmentData._from_json(a1.asdict())
            a1_ch._course = "Tuck-10001"
            self.assertNotEqual(a1, a1_ch)

            # a1_ch = AssignmentData._from_json(a1.asdict())
            # a1_ch.submission_files.append(base / "submission_files4.json")
            # self.assertNotEqual(a1, a1_ch)

            a1_ch = AssignmentData._from_json(a1.asdict())
            a1_ch._required_files["c.c"] = SubmissionFileData(path="c.c")
            self.assertNotEqual(a1, a1_ch)

            a1_ch = AssignmentData._from_json(a1.asdict())
            a1_ch._optional_files["c.h"] = SubmissionFileData(path="c.h")
            self.assertNotEqual(a1, a1_ch)

            a1_ch = AssignmentData._from_json(a1.asdict())
            a1_ch._options.anonymize_names = not a1._options.anonymize_names
            self.assertNotEqual(a1, a1_ch)

    def test_save_load(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            file_store = base / "assignment_data.json"
            subm_files = [base / "submission_files.json", base / "submission_files2.json", base / "submission_files3.json"]
            subm_files = [subm_file.relative_to(base) for subm_file in subm_files]
            # for sf in subm_files:
            #     sf.touch()

            a1 = AssignmentData(
                _name="test",
                _year=1997,
                _grade_period="Fall",
                _course="Tuck-10000",
                # _submission_files=subm_files,
                _required_files={
                    "a": SubmissionFileData(path="a.c"),
                    "b": SubmissionFileData(path="b.c"),
                    "c": SubmissionFileData(path="b.h"),
                },
                _optional_files={"a": SubmissionFileData(path="a.h"), "b": SubmissionFileData(path="Makefile")},
            )

            a1.save(file_store)
            a1_loaded = AssignmentData.load(file_store)
            self.assertEqual(a1, a1_loaded)


class TestAssignment(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.td = tempfile.TemporaryDirectory()
        self.base = Path(self.td.name)


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
        missing = a.getMissingDirectories()
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
        a1.addRequiredFile(SubmissionFileData(path="main.py"))
        a1.addRequiredFile(SubmissionFileData(path="README.md"))

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
        a.createMissingDirectories()
        a3 = Assignment.load(a.tests_dir)
        self.assertEqual(a3, a)

    def test_missing_directories(self):
        base = self.base
        a = Assignment(assignment_directory=base)
        self.assertGreater(len(a.getMissingDirectories()), 0)
        self.assertTrue(False not in [cur_dir in a._directories for cur_dir in a.getMissingDirectories()])

    def test_create_missing_directories_and_readmes(self):
        base = self.base
        a = Assignment(assignment_directory=base)

        # Initially, none should exist
        self.assertGreater(len(a.getMissingDirectories()), 0)

        a.createMissingDirectories()

        # All required directories should now exist
        self.assertEqual(a.getMissingDirectories(), [])

    def create_test_files(self):
        self.assignment = Assignment(self.base)
        self.assignment.createMissingDirectories()
        test_base = self.assignment.tests_dir
        # Create test files
        self.test_files = [
            test_base / "test_1.py",
            test_base / "test_2.py",
            test_base / "test_3.py",
            test_base / "test_4.py",
        ]
        for idx, cur_file in enumerate(self.test_files):
            cur_file.touch()
            with open(cur_file, "w") as f:
                # for func_idx in range(idx + 1):
                f.write(f"def test_{idx}():\n  assert True\n")
                    # f.write(f"def test_{idx}_{func_idx}(json_report_data):\n  json_report_data('test_{idx}_{func_idx}', {idx})\n  assert True\n")
            # print(cur_file.read_text())
        return self.test_files

    def create_unprocessed(self, num_unproc:int, ext:str = ".txt") -> list[Path]:
        a = Assignment(assignment_directory=self.base)
        a.createMissingDirectories()
        ret_val = [(a.unprocessed_dir / f"{idx}{ext}") for idx in range(num_unproc)]
        for cur_file in ret_val:
            cur_file.touch()
        return ret_val

    def create_makefile_build(self):
        a = Assignment(assignment_directory=self.base)
        a.createMissingDirectories()
        makefile = a.templateDir / "Makefile"
        makefile.touch()
        makefile.write_text("all:\n  echo 'Hello, world!'\nbad: noexist.c\n\tgcc -o bad noexist.c")
        return makefile

    def test_submissions(self):
        # self.td = tempfile.TemporaryDirectory(delete=False)
        # self.base = Path(self.td.name)
        base = self.base
        a = Assignment(assignment_directory=self.base)
        a.createMissingDirectories()
        unproc = self.create_unprocessed(5)
        cur_num_subm = 0
        for cur_file in unproc:
            self.assertEqual(cur_num_subm, len([*a.Submissions]))
            a.AddSubmission(cur_file).save()
            cur_num_subm += 1
            a.save()
            a1 = Assignment.load(base)
            self.assertEqual(a1, a)


LinkProto = Assignment.LinkProto

@pytest.fixture
def temp_assignment(tmp_path):
    """Fixture to create a temporary Assignment object."""
    assignment_dir = tmp_path / "assignment"
    assignment_dir.mkdir()
    ret_val = Assignment(assignment_directory=assignment_dir)
    ret_val.createMissingDirectories()
    ret_val.save()
    return ret_val

@pytest.fixture
def filled_assignment(temp_assignment):
    """Fixture to create a temporary Assignment object with some files."""
    temp_assignment.addRequiredFile(SubmissionFileData(path="a.c"))
    # temp_assignment.add_o SubmissionFileData(path="b.c"))
    return temp_assignment

@pytest.fixture
def temp_submission_file(temp_assignment):
    """Fixture to create a temporary submission file."""
    sub_file = temp_assignment.unprocessed_dir / "submission.txt"
    sub_file.touch()
    sub_file.write_text("Hello, world!")
    return sub_file

def test_pps_creates_new_submission(temp_assignment, temp_submission_file):
    """Test that PostProcessSubmission creates a new Submission instance for a valid file."""
    new_submission = temp_assignment.AddSubmission(temp_submission_file)
    assert isinstance(new_submission, Submission)
    assert new_submission.evaluation_directory.exists()

def test_bad_submission(temp_assignment, temp_submission_file):
    """Test that PostProcessSubmission creates a new Submission instance for a valid file."""
    with pytest.raises(FileNotFoundError):
        new_submission = temp_assignment.AddSubmission(temp_assignment.unprocessed_dir / "bad.txt")
        assert False

def test_pps_links_test_files(temp_assignment, temp_submission_file):
    """Test that PostProcessSubmission links required and optional files."""
    new_submission = temp_assignment.AddSubmission(temp_submission_file)
    assert new_submission.evaluation_directory.exists()
    assert (new_submission.evaluation_directory / "tests").is_symlink()

def test_pps_links_test_files(temp_assignment, temp_submission_file):
    """Test that PostProcessSubmission links required and optional files."""
    new_submission = temp_assignment.AddSubmission(temp_submission_file)
    assert new_submission.submission_file.exists()
    assert new_submission.submission_file.read_text() == "Hello, world!"



# def test_postprocesssubmission_raises_error_if_link_exists(temp_assignment, temp_submission_file, tmp_path):
#     """Test that PostProcessSubmission raises FileExistsError if link already exists and protocol is RAISE_ERROR."""
#     conflict_file = tmp_path / "tests"
#     conflict_file.mkdir()
#
#     new_submission = temp_assignment.PostProcessSubmission(temp_submission_file)
#     (new_submission.evaluation_directory / "tests").symlink_to(conflict_file)
#
#     with pytest.raises(FileExistsError):
#         temp_assignment.PostProcessSubmission(temp_submission_file, exists_protocol=LinkProto.RAISE_ERROR)


# def test_postprocesssubmission_ignores_existing_link(temp_assignment, temp_submission_file, tmp_path):
#     """Test that PostProcessSubmission ignores existing link when protocol is IGNORE_ERROR."""
#     conflict_file = tmp_path / "tests"
#     conflict_file.mkdir()
#
#     new_submission = temp_assignment.PostProcessSubmission(temp_submission_file)
#     (new_submission.evaluation_directory / "tests").symlink_to(conflict_file)
#
#     try:
#         temp_assignment.PostProcessSubmission(temp_submission_file, exists_protocol=LinkProto.IGNORE_ERROR)
#     except FileExistsError:
#         pytest.fail("PostProcessSubmission should not raise FileExistsError when IGNORE_ERROR is used.")


# def test_postprocesssubmission_overwrites_existing_link(temp_assignment, temp_submission_file, tmp_path):
#     """Test that PostProcessSubmission overwrites existing link when protocol is LINK_OVERWRITE."""
#     conflict_file = tmp_path / "tests"
#     conflict_file.mkdir()
#
#     new_submission = temp_assignment.PostProcessSubmission(temp_submission_file)
#     conflict_link = new_submission.evaluation_directory / "tests"
#     conflict_link.symlink_to(conflict_file)
#
#     new_link_target = tmp_path / "new_tests"
#     new_link_target.mkdir()
#
#     temp_assignment.linkTemplateDir = new_link_target
#
#     temp_assignment.PostProcessSubmission(temp_submission_file, exists_protocol=LinkProto.LINK_OVERWRITE)
#
#     assert conflict_link.is_symlink()
#     assert conflict_link.readlink() == new_link_target


#     def confirm_sub_was_tested(self, s: Submission, capsys):
#         out,err = capsys.readouterr()
#         LineMatcher(out.splitlines()).fnmatch_lines([
#             f"rootdir: {s.evaluation_directory}",
#         ])
#
#     @pytest.mark.xfail
#     def test_a_submission_tests(self, capsys):
#         a = Assignment(assignment_directory=self.base)
#         a.save()
#         a.createMissingDirectories()
#         unsubmitted = self.create_unprocessed(2)
#         for cur_file in unsubmitted:
#             a.AddSubmission(cur_file).save()
#         self.create_test_files()
#         a.save()
#         s = next(a.Submissions)
#         a.RunTestsOnSubmission(s)
#         self.confirm_sub_was_tested(s)
#
#     def test_submissions_tests(self):
#         a = Assignment(assignment_directory=self.base)
#         a.save()
#         unsubmitted = self.create_unprocessed(2)
#         for cur_file in unsubmitted:
#             a.AddSubmission(cur_file).save()
#         self.create_test_files()
#         a.RunTests()
#         for s in a.Submissions:
#             self.confirm_sub_was_tested(s)
#
#     def test_a_submission_build(self):
#         a = Assignment(assignment_directory=self.base)
#         a.save()
#         a.createMissingDirectories()
#         unsubmitted = self.create_unprocessed(2)
#         for cur_file in unsubmitted:
#             a.AddSubmission(cur_file).save()
#         tf = self.create_test_files()
#         build_test_text = """
# def test_build(agh_build_makefile):
#     ret = agh_build_makefile('all')
#     ret.stdout.matcher.fnmatch_lines(['Hello, world!'])
#     assert ret.ret == 0
#     """
#         tf[0].write_text(build_test_text)
#         self.create_makefile_build()
#         s = next(a.Submissions)
#         a.RunBuildOnSubmission(s)
#
#     def test_a_submission_build_bad(self):
#         a = Assignment(assignment_directory=self.base)
#         a.createMissingDirectories()
#         a.save()
#         unsubmitted = self.create_unprocessed(2)
#         for cur_file in unsubmitted:
#             a.AddSubmission(cur_file).save()
#         tf = self.create_test_files()
#         tf[0].write_text("def test_build(agh_build_makefile):\n  ret = agh_build_makefile('bad')\n  assert ret.ret == 0")
#         self.create_makefile_build()
#         s = next(a.Submissions)
#         a.RunBuildOnSubmission(s)

if __name__ == "__main__":
    unittest.main()
