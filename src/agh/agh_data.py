import datetime
import json
import os
import pathlib
from collections.abc import Callable
from collections.abc import Generator
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from dataclasses import fields
from dataclasses import is_dataclass
from enum import IntEnum
from pathlib import Path
from string import Template
from typing import Any
from typing import Literal
from typing import Self
from typing import get_args
from typing import get_origin

import agh.anonymizer as anonymizer

DEFAULT_MAX_OUT_FILE_SIZE = 20 * 1024

META_INTERNAL_SUB_OUTPUT = "OUTPUT_INFO"

META_INTERNAL_SUB_KEY = "SUBMISSION"

META_AGH_INTERNAL_KEY = "AGH_INTERNAL"
META_INTERNAL_SUB_KEYS = [META_AGH_INTERNAL_KEY, META_INTERNAL_SUB_KEY]
META_INTERNAL_SUB_OUTPUT_COMPLETE = [META_AGH_INTERNAL_KEY, META_INTERNAL_SUB_KEY, META_INTERNAL_SUB_OUTPUT, "COMPLETED_OUTPUT"]
META_INTERNAL_SUB_OUTPUT_GRADED = [META_AGH_INTERNAL_KEY, META_INTERNAL_SUB_KEY, META_INTERNAL_SUB_OUTPUT, "GRADED"]
META_INTERNAL_SUB_OUTPUT_NON_ANON = [META_AGH_INTERNAL_KEY, META_INTERNAL_SUB_KEY, META_INTERNAL_SUB_OUTPUT, "NON_ANON"]

_USER_DEFAULTS_FILE = Path.home() / ".config" / "agh" / ".agh_user_defaults.json"


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
    Currently, it supports deserialization from JSON to dataclasses properly for:

    - Directly nested dataclasses.
    - Single-level lists of DataclassJson subclasses (in the type hint must have dataclass as the first or only type).
    - Dictionaries where the value type is a subclass of DataclassJson.
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
class SubmissionFileData(DataclassJson):
    path: pathlib.Path
    title: str = ""
    type: str = "default"
    include_in_output: bool = True
    description: str = ""
    unlisted: bool = False
    copy_to_sub_if_missing: bool = True

    def __post_init__(self):
        if self.title == "":
            if isinstance(self.path, str):
                self.path = pathlib.Path(self.path)
                self.title = self.path.name
            else:
                self.title = self.path.name

    @property
    def anchorText(self) -> str:
        """Returns the anchor text for the section suitable in use for Markdown links."""
        return f"{self.title.lower().replace(' ', '-')}"

    @property
    def qmdLink(self) -> str:
        return f"[{self.title}]({self.title}.qmd)"

    @property
    def sectionAttr(self) -> str:
        if self.unlisted:
            return " {.unlisted .unnumbered}"
        return ""

    def asQmdSection(self, heading_level: int, max_file_size: int = DEFAULT_MAX_OUT_FILE_SIZE) -> str:
        if not self.include_in_output:
            return ""
        # if not self.path.exists():
        #     self.path.touch()

        # Check for excessive length.
        hdr_txt = "#" * heading_level + " " + self.title + self.sectionAttr
        ret_val = f"\n\n{hdr_txt}\n\n{self.description}\n\n"
        if self.path.exists() and self.path.stat().st_size > max_file_size:
            with self.path.open("rt", encoding="utf-8", errors="replace") as f:
                ret_val += (
                    f"**[File too large! Contents truncated to {max_file_size} bytes.]{{.mark}}**\n\n```{{."
                    f"{self.type}}}\n{f.read(max_file_size)}\n```\n\n"
                )
            return ret_val

        return f"{ret_val}```{{.{self.type}}}\n{{{{< include {self.path} >}}}}\n```\n\n"


