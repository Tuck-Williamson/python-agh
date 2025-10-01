import json
import os
import pathlib
from collections.abc import Iterable
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from dataclasses import fields
from dataclasses import is_dataclass
from typing import Any
from typing import get_args
from typing import get_origin

import agh.anonimizer as anonimizer


def findFileInParents(path: pathlib.Path, filename: str) -> pathlib.Path | None:
    """Find a file in the parent directories of a path.

    :param path: The path to start searching from.
    :param filename: The name of the file to search for.

    :return: The path to the file if found, None otherwise.
    """
    while path != path.parent:
        if (path / filename).exists():
            return path / filename
        path = path.parent

    return None


class DataclassJson:
    """Parent class for dataclasses to serialize to JSON.
    This class should only be used as a parent class for dataclasses.

    This class is designed to be used with the @dataclass decorator.

    The class provides methods to save and load dataclasses to JSON files.
    Currently it supports deserialization from JSON to dataclasses properly for
    directly nested dataclasses, single-level lists of DataclassJson subclasses as long as the
    type info lists the dataclass as the first type in a series of possible types,
    and dictionaries where the value type is a subclass of DataclassJson.
    """

    def __init__(self, *args, **kwargs):
        assert issubclass(self, DataclassJson), "This class should only be used as a parent class for dataclasses."
        assert is_dataclass(self), "This class should only be used as a parent class for dataclasses."

    def asdict(self) -> dict[str, Any]:
        restore_these: dict[str, Any] = {}
        for cur_field in fields(self):
            if hasattr(cur_field.type, "asdict"):
                restore_these[cur_field.name] = getattr(self, cur_field.name)
                setattr(self, cur_field.name, getattr(self, cur_field.name).asdict())
            if cur_field.type is pathlib.Path and isinstance(getattr(self, cur_field.name), pathlib.Path):
                restore_these[cur_field.name] = getattr(self, cur_field.name)
                setattr(self, cur_field.name, str(restore_these[cur_field.name]))
            elif get_origin(cur_field.type) is list and get_args(cur_field.type)[0] is pathlib.Path:
                restore_these[cur_field.name] = getattr(self, cur_field.name)
                setattr(self, cur_field.name, [str(cur_val) for cur_val in restore_these[cur_field.name]])
            elif get_origin(cur_field.type) is dict and hasattr(get_args(cur_field.type)[-1], "asdict"):
                restore_these[cur_field.name] = getattr(self, cur_field.name)
                setattr(self, cur_field.name, {cur_key: cur_val.asdict() for cur_key, cur_val in restore_these[cur_field.name].items()})
        # if len(restore_these) > 0:
        #   print(self)
        ret_val = asdict(self)
        # if len(restore_these) > 0:
        #   print(ret_val)

        for cur_key, cur_val in restore_these.items():
            setattr(self, cur_key, cur_val)

        return ret_val

    def save(self, filepath: pathlib.Path, indent: int = 2):
        with filepath.open("w") as f:
            data = self.asdict()
            json.dump(data, f, indent=indent)

    @classmethod
    def _from_json(cls, data: dict):
        for cur_field in fields(cls):
            # if get_origin(cur_field.type) == dict:
            #   print(f"{cur_field.name} = {data[cur_field.name]} and has type {cur_field.type}")

            if hasattr(cur_field.type, "_from_json"):
                data[cur_field.name] = cur_field.type._from_json(data[cur_field.name])
            elif get_origin(cur_field.type) is list and hasattr(get_args(cur_field.type)[0], "_from_json"):
                data[cur_field.name] = [get_args(cur_field.type)[0]._from_json(p) for p in data[cur_field.name]]
            elif get_origin(cur_field.type) is dict and hasattr(get_args(cur_field.type)[-1], "_from_json"):
                # print(data[cur_field.name])
                data[cur_field.name] = {k: get_args(cur_field.type)[-1]._from_json(p) for k, p in data[cur_field.name].items()}
            elif is_dataclass(cur_field.type):
                data[cur_field.name] = cur_field.type(**data[cur_field.name])
            elif get_origin(cur_field.type) is list and is_dataclass(get_args(cur_field.type)[0]):
                data[cur_field.name] = [get_args(cur_field.type)[0](**p) for p in data[cur_field.name]]
            elif get_origin(cur_field.type) is dict and is_dataclass(get_args(cur_field.type)[-1]):
                data[cur_field.name] = {k: get_args(cur_field.type)[-1](**p) for k, p in data[cur_field.name].items()}
            elif cur_field.type is pathlib.Path:
                data[cur_field.name] = pathlib.Path(data[cur_field.name])
            elif cur_field.type is list[pathlib.Path]:
                data[cur_field.name] = [pathlib.Path(p) for p in data[cur_field.name]]
        return cls(**data)

    @classmethod
    def load_json(cls, filepath: pathlib.Path):
        with filepath.open() as f:
            data = json.load(f)
            # Transform the data to the correct types.
            return cls._from_json(data)

    @classmethod
    def load(cls, filepath: pathlib.Path):
        if filepath.exists() and filepath.is_file():
            return cls.load_json(filepath)
        else:
            raise FileNotFoundError(filepath)


# Mark all fields as keyword-only so that we can load directly from JSON.
@dataclass(kw_only=True)
class submission_file_data(DataclassJson):
    path: pathlib.Path
    title: str = ""
    type: str = "default"
    include_in_output: bool = True
    description: str = ""
    unlisted: bool = False

    def __post_init__(self):
        if self.title == "":
            if isinstance(self.path, str):
                self.path = pathlib.Path(self.path)
                self.title = self.path.name
            else:
                self.title = self.path.name


# Mark all fields as keyword-only so that we can load directly from JSON.
@dataclass(kw_only=True)
class GraderOptions(DataclassJson):
    """Serializable data container for grading options.
    There will be a global user configuration file that contains the default grading options.

    This will also be contained in the assignment data for per-assignment options.
    """

    anonymize_names: bool = field(default=True)


# Mark all fields as keyword-only so that we can load directly from JSON.
@dataclass(kw_only=True)
class AssignmentData(DataclassJson):
    _name: str = "assignment"
    _year: int = 2025
    _grade_period: str = "Fall"
    _course: str = "CSCI-340"
    _required_files: dict[str, submission_file_data] = field(default_factory=dict)
    _optional_files: dict[str, submission_file_data] = field(default_factory=dict)
    _options: GraderOptions = field(default_factory=GraderOptions)
    metadata: dict[str, Any] = field(default_factory=dict)