# Mark all fields as keyword-only so that we can load directly from JSON.
@dataclass(kw_only=True)
class OutputSectionData(SubmissionFileData):
    text: str = ""
    instructor_section: bool = False
    heading_level: int = 2
    included_files: list[SubmissionFileData] = field(default_factory=list)
    included_sections: list["OutputSectionData"] = field(default_factory=list)
    only_output_if_data: bool = False
    post_script: str = ""
    _errors: list[dict[Literal["title", "message"], str]] = field(default_factory=list)
    _warnings: list[dict[Literal["title", "message"], str]] = field(default_factory=list)

    @property
    def hasData(self):
        if len(self._errors) > 0 or len(self._warnings) > 0:
            return True
        elif len(self.included_sections) > 0 or len(self.included_files) > 0:
            return True in [cur_sub_sec.hasData for cur_sub_sec in self.included_sections] or True in [
                (cur_inc_file.path.exists() and cur_inc_file.path.stat().st_size > 1) for cur_inc_file in self.included_files
            ]
        elif self.text.strip() != "":
            # If there are no 'includes' then the section is the data
            return True
        return False

    def asQmdSection(self) -> str:
        if not self.hasData and self.only_output_if_data:
            return ""
        inc_file_txt = "\n\n".join([cur_inc_file.asQmdSection(self.heading_level + 1) for cur_inc_file in self.included_files])
        inc_sec_txt = "\n\n".join([cur_inc_sec.asQmdSection() for cur_inc_sec in self.included_sections])

        warnings = ""
        for warn in self._warnings:
            warnings += f"\n\n+ **{warn['title']}:** {warn['message']}"
        if warnings != "":
            warnings = f'\n\n::: {{.callout-note title="To Consider"}}\n\n{warnings}\n\n:::\n\n'

        errors = ""
        for err in self._errors:
            errors += f"\n\n+ **{err['title']}:** {err['message']}"
        if errors != "":
            errors = f'\n\n::: {{.callout-important title="Errors"}}\n\n{errors}\n\n:::\n\n'

        pre = "#" * self.heading_level + f" {self.title} {self.sectionAttr}\n\n{self.description}\n\n{self.text}{errors}{warnings}"
        return f"{pre}\n\n{inc_file_txt}\n\n{inc_sec_txt}\n\n{self.post_script}"

    def addSection(self, section: "OutputSectionData") -> Self:
        self.included_sections.append(section)
        section.heading_level = self.heading_level + 1
        return self

    def addWarning(self, warn_title: str, warn_msg: str) -> Self:
        self._errors.append({"title": warn_title, "message": warn_msg})
        return self

    def addError(self, error_title: str, error_msg: str) -> Self:
        self._errors.append({"title": error_title, "message": error_msg})
        return self


@dataclass(kw_only=True)
class MetaDataclassJson(DataclassJson):
    """A mixin class that adds support for serializing dataclasses to JSON."""

    _metadata: dict[str, Any] = field(default_factory=dict)

    def _getMetadata(self, metadata_key: str, default: Any = None) -> dict[str, Any] | Any:
        """Returns the metadata associated with the assignment.
        If the key is not present in the metadata, it will return the default value.

        :param metadata_key: This should be a dot-separated string.
            E.g. 'course.name.short' would get the following:
            {'course': {'name': {'short': `value`}}} creating sub-dictionaries as necessary,
            while also preserving existing keys at each level.
        :param default: The default value to return if the key is not present in the metadata.
        :return: The value associated with the key, or the default value if the key is not present."""
        cur_metadata = self._metadata
        for key in metadata_key.split("."):
            if key in cur_metadata:
                cur_metadata = cur_metadata[key]
            else:
                return default
        return cur_metadata

    def getMetadata(self, *args, default: Any = None) -> dict[str, Any] | Any:
        """Returns the metadata associated with the assignment.

        If the key is not present in the metadata, it will return the default value.
        :param args: This should be a series of strings.
            E.g. ``getMetadata('course', 'name', 'short', default)`` would get the following:
            ``{'course': {'name': {'short': value or default}}}`` creating sub-dictionaries as necessary,
            while also preserving existing keys at each level.
        :param default: The default value to return if the key is not present in the metadata.
        :return: The value associated with the key, or the default value if the key is not present."""
        return self._getMetadata(".".join(args), default=default)

    def _setMetadata(self, metadata_key: str, value: Any) -> Self:
        """This sets the metadata associated with the assignment.

        :param metadata_key: This should be a dot-separated string.
            E.g. 'course.name.short' would set successive keys in dictionaries
            {'course': {'name': {'short': `value`}}} while also preserving existing keys at each level.
        :param value: The value to set.
        :return: This object for chaining.
            Ex: ``obj.setMetadata('key', 'value').setMetadata('key2', 'value2')``
        :rtype: Self
        """
        metadata_keys = [key.strip() for key in metadata_key.strip().split(".")]
        if "" in metadata_keys:
            raise ValueError("Cannot set metadata with empty key. key: " + metadata_key)
        cur_metadata: dict[str, dict | Any] = self._metadata
        # Loop down to the last level to set.
        for key in metadata_keys[:-1]:
            if key not in cur_metadata:
                cur_metadata[key] = {}
            cur_metadata = cur_metadata[key]
        cur_metadata[metadata_keys[-1]] = value
        return self

    def setMetadata(self, *args, value: Any) -> Self:
        """Returns the metadata associated with the assignment.

        If the key is not present in the metadata, it will return the default value.
        :param args: This should be a series of strings.
            E.g. ``setMetadata('course', 'name', 'short', default)`` would set the following:
            ``{'course': {'name': {'short': value or default}}}`` creating sub-dictionaries as necessary,
            while also preserving existing keys at each level.
        :param value: The value to set.
        :return: This object for chaining.
            Ex: ``obj.setMetadata('key', 'value').setMetadata('key2', 'value2')``
        :rtype: Self
        """
        return self._setMetadata(".".join(args), value=value)