class Assignment(AssignmentData):
    """Represents an assignment.
    At its core, an assignment is a collection of required files and optional files,
    along with a name, and the submissions for that assignment.
    The submissions are stored in a list of Submission objects.

    The assignment is also associated with tests to run on the submissions.
    """

    ASSIGNMENT_FILE_NAME = "assignment.json"

    def __init__(self, assignment_directory: pathlib.Path | None = None, *args, **kwargs):
        """Create a new Assignment object.

        See Assignment.load for loading an assignment from a JSON file.

        :param assignment_directory: Path to the assignment directory root.
        :param do: Assignment data object.
        """
        super().__init__(*args, **kwargs)
        if assignment_directory is None:
            assignment_directory = pathlib.Path("./")
        elif not assignment_directory.exists():
            raise FileNotFoundError(assignment_directory)
        elif not assignment_directory.is_dir():
            raise NotADirectoryError(assignment_directory)

        if assignment_directory is None:
            assignment_directory = pathlib.Path.cwd()

        do_file = assignment_directory / self.ASSIGNMENT_FILE_NAME
        self._do_file = do_file
        # self._do = do

        self._directory = assignment_directory
        self.__post_init__()

    def __post_init__(self):
        """Post-load processing for the assignment.
        This method is called after the assignment is loaded from JSON or a directory.
        It sets up the directory structure for the assignment.
        """

        self._directories = set()

        input_dir = self._directory / "submissions"
        output_dir = self._directory / "output"
        assignment_dir = self._directory / "assignment"

        # Input - submssion directories
        self.archive_dir = input_dir / "archive"
        self._directories.add(self.archive_dir)
        # self.to_process_dir = self._directory / 'to_process'
        self.unprocessed_dir = input_dir / "unprocessed/"
        self._directories.add(self.unprocessed_dir)
        self.eval_dir = input_dir / "evaluations/"
        self._directories.add(self.eval_dir)

        # Output
        self.complete_eval_dir = output_dir / "as_rendered"
        self._directories.add(self.complete_eval_dir)
        self.oaks_ready_dir = output_dir / "graded"
        self._directories.add(self.oaks_ready_dir)
        if self._options.anonymize_names:
            self.oaks_named_dir = output_dir / "de-anonymized"
        else:
            self.oaks_named_dir = self.oaks_ready_dir
        self._directories.add(self.oaks_named_dir)

        # Assignment information and how to test the submissions.
        self.templateDir = assignment_dir / "template/"
        self._directories.add(self.templateDir)
        self.linkTemplateDir = self.templateDir
        self._directories.add(self.linkTemplateDir)
        self.assignmentDir = assignment_dir / "description"
        self._directories.add(self.assignmentDir)
        self.tests_dir = assignment_dir / "how_to_evaulate"
        self._directories.add(self.tests_dir)

    @classmethod
    def load(cls, filepath: pathlib.Path):
        """Load an assignment from a JSON file or a directory.

        These objects are stored in JSON files in the same directory as the assignment.
        They are intended to be short lived and dynamically loaded from any sub-directory.
        Therefore, if you pass in a directory, this will look for the JSON file in that directory and it's parents.

        :param filepath: Path to the JSON file or directory containing the assignment data.
        :raises FileNotFoundError: If the file or directory does not exist.
        :return: The loaded assignment object.
        """
        if filepath.exists() and filepath.is_dir():
            filepath = findFileInParents(filepath, cls.ASSIGNMENT_FILE_NAME)
            if filepath is None:
                raise FileNotFoundError(f"Could not find assignment JSON file in {filepath} or any of its parents.")

        if filepath.exists() and filepath.is_file():
            data = json.loads(filepath.read_text())
            data["assignment_directory"] = filepath.parent
            return cls._from_json(data)

        raise FileNotFoundError(filepath)

    def save(self, filepath: pathlib.Path | None = None, indent: int = 2):
        if filepath is None:
            filepath = self._do_file
        super().save(filepath, indent)

    @property
    def file(self) -> pathlib.Path | None:
        return self._do_file

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def Submissions(self):
        for subm_file in self._directory.rglob(Submission.SUBMISSION_FILE_NAME):
            yield Submission.load(subm_file)

    def AddSubmission(self, submission_file: pathlib.Path) -> "Submission":
        """Add a new submission to the assignment.
        :param submission_file:
        :return: The new submission.
        :rtype: "Submission"
        """
        ret_val = Submission.new(self, submission_file=submission_file)
        # link in the tests.
        sub_test = ret_val.evaluation_directory / "tests"
        sub_test.symlink_to(self.tests_dir, target_is_directory=True)
        return ret_val

    def RunTests(self, submissions_to_test: Iterable["Submission"] | None = None):
        if submissions_to_test is None:
            submissions_to_test = self.Submissions

        for submission in submissions_to_test:
            self.RunTestsOnSubmission(submission)

    def RunTestsOnSubmission(self, submission_to_test: "Submission"):
        os.system(f'cd "{submission_to_test.evaluation_directory}" && pytest ./')

    @property
    def required_files(self):
        return self._required_files

    @property
    def GraderOptions(self) -> GraderOptions:
        # Eventually meld the user defaults with the assignment settings.
        return self._GraderOptions

    def add_required_file(self, new_file: submission_file_data):
        """Adds a new required file to the assignment.

        :param new_file: The new required file to add.

        Returns:
            This assignment object with the new required file added for chaining if desired.
        """
        self._required_files[str(new_file.path)] = new_file
        return self

    @property
    def year(self):
        return self._year

    @year.setter
    def year(self, value):
        self._year = value

    @property
    def grade_period(self):
        return self._grade_period

    @grade_period.setter
    def grade_period(self, value):
        self._grade_period = value

    @property
    def course(self):
        """The course name/number for the assignment."""
        return self._course

    @course.setter
    def course(self, value):
        """Sets the course name/number for the assignment."""
        self._course = value

    def get_missing_directories(self) -> list[pathlib.Path]:
        """Get a list of missing directories for the assignment."""
        return [d for d in self._directories if not d.exists()]

    def get_readme_files(self):
        """Get a list of README files that explain the directory structure."""
        return [
            (
                self.oaks_named_dir / "README.txt",
                f"""This {self.oaks_named_dir.relative_to(self._directory)} directory contains the PDFs for the
                 assignment that are named after the student's name as
                 oaks expects them so that they can be zipped and batch uploaded to oaks.
                 They are de-anonimized, symbolic links to the instructor edited pdfs from the ready_for_oaks
                 directory for each submission.""",
            ),
            (
                self.complete_eval_dir / "README.txt",
                f"""This {self.complete_eval_dir.relative_to(self._directory)} directory contains the PDFs (with
                 anonymous file names) for the assignment that are ready
                 for the instructor to review.
                 They are symbolic links to the original PDFs in the evaluation directory for each submission.""",
            ),
            (
                self.oaks_ready_dir / "README.txt",
                f"""This {self.oaks_ready_dir.relative_to(self._directory)} directory contains copies of the PDFs
                 from the evaluation
                directory for each submission.
                The instructor can edit them and the original PDFs are still stored in the evaluation directory.""",
            ),
            (
                self._directory / "pdfs" / "README.txt",
                f"""This {self.complete_eval_dir.parent.relative_to(self._directory)} directory contains
                 sub-directories with PDFs for each student.

                The {self.complete_eval_dir.name} directory contains links to the PDFs in the evaluation directory for
                each submission. The instructor SHOULD NOT edit the PDFs in this directory.

                The {self.oaks_ready_dir.name} directory should be filled with instructor marked-up copies of the PDFs
                from the evaluation directory for each submission.
                The instructor SHOULD put the completed pdfs in this directory.

                I zip these files up initially and copy them to my iPad, so that I can grade them.
                After completing the grades I overwrite the files in the evaluation directory with the completed pdfs
                from my iPad.

                The {self.oaks_named_dir.name} directory contains the PDFs for the assignment that are named after
                the student's name as oaks expects them so that they can be zipped and batch uploaded to oaks.
                After putting my evaluated pdfs in the {self.oaks_ready_dir.name} directory, I zip them up and upload
                them to oaks.""",
            ),
        ]

    def create_missing_directories(self):
        """Create missing directories for the assignment."""
        for d in self.get_missing_directories():
            d.mkdir(exist_ok=True, parents=True)

        readmes = self.get_readme_files()

        # Populate the directories with READMEs.
        for f, content in readmes:
            if not f.exists():
                f.parent.mkdir(exist_ok=True, parents=True)
                f.write_text(content)


@dataclass(kw_only=True)
class submission_data(DataclassJson):
    # Make all fields keyword-only so that they can be loaded from JSON.
    submission_file: pathlib.Path
    evaluation_directory: pathlib.Path
    anon_name: str
    original_name: str
    compiled_initially: bool | None = None
    initial_missing_files: list[str] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.submission_file is None:
            raise ValueError("submission_file must be set.")
        if self.evaluation_directory is None:
            raise ValueError("evaluation_directory must be set.")
        if not self.submission_file.exists() or not self.submission_file.is_file():
            raise ValueError(f"submission_file '{self.submission_file}' does not exist or is not a file.")
        if not self.evaluation_directory.exists() or not self.evaluation_directory.is_dir():
            raise ValueError(f"evaluation_directory '{self.evaluation_directory}' does not exist or is not a directory.")


class Submission(submission_data):
    """Represents a submission to an assignment.

    This class should be subclassed to represent different submission types (zip, tar, etc.).
    The class maintains an evaluation directory for the submission, compiles source code from the submission in this
    directory, and stores information about the submission.

    The source files are stored in the 'as_submitted' directory, and required files are copied to the evaluation
    directory.
    This is so the evaluator can fix any compilation errors before testing the submission, but the submission
    documentation will still reflect the original submission files.

    Perhaps in the future the documentation will automatically reflect a git diff between the original submission
    and any necessary changes made during testing.
    """

    SUBMISSION_FILE_NAME = "submission.json"
    AS_SUBMITTED_DIR_NAME = "as_submitted"

    def __init__(self, **kwargs):
        """
        Get an object instance representing a submission to an assignment.

        See `load` for loading a submission from a JSON file.
        See `new` for creating a brand-new submission from a submission file.

        :param assignment: This is the assignment this submission belongs to.
        :param kwargs: Keyword arguments to initialize the Submission object.
        """
        super().__init__(**kwargs)

        self.as_submitted_dir = self.evaluation_directory / "as_submitted"

        self.__post_init__()

    def save(self):
        super().save(self.evaluation_directory / self.SUBMISSION_FILE_NAME)

    @classmethod
    def load(cls, filepath: pathlib.Path):
        """Load a submission from a JSON file or a directory.

        These objects are stored in JSON files in the same directory as the assignment.
        They are intended to be short lived and dynamically loaded from any sub-directory.
        Therefore, if you pass in a directory, this will look for the JSON file in that directory and it's parents.

        :param filepath: Path to the JSON file or directory containing the assignment data.
        :raises FileNotFoundError: If the file or directory does not exist.
        :return: The loaded assignment object.
        """
        if filepath.exists() and filepath.is_dir():
            filepath = findFileInParents(filepath, cls.SUBMISSION_FILE_NAME)
            if filepath is None:
                raise FileNotFoundError(f"Could not find submission JSON file in {filepath} or any of its parents.")

        if filepath.exists() and filepath.is_file():
            data = json.loads(filepath.read_text())
            return cls._from_json(data)

        raise FileNotFoundError(filepath)

    @classmethod
    def new(cls, assignment: Assignment, submission_file: pathlib.Path):
        """
        _Submission.new: Create a brand-new submission from a submission file.

        Create a brand-new submission from a submission file.
        """

        # This is a brand-new submission. Create the evaluation directories and move the submission file there.
        anon_name = None
        base_file_name = submission_file.name
        base_file_name_set = False
        if assignment._options.anonymize_names:
            anon_name = cls.get_anon_name(assignment, submission_file)
        else:
            # See if we can parse an OAKS name from the submission file.
            # Ex: 341751-430460 - Alice Jones - Sep 18, 2025 1156 PM - p2sol.tar.gz
            match submission_file.stem.split(" - "):
                case [_, student_name, _, file_name]:
                    anon_name = student_name
                    base_file_name = file_name
                    base_file_name_set = True
                case _:
                    anon_name = submission_file.stem

        evaluation_directory = assignment.eval_dir / anon_name
        evaluation_directory.mkdir(exist_ok=True)

        # This is the directory where the submission files are stored.
        as_submitted_dir = evaluation_directory / cls.AS_SUBMITTED_DIR_NAME
        as_submitted_dir.mkdir(exist_ok=True, parents=True)

        my_submission_file = as_submitted_dir / (anon_name + "".join(submission_file.suffixes))
        if base_file_name_set:
            my_submission_file = as_submitted_dir / (base_file_name + "".join(submission_file.suffixes))

        # my_submission_file.symlink_to(submission_file)
        submission_file.rename(my_submission_file)

        ret_val = cls(
            submission_file=my_submission_file,
            evaluation_directory=evaluation_directory,
            anon_name=anon_name,
            original_name=submission_file.name,
        )
        ret_val.__post_process_new__(assignment)
        return ret_val

    def __post_init__(self):
        """
        This method should be overridden by subclasses to perform any post-processing required for brand-new
        submissions.

        .. important:: Any subclasses should call the super method.
        """
        super().__post_init__()

    def __post_process_new__(self, assignment: Assignment, base_file_name: str | None = None):
        """Post-process a brand-new submission.
        This method should be overridden by subclasses to perform any post-processing required for brand-new
        submissions.

        **Any subclasses should call the super method.**
        """
        if "tar" in self.submission_file.name:
            # If it is a tar file, we need to untar it.
            os.system(f'tar -xf "{self.submission_file.absolute()}" -C "{self.as_submitted_dir.absolute()}"')
        elif "zip" in self.submission_file.name:
            os.system(f'cd "{self.as_submitted_dir.absolute()}" && unzip "{self.submission_file.absolute()}"')
        elif base_file_name is not None:
            os.system(f'cp "{self.submission_file.absolute()}" "{self.evaluation_directory.absolute()}/{base_file_name}"')

        self._missing_files_initially = self.check_missing_files(assignment)

        # Make the submission file(s) private and readonly.
        # Also copy them to the evaluation directory if they are part of the required files.
        for f in self.as_submitted_dir.iterdir():
            if f.name in assignment.required_files.values():
                os.system(f'cp "{f.absolute()}" "{self.evaluation_directory.absolute()}"')
            f.chmod(0o400)

    def check_missing_files(self, assignment: Assignment) -> list[submission_file_data]:
        """Check if the submission is missing required files.
        :param assignment: The assignment this submission belongs to.
        :return: A list of missing required file names, or an empty list if the submission is missing no required files.
        """
        as_sub_files = [f.name for f in self.as_submitted_dir.iterdir()]
        return [required_file for required_file in assignment.required_files.values() if required_file not in as_sub_files]

    @classmethod
    def get_anon_name(cls, assignment: Assignment, submission_file: pathlib.Path):
        """Generate an anonymous name for the submission.

        Args:
            assignment (Assignment): The assignment this submission belongs to
            submission_file (pathlib.Path): Path to the submission file

        Returns:
            str: Anonymous name for the submission
        """
        return anonimizer.anonymize(submission_file.name, assignment.name, assignment.year, assignment.grade_period, assignment.course)


# class TarSubmission(Submission):
#   def post_process_new(self, assignment: Assignment):
#     os.system(f'tar -xf "{self.submission_file.absolute()}" -C "{self.as_submitted_dir.absolute()}"')
#     for f in self.as_submitted_dir.iterdir():
#       f.chmod(0o400)
#       if f.name in assignment.required_files:
#         os.system(f'cp "{f.absolute()}" "{assignment.evalDir.absolute()}"')
#
#     super().post_process_new(assignment)