def _gen_prop_methods(parameter: str, default: Any):
    """Helper function to generate properties and methods for a given parameter for GraderOptions class."""
    return (
        lambda self: self._getValue(parameter, default),
        lambda self, value: self._setValue(parameter, value),
        lambda self: self._delValue(parameter),
    )


# Mark all fields as keyword-only so that we can load directly from JSON.
@dataclass(kw_only=True)
class GraderOptions(MetaDataclassJson):
    """Serializable data container for grading options.
    There will be a global user configuration file that contains the default grading options.

    This will also be contained in the assignment data for per-assignment options.
    """

    # todo: Figure out how to load defaults from ~/.config/agh/agh_user_defaults.json

    # This determines if the names of students are anonymized.
    anonymize_names: bool = field(default=True)

    # A list of files generated by the output. The first file is considered the primary output file.
    _output_files: list[str] | None = None
    output_files = property(
        *_gen_prop_methods("_output_files", ["index.pdf"]),
        doc="A list of files generated by the output. The first file is considered the primary output file.",
    )

    output_template_name: str = "index.qmd"
    template_editor_command: Template = "subl $file"
    test_editor_command: Template = "subl $file"
    default_test_file_name: str = "test-assignment.py"

    _general_editor_command: str | None = None
    general_editor_command = property(
        *_gen_prop_methods("_general_editor_command", "subl $files"), doc="A command to open a submission file in a text editor."
    )

    # This is a dictionary of metadata associated with the assignment.
    # _metadata: dict[str, Any] = field(default_factory=dict)

    def _getValue(self, property, default):
        # This function should be used to construct the property getter.
        if getattr(self, property) is not None:
            return getattr(self, property)
        else:
            user_defaults = self.loadUserDefaults()
            if getattr(user_defaults, property, default) is not None:
                return getattr(user_defaults, property, default)
            else:
                return default

    def _setValue(self, property, value):
        # This function should be used to construct the property setter.
        setattr(self, property, value)

    def _delValue(self, property):
        # This function should be used to construct the property deleter.
        delattr(self, property)

    def _getMetadata(self, metadata_key: str, default: Any = None) -> dict[str, Any]:
        """Returns the metadata associated with the assignment.
        If the key is not present in the metadata, it will return the default value."""
        cur_metadata = self._metadata
        user_defaults = self.loadUserDefaults()
        user_metadata = user_defaults._metadata
        for key in metadata_key.split("."):
            user_metadata = user_metadata.get(key, {})
            if key in cur_metadata:
                cur_metadata = cur_metadata[key]
            elif user_metadata:
                cur_metadata = user_metadata
            else:
                return default

        return cur_metadata

    # @property
    # def output_files(self):
    #     if self._output_files is None:
    #         user_defaults = self.loadUserDefaults()
    #         if user_defaults._output_files is not None:
    #             return user_defaults._output_files
    #         else:
    #             return ["index.pdf"]
    #     else:
    #         return self._output_files
    #
    # @output_files.setter
    # def output_files(self, value: list[str] | None):
    #     self._output_files = value

    @classmethod
    def loadUserDefaults(cls):
        """This function loads the user defaults from the user's default configuration file.

        :return: GraderOptions object with the loaded user defaults.
        """
        user_defaults_file = _USER_DEFAULTS_FILE
        user_defaults_file.parent.mkdir(parents=True, exist_ok=True)
        if user_defaults_file.exists():
            return cls.load_json(user_defaults_file)
        else:
            return cls()

    def saveAsUserDefaults(self):
        self.save(_USER_DEFAULTS_FILE)

    # def editTemplate(self) -> None:
    #     """Open the assignment's output template in the user's default editor."""
    #     assert self.template_editor_command is not None
    #     assert isinstance(self.template_editor_command, Template)
    #     assignment = Assignment.load()
    #
    #     os.system(self.template_editor_command.substitute(file=self.output_template_name,
    #                                                       assignment_directory=assignment.root_directory))
    #
    # def editTests(self) -> None:
    #     """Open the assignment's test files in the user's default editor."""
    #     assert self.test_editor_command is not None
    #     assert isinstance(self.test_editor_command, Template)
    #     assignment = Assignment.load()
    #     os.system(self.test_editor_command.substitute(file=self.default_test_file_name,
    #                                                   assignment_directory=assignment.root_directory))


# Mark all fields as keyword-only so that we can load directly from JSON.
@dataclass(kw_only=True)
class AssignmentData(MetaDataclassJson):
    _name: str = "assignment"
    _year: int = 2025
    _grade_period: str = "Fall"
    _course: str = "CSCI-340"
    _required_files: dict[str, SubmissionFileData] = field(default_factory=dict)
    _optional_files: dict[str, SubmissionFileData] = field(default_factory=dict)
    _options: GraderOptions = field(default_factory=GraderOptions)
    # metadata: dict[str, Any] = field(default_factory=dict)


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
        cur_date = datetime.datetime.now(tz=datetime.timezone.utc)
        cur_date = cur_date.astimezone()
        if "_year" not in kwargs:
            kwargs["_year"] = cur_date.year
        if "_grade_period" not in kwargs:
            period = "Fall"
            match cur_date.month:
                case 1 | 2 | 3:
                    period = "Spring"
                case 4 | 5:
                    period = "Maymester"
                case 6:
                    period = "SummerI"
                case 7:
                    period = "SummerII"
                case 11 | 12:
                    period = "Winter"
                case _:
                    period = "Fall"
            kwargs["_grade_period"] = period

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

        # Input - submission directories
        self._archive_dir = input_dir / "archive"
        self._directories.add(self._archive_dir)
        # self._to_process_dir = self._directory / 'to_process'
        self._unprocessed_dir = input_dir / "unprocessed/"
        self._directories.add(self._unprocessed_dir)
        self._eval_dir = input_dir / "evaluations/"
        self._directories.add(self._eval_dir)

        # Output
        self._complete_eval_dir = output_dir / "as_rendered"
        self._directories.add(self._complete_eval_dir)
        self._oaks_ready_dir = output_dir / "graded"
        self._directories.add(self._oaks_ready_dir)
        self._oaks_named_dir = output_dir / "de-anonymized"
        self._directories.add(self._oaks_named_dir)

        # Assignment information and how to test the submissions.
        self._template_dir = assignment_dir / "template/"
        self._directories.add(self._template_dir)
        self._link_template_dir = self._template_dir
        self._directories.add(self._link_template_dir)
        self._assignment_description_dir = assignment_dir / "description"
        self._directories.add(self._assignment_description_dir)
        self._tests_dir = assignment_dir / "tests"
        self._directories.add(self._tests_dir)

    @classmethod
    def load(cls, filepath: pathlib.Path | None = None):
        """Load an assignment from a JSON file or a directory.

        These objects are stored in JSON files in the same directory as the assignment.
        They are intended to be short lived and dynamically loaded from any sub-directory.
        Therefore, if you pass in a directory, this will look for the JSON file in that directory and it's parents.

        :param filepath: Path to the JSON file or directory containing the assignment data.
        :raises FileNotFoundError: If the file or directory does not exist.
        :return: The loaded assignment object.
        """
        if filepath is None:
            filepath = pathlib.Path.cwd()

        if filepath.exists() and filepath.is_dir():
            orig_filepath = filepath
            filepath = filepath.absolute()
            filepath = findFileInParents(filepath, cls.ASSIGNMENT_FILE_NAME)
            if filepath is None:
                raise FileNotFoundError(f"Could not find assignment JSON file in {orig_filepath} or any of its parents.")

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
    def archive_dir(self) -> pathlib.Path:
        """Directory containing archived submission files."""
        return self._archive_dir

    @property
    def unprocessed_dir(self) -> pathlib.Path:
        """Directory containing unprocessed submission files."""
        return self._unprocessed_dir

    @property
    def eval_dir(self) -> pathlib.Path:
        """Directory containing submission evaluation files."""
        return self._eval_dir

    @property
    def complete_eval_dir(self) -> pathlib.Path:
        """Directory containing completed evaluation PDFs."""
        return self._complete_eval_dir

    @property
    def graded_output_dir(self) -> pathlib.Path:
        """Directory containing graded files."""
        return self._oaks_ready_dir

    @property
    def d2l_named_dir(self) -> pathlib.Path:
        """Directory containing de-anonymized files for D2L LMS (OAKS)."""
        return self._oaks_named_dir

    @property
    def link_template_dir(self) -> pathlib.Path:
        """Directory containing files to link into submission directories.

        Instructors should use this to link files into the submission directories that are needed to run the tests.
        This could include Makefiles that work with the build system, or headers that the students were not supposed
        to edit.
        """
        return self._template_dir

    @property
    def assignment_description_dir(self) -> pathlib.Path:
        """Directory containing files that describe the assignment.
        Instructors can use this to describe the assignment to students as the source of files posted in a LMS system.

        This can be empty.
        """
        return self._assignment_description_dir

    @property
    def tests_dir(self) -> pathlib.Path:
        """Directory containing test files suitable for use with pytest that test the submissions of the assignment.

        This directory MUST contain some files. It may just be a single file named _options.default_test_file_name.
        It could also contain multiple test files that work in combination to test the submissions.
        """
        return self._tests_dir

    @property
    def root_directory(self) -> pathlib.Path:
        """The root directory of the assignment."""
        return self._directory

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
        for submission_file in self._directory.rglob(Submission.SUBMISSION_FILE_NAME):
            yield Submission.load(submission_file)

    class LinkProto(IntEnum):
        # Raise an error if the file exists.
        RAISE_ERROR = 0
        # Ignore an error and continue with the rest of the links if the file exists (don't do anything).
        IGNORE_ERROR = 1
        # Overwrite the existing file if it already exists.
        LINK_OVERWRITE = 2

    def PostProcessSubmission(
        self,
        submission_file: "pathlib.Path|Submission",
        exists_protocol: LinkProto = LinkProto.RAISE_ERROR,
        warning_callback: Callable[[str], None | Any] | None = None,
    ) -> "Submission":
        ret_val: Submission = submission_file
        if isinstance(submission_file, pathlib.Path):
            ret_val = Submission.load(filepath=submission_file)

        # link in the tests.

        def all_linked_files() -> Generator[Path]:
            """Internal generator to get all the files to be linked."""
            yield self.tests_dir
            for link_item in self.link_template_dir.iterdir():
                yield link_item
            for link_item in self._optional_files.values():
                if link_item.copy_to_sub_if_missing and not (ret_val.evaluation_directory / link_item.path.name).exists():
                    yield link_item.path

        for link_item in all_linked_files():
            link_tgt = ret_val.evaluation_directory / link_item.name

            # Handle if the target is also a symlink
            if link_item.is_symlink():
                link_item = link_item.readlink()

            # Depending on the protocol handle if there is already an existing link.
            if link_tgt.exists():
                # Handle if the link exists but is pointing to the correct target already - continue.
                if link_tgt.is_symlink() and link_tgt.readlink() == link_item:
                    continue

                match exists_protocol:
                    case self.LinkProto.RAISE_ERROR:
                        raise FileExistsError(link_tgt)
                    case self.LinkProto.IGNORE_ERROR:
                        continue
                    case self.LinkProto.LINK_OVERWRITE:
                        link_tgt.unlink()
                    case _:
                        raise NotImplementedError("New existing link protocol added, but code not added")

            link_tgt.symlink_to(link_item.absolute(), target_is_directory=link_item.is_dir())

        # Now start linking the output stuff together.
        return self.postProcessSubmissionRender(ret_val, warning_callback=warning_callback)

    def postProcessSubmissionRender(
        self, submission: "Submission", warning_callback: Callable[[str], None | Any] | None = None
    ) -> "Submission":
        for output_file in self._options.output_files:
            output_in_sub_dir = submission.evaluation_directory / output_file
            output_file = self.complete_eval_dir / (submission.evaluation_directory.name + output_in_sub_dir.suffix)
            submission.setMetadata(*META_INTERNAL_SUB_OUTPUT_COMPLETE, value=str(output_file))
            output_not_anon = self.d2l_named_dir / (submission.original_name + output_in_sub_dir.suffix)
            submission.setMetadata(*META_INTERNAL_SUB_OUTPUT_NON_ANON, value=str(output_not_anon))
            output_graded = self.graded_output_dir / output_file.name
            submission.setMetadata(*META_INTERNAL_SUB_OUTPUT_GRADED, value=str(output_graded))
            try:
                # Copy output_in_sub_dir to output_graded if needed
                if (not output_graded.exists()) or (
                    output_graded.exists() and output_graded.stat().st_ctime_ns == output_graded.stat().st_mtime_ns
                ):
                    output_graded.parent.mkdir(parents=True, exist_ok=True)

                    #  This is to ensure that ctime == mtime!
                    output_graded.unlink(missing_ok=True)

                    output_graded.write_bytes(output_in_sub_dir.read_bytes())
                elif warning_callback is not None:
                    warning_callback(
                        f'The graded output file "{output_graded}" already exists and appears modified. '
                        f"{output_graded} will not be overwritten."
                    )
                    # stats = output_graded.stat()
                    # warning_callback(f'The graded output file info a:{stats.st_atime_ns}, c: {stats.st_ctime_ns},
                    # m: {stats.st_mtime_ns}.')

                output_file.unlink(missing_ok=True)
                output_not_anon.unlink(missing_ok=True)
            except FileNotFoundError:
                pass
            # Create symbolic links
            output_file.symlink_to(
                output_in_sub_dir.relative_to(output_file.parent, walk_up=True), target_is_directory=output_file.is_dir()
            )
            # output_file.chmod(0o444)

            output_not_anon.symlink_to(
                output_graded.relative_to(output_not_anon.parent, walk_up=True), target_is_directory=output_not_anon.is_dir()
            )

        return submission

    def AddSubmission(
        self, submission_file: pathlib.Path, override_anon: bool | None = None, warning_callback: Callable[[str], None | Any] | None = None
    ) -> "Submission":
        """Add a new submission to the assignment.
        :param submission_file: The path to the submission file to add.
        :param override_anon: If none then abide by the default for the assignment.
        If True then make it anonymous even if assignment is default non-anonymous.
        If False then make it non-anonymous even if assignment is default anonymous.
        :param warning_callback: A callback function to be called when a warning is encountered.
        :return: The new submission.
        :rtype: "Submission"
        """
        ret_val = Submission.new(self, submission_file=submission_file, override_anon=override_anon)
        ret_val.save()
        return self.PostProcessSubmission(ret_val, exists_protocol=self.LinkProto.RAISE_ERROR, warning_callback=warning_callback)

    # def __pytest_cmd(self):
    #     return "pytest ./ -p shell-utilities -p agh"

    # def RunTests(self, submissions_to_test: Iterable["Submission"] | None = None):
    #     if submissions_to_test is None:
    #         submissions_to_test = self.Submissions
    #
    #     for submission in submissions_to_test:
    #         self.RunTestsOnSubmission(submission)
    #
    # def RunTestsOnSubmission(self, submission_to_test: "Submission"):
    #     os.system(f'cd "{submission_to_test.evaluation_directory}" && {self.__pytest_cmd()}')
    #
    # def RunBuildOnSubmission(self, submission_to_test: "Submission"):
    #     os.system(f'cd "{submission_to_test.evaluation_directory}" && {self.__pytest_cmd()} -m build')

    @property
    def required_files(self):
        return self._required_files

    @property
    def GraderOptions(self) -> GraderOptions:
        # Eventually meld the user defaults with the assignment settings.
        return self._options

    def addRequiredFile(self, new_file: SubmissionFileData) -> "Assignment":
        """Adds a new required file to the assignment.

        :param new_file: The new required file to add.

        Returns:
            This assignment object with the new required file added for chaining if desired.
        """
        self._required_files[str(new_file.path)] = new_file
        return self

    @property
    def optional_files(self):
        return self._optional_files

    def addOptionalFile(self, new_file: SubmissionFileData) -> "Assignment":
        """Adds a new optional file to the assignment.

        :param new_file: The new optional file to add.
        """
        self._optional_files[str(new_file.path)] = new_file
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

    def getMissingDirectories(self) -> list[pathlib.Path]:
        """Get a list of missing directories for the assignment."""
        return [d for d in self._directories if not d.exists()]

    # def get_readme_files(self):
    #     """Get a list of README files that explain the directory structure."""
    #     return [
    #         (
    #             self.d2l_named_dir / "README.txt",
    #             f"""This {self.d2l_named_dir.relative_to(self._directory)} directory contains the PDFs for the
    #              assignment that are named after the student's name as
    #              oaks expects them so that they can be zipped and batch uploaded to oaks.
    #              They are de-anonymized, symbolic links to the instructor edited pdfs from the ready_for_oaks
    #              directory for each submission.""",
    #         ),
    #         (
    #             self.complete_eval_dir / "README.txt",
    #             f"""This {self.complete_eval_dir.relative_to(self._directory)} directory contains the PDFs (with
    #              anonymous file names) for the assignment that are ready
    #              for the instructor to review.
    #              They are symbolic links to the original PDFs in the evaluation directory for each submission.""",
    #         ),
    #         (
    #             self.graded_output_dir / "README.txt",
    #             f"""This {self.graded_output_dir.relative_to(self._directory)} directory contains copies of the PDFs
    #              from the evaluation
    #             directory for each submission.
    #             The instructor can edit them and the original PDFs are still stored in the evaluation directory.""",
    #         ),
    #         (
    #             self._directory / "pdfs" / "README.txt",
    #             f"""This {self.complete_eval_dir.parent.relative_to(self._directory)} directory contains
    #              sub-directories with PDFs for each student.
    #
    #             The {self.complete_eval_dir.name} directory contains links to the PDFs in the evaluation directory for
    #             each submission. The instructor SHOULD NOT edit the PDFs in this directory.
    #
    #             The {self.graded_output_dir.name} directory should be filled with instructor marked-up copies of
    #             the PDFs
    #             from the evaluation directory for each submission.
    #             The instructor SHOULD put the completed pdfs in this directory.
    #
    #             I zip these files up initially and copy them to my iPad, so that I can grade them.
    #             After completing the grades I overwrite the files in the evaluation directory with the completed pdfs
    #             from my iPad.
    #
    #             The {self.d2l_named_dir.name} directory contains the PDFs for the assignment that are named after
    #             the student's name as oaks expects them so that they can be zipped and batch uploaded to oaks.
    #             After putting my evaluated pdfs in the {self.graded_output_dir.name} directory, I zip them up and
    #             upload
    #             them to oaks.""",
    #         ),
    #     ]

    def createMissingDirectories(self):
        """Create missing directories for the assignment."""
        for d in self.getMissingDirectories():
            d.mkdir(exist_ok=True, parents=True)

        # readmes = self.get_readme_files()

        # Populate the directories with README files.
        # for f, content in readmes:
        #     if not f.exists():
        #         f.parent.mkdir(exist_ok=True, parents=True)
        #         f.write_text(content)


@dataclass(kw_only=True)
class SubmissionData(MetaDataclassJson):
    # Make all fields keyword-only so that they can be loaded from JSON.
    submission_file: pathlib.Path
    evaluation_directory: pathlib.Path
    anon_name: str
    original_name: str
    # compiled_initially: bool | None = None

    # This lists any of the required files that are missing.
    initial_missing_files: list[str] | None = None

    # This can be used to store additional metadata about the submission by test cases etc.
    # metadata: dict[str, Any] = field(default_factory=dict)

    # The section this submission belongs to.
    section: str | None = None

    def __post_init__(self):
        if self.submission_file is None:
            raise ValueError("submission_file must be set.")
        if self.evaluation_directory is None:
            raise ValueError("evaluation_directory must be set.")
        if not self.submission_file.exists() or not self.submission_file.is_file():
            raise ValueError(f"submission_file '{self.submission_file}' does not exist or is not a file.")
        if not self.evaluation_directory.exists() or not self.evaluation_directory.is_dir():
            raise ValueError(f"evaluation_directory '{self.evaluation_directory}' does not exist or is not a directory.")


class Submission(SubmissionData):
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

    # def __init__(self, compiled_initially=None, **kwargs):
    def __init__(self, **kwargs):
        """
        Get an object instance representing a submission to an assignment.

        See `load` for loading a submission from a JSON file.
        See `new` for creating a brand-new submission from a submission file.

        :param assignment: This is the assignment this submission belongs to.
        :param kwargs: Keyword arguments to initialize the Submission object.
        """
        super().__init__(**kwargs)

        self._as_submitted_dir = self.evaluation_directory / "as_submitted"

        self.__post_init__()

    def save(self):
        super().save(self.evaluation_directory / self.SUBMISSION_FILE_NAME)

    @classmethod
    def get_anon_name(cls, assignment: Assignment, submission_file: pathlib.Path):
        """Generate an anonymous name for the submission.

        Args:
            assignment (Assignment): The assignment this submission belongs to
            submission_file (pathlib.Path): Path to the submission file

        Returns:
            str: Anonymous name for the submission
        """
        return anonymizer.anonymize(submission_file.name, assignment.name, str(assignment.year), assignment.grade_period, assignment.course)

    @classmethod
    def load(cls, filepath: pathlib.Path | None = None):
        """Load a submission from a JSON file or a directory.

        These objects are stored in JSON files in the same directory as the assignment.
        They are intended to be short lived and dynamically loaded from any sub-directory.
        Therefore, if you pass in a directory, this will look for the JSON file in that directory and it's parents.

        :param filepath: Path to the JSON file or directory containing the assignment data.
        :raises FileNotFoundError: If the file or directory does not exist.
        :return: The loaded assignment object.
        """
        if filepath is None:
            filepath = pathlib.Path.cwd()

        if filepath.exists() and filepath.is_dir():
            orig_filepath = filepath
            filepath = filepath.absolute()
            filepath = findFileInParents(filepath, cls.SUBMISSION_FILE_NAME)
            if filepath is None:
                raise FileNotFoundError(f"Could not find submission JSON file in {orig_filepath} or any of its parents.")

        if filepath.exists() and filepath.is_file():
            data = json.loads(filepath.read_text())
            return cls._from_json(data)

        raise FileNotFoundError(filepath)

    @classmethod
    def new(cls, assignment: Assignment, submission_file: pathlib.Path, override_anon: bool | None = None):
        """
        _Submission.new: Create a brand-new submission from a submission file.

        Create a brand-new submission from a submission file.
        """

        # This is a brand-new submission. Create the evaluation directories and move the submission file there.
        anon_name = None
        base_file_name = submission_file.name
        base_file_name_set = False
        make_anon: bool = assignment._options.anonymize_names
        if override_anon is not None:
            make_anon = override_anon

        if make_anon:
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
                    anon_name = submission_file.with_suffix("").name

        evaluation_directory = assignment.eval_dir / anon_name
        evaluation_directory.mkdir(exist_ok=True, parents=True)

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

    @property
    def as_submitted_dir(self):
        """The directory where the submission files are stored.

        The contents of this directory are copied to the root of the evaluation directory.
        This is so the evaluator can fix any compilation errors before testing the submission, but the submission
        file contents printed in the output will still reflect the original submission files.
        """
        return self._as_submitted_dir

    def fix(self, assignment: Assignment):
        """Try to fix errors in the submission directory."""
        self.__post_process_new__(assignment)

    def __post_process_new__(self, assignment: Assignment, base_file_name: str | None = None):
        """Post-process a brand-new submission.
        This method should be overridden by subclasses to perform any post-processing required for brand-new
        submissions.

        **Subclasses should call the super method.**
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
            if f.name in assignment.required_files.keys() or f.name in assignment._optional_files.keys():
                os.system(f'cp "{f.absolute()}" "{self.evaluation_directory.absolute()}"')
            f.chmod(0o400)

    def check_missing_files(self, assignment: Assignment) -> list[Path]:
        """Check if the submission is missing required files.
        :param assignment: The assignment this submission belongs to.
        :return: A list of missing required file names, or an empty list if the submission is missing no required files.
        """
        as_sub_files = [f.name for f in self.as_submitted_dir.iterdir()]
        return [
            (self.as_submitted_dir / required_file)
            for required_file in assignment.required_files.keys()
            if required_file not in as_sub_files
        ]

    @property
    def name(self):
        """The name of the submission."""
        return self.anon_name

    @property
    def main_output_files(self) -> list[Path | None]:
        """Return the submission's output files.
        :return: A list of output files as follows:
        ``[<main-output-file-where-rendered>,
        <output-file-with-anon-name-in-output-directory>, <output-file-with-anon-name-in-GRADED-output-directory>,
        <output-file-with-NON-anon-name-in-output-directory>]``
        """
        assign = Assignment.load()
        rendered = None
        for output_file in assign._options.output_files:
            output_file = self.evaluation_directory / output_file
            if output_file.exists():
                rendered = output_file

        main = self.getMetadata(*META_INTERNAL_SUB_OUTPUT_COMPLETE)
        graded = self.getMetadata(*META_INTERNAL_SUB_OUTPUT_GRADED)
        non_anon: None | str | Path = self.getMetadata(*META_INTERNAL_SUB_OUTPUT_NON_ANON)

        if main is not None:
            main = Path(main)
        if graded is not None:
            graded = Path(graded)
        if non_anon is not None:
            non_anon = Path(non_anon)

        return [rendered, main, graded, non_anon]

    # The next three methods have to do with getting, setting, and clearing errors or warnings.
    def _getErrWarnList(self, type: Literal["errors", "warnings"]) -> list[str]:
        return list(self.getMetadata(*META_INTERNAL_SUB_KEYS, type, default={}).values())

    def _setErrWarnItem(self, type: Literal["errors", "warnings"], key: str, txt_or_markdown: str) -> Self:
        keys = list(META_INTERNAL_SUB_KEYS)
        keys.append(type)
        keys.append(key)
        return self.setMetadata(*keys, value=txt_or_markdown)

    def _delErrWarnItem(self, type: Literal["errors", "warnings"], key: str) -> Self:
        exist_md_dict: dict[Any, Any] = self.getMetadata(*META_INTERNAL_SUB_KEYS, type, default={})
        exist_md_dict.pop(key, None)
        return self.setMetadata(*META_INTERNAL_SUB_KEYS, type, value=exist_md_dict)

    @property
    def errors(self) -> None | list[str]:
        """Check if the submission has errors.
        These are NOT testing errors, but anything preventing the submission from being tested.
        """
        errors: list[str] = self._getErrWarnList("errors")
        if not self.as_submitted_dir.exists():
            errors.append(f"Submission directory '{self.as_submitted_dir.absolute()}' does not exist.")
            return errors

        missing_files = self.check_missing_files(Assignment.load())
        if len(missing_files) > 0:
            errors.append(f"Missing required file{'s' if len(missing_files) > 1 else ''}: {[mf.name for mf in missing_files]}")

        if len(errors) > 0:
            return errors

        return None

    def addError(self, key: str, txt_or_markdown: str) -> "Submission":
        """Add an error to the submission.
        These are NOT testing errors, but anything preventing the submission from being tested.
        """

        # DON'T USE the property above. It adds transient errors. Just get the metadata and add to it.
        return self._setErrWarnItem("errors", key, txt_or_markdown)
        # errors: list[str] = self.getMetadata(META_AGH_INTERNAL_KEY, META_INTERNAL_SUB_KEY, "errors", default=[])
        # errors.append(txt_or_markdown)
        # return self.setMetadata(META_AGH_INTERNAL_KEY, META_INTERNAL_SUB_KEY, "errors", value=errors)

    def delError(self, key: str) -> "Submission":
        return self._delErrWarnItem("errors", key)

    @property
    def warnings(self) -> None | list[str]:
        """Check if the submission has warnings.
        These are NOT testing warnings, but anything possibly preventing the submission from being tested.
        """
        return self._getErrWarnList("warnings")

    def addWarning(self, key: str, txt_or_markdown: str) -> "Submission":
        """Add a warning to the submission.
        These are NOT testing warnings, but anything possibly preventing the submission from being tested.
        """
        return self._setErrWarnItem("warnings", key, txt_or_markdown)

    def delWarning(self, key: str) -> "Submission":
        return self._delErrWarnItem("warnings", key)
