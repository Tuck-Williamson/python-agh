import os
import signal
from collections.abc import Callable
from pathlib import Path

import pytest
from pytestshellutils.shell import ProcessResult
from pytestshellutils.shell import ScriptSubprocess

from .agh_data import Assignment
from .agh_data import OutputSectionData
from .agh_data import Submission
from .agh_data import SubmissionFileData

TEST_MD_KEY = "TEST_INFO"

CORE_DUMP_FILE_NAME = "aghAssignmentCoreDump.core"


class AghPtPlugin:
    def __init__(self, config):
        self.config = config
        self.test_dirs = []
        self.results = {}

    def pytest_report_header(config, start_path, startdir):
        return "AGH Loaded"

    def pytest_terminal_summary(self, terminalreporter, exitstatus, config):
        terminalreporter.write_line("[purple]AGH[/] Test run complete.")
        # terminalreporter.write_line("JSON report saved to rich_parallel_report.json")


def pytest_addoption(parser):
    parser.addoption("--agh", action="store_true", help="Enable AGH, assignment grading helper, extensions.")


def pytest_configure(config):
    if config.getoption("--agh"):
        plugin = AghPtPlugin(config)
        config.pluginmanager.register(plugin, name="agh_plugin")
        config.addinivalue_line("markers", "build: This marks anything related to building a submission's exe.")
        config.addinivalue_line("markers", "render: This marks anything related to rendering a submission's documentation.")


@pytest.fixture
def agh_submission(request):
    return Submission.load(request.path.parent)


@pytest.fixture
def agh_assignment(request):
    print(request.path)
    return Assignment.load(request.path.parent)


@pytest.fixture
def resultsDir(agh_submission) -> Path:
    ret_val = agh_submission.evaluation_directory / "results"
    ret_val.mkdir(parents=True, exist_ok=True)
    return ret_val


def register_render_env_var(env_var_name: str, env_var_value, cache: pytest.Cache):
    env_vars = cache.get("agh_render_env_vars", set())
    env_vars.add(env_var_name)
    cache.set("agh_render_env_vars", list(env_vars))
    cache.set(env_var_name, env_var_value)


def storeRunOutErr(tgt_name: str, res, resultsDir):
    stdout_file = resultsDir / f"{tgt_name}.stdout"
    stdout_file.write_text(res.stdout)
    stderr_file = resultsDir / f"{tgt_name}.stderr"
    stderr_file.write_text(res.stderr)


evaluationDataOS = OutputSectionData(path=Path("eval_data_section.md"), title="Evaluation Data", heading_level=1)
instructor_out_data = OutputSectionData(path=Path("instructor_data_section.md"), title="Instructor Data", heading_level=1)


def _make_sections(resultsDir: Path, agh_assignment: Assignment, agh_submission: Submission):
    global evaluationDataOS, instructor_out_data

    orig_cwd = Path.cwd()
    os.chdir(agh_submission.evaluation_directory)
    try:
        yourCodeOS = OutputSectionData(path=Path("code_section.md"), title="Your Code", heading_level=1)

        instructor_out_data.path = resultsDir / instructor_out_data.path.name
        instructor_out_data.path.write_text(instructor_out_data.asQmdSection())

        # todo: handle loading from file.
        # for cur_section in [evaluationDataOS, yourCodeOS, instructor_out_data]:
        #     if not cur_section.hasData:
        #         # Try loading it from the filesystem.
        #         cur_section.path = resultsDir / (cur_section.path.with_suffix('.json'))
        #         if cur_section.path.exists():

        evalOut = resultsDir / evaluationDataOS.path
        evalOut.write_text(evaluationDataOS.asQmdSection())

        codeOut = resultsDir / yourCodeOS.path
        for s_file in agh_assignment.required_files.values():
            if s_file.include_in_output:
                tgt = agh_submission.as_submitted_dir.absolute() / s_file.path.name

                # Create a submission file that points to my submission.
                my_sub_src_file = SubmissionFileData(**s_file.asdict())
                my_sub_src_file.path = tgt.relative_to(agh_submission.evaluation_directory)
                tgt = agh_submission.evaluation_directory / my_sub_src_file.path
                if not tgt.exists():
                    tgt.touch()
                yourCodeOS.included_files.append(my_sub_src_file)
        codeOut.write_text(yourCodeOS.asQmdSection())
    finally:
        os.chdir(orig_cwd)


@pytest.fixture
def agh_build_makefile(agh_submission, shell, cache, request, resultsDir) -> Callable[[str], str]:
    request.applymarker(pytest.mark.build)

    def build(target: str | None = None, include_build_in_eval: bool = True):
        # Check to see if this is the first time we're building this submission.
        first_build = False
        if agh_submission.getMetadata(TEST_MD_KEY, "initial_build_success", default=None) is None:
            first_build = True
            agh_submission.setMetadata(TEST_MD_KEY, "initial_build_success", value=False)

        # Build the submission.
        cmd = ["make"]
        if target is not None:
            cmd.append(target)
        res = shell.run(*cmd, shell=True, cwd=agh_submission.evaluation_directory, env={"AGH_BUILD_TESTING": "1"})

        # Update permanent cache state for initial build ok.
        if first_build:
            agh_submission.setMetadata(TEST_MD_KEY, "initial_build_success", value=res.returncode == 0)

        build_out_section = OutputSectionData(path=Path("build_data.md"), title="Build Output")
        if include_build_in_eval:
            evaluationDataOS.addSection(build_out_section)
        stdout_file = resultsDir / f"{target if target else ''}build.stdout"
        stdout_file.parent.mkdir(exist_ok=True)
        stdout_file.write_text(res.stdout)
        build_out_section.included_files.append(
            SubmissionFileData(path=stdout_file.relative_to(agh_submission.evaluation_directory), title="Build Stdout Output")
        )
        stderr_file = resultsDir / f"{target if target else ''}build.stderr"
        stderr_file.write_text(res.stderr)
        if len(res.stderr) > 0:
            build_out_section.included_files.append(
                SubmissionFileData(path=stdout_file.relative_to(agh_submission.evaluation_directory), title="Build Stderr Output")
            )

        return res

    return build


@pytest.fixture
def _core_file_saved(agh_submission):
    core_path = Path("/proc/sys/kernel/core_pattern")
    path_good = core_path.exists() and "apport" not in core_path.read_text().strip()
    if path_good:
        agh_submission.delWarning("core_file_saved")
    else:
        agh_submission.addWarning("core_file_saved", "Core file pattern will not allow debugging information to be captured.")
    return path_good


@pytest.fixture
def agh_run_executable(
    agh_submission, shell: ScriptSubprocess, resultsDir, _core_file_saved
) -> Callable[..., tuple[ProcessResult, OutputSectionData]]:
    def run_executable(
        command: str,
        test_key: str,
        test_exe_file: Path,
        timeout_sec: int = 25,
        kill_timeout_sec: int = 50,
        parent_section: OutputSectionData | None = None,
        handle_core_dump: bool = True,
        handle_timeout: bool = True,
        **kwargs,
    ) -> tuple[ProcessResult, OutputSectionData]:
        """Run an executable and return the results.
        .. important::

            You must finish setting up the returned output section with a title etc.
        """

        # Build up the shell command line based on options selected by the grader.
        shell_cmd_line = command
        if handle_timeout:
            shell_cmd_line = f"timeout -vk {kill_timeout_sec} -s SIGXCPU {timeout_sec} " + shell_cmd_line
        if handle_core_dump:
            shell_cmd_line = "ulimit -c unlimited && " + shell_cmd_line

        # Clear any old core files.
        for core_file in agh_submission.evaluation_directory.glob(f"{CORE_DUMP_FILE_NAME}.*"):
            core_file.unlink()

        if "stdin" in kwargs.keys() and kwargs["stdin"] is not None and isinstance(kwargs["stdin"], str):
            shell_cmd_line = f"bash -c 'echo -e \"{kwargs['stdin']}\" | {shell_cmd_line}'"

        result = shell.run(shell_cmd_line, shell=True, cwd=agh_submission.evaluation_directory, **kwargs)

        if parent_section is None:
            parent_section = evaluationDataOS

        current_out_section = OutputSectionData(path=Path(resultsDir / f"{test_key}_section.md"))
        parent_section.addSection(current_out_section)

        std_out_file = resultsDir / f"{test_key}.stdout"
        current_out_section.included_files.append(
            SubmissionFileData(
                path=std_out_file.relative_to(agh_submission.evaluation_directory),
                title="Standard Output",
                description="This is the standard output from running your code.",
                type="default",
            )
        )
        std_out_file.parent.mkdir(exist_ok=True)
        std_out_file.write_text(result.stdout, encoding="ascii", errors="backslashreplace")

        if len(result.stderr) > 0:
            std_err_file = resultsDir / f"{test_key}.stderr"
            current_out_section.included_files.append(
                SubmissionFileData(
                    path=std_err_file.relative_to(agh_submission.evaluation_directory),
                    title="Standard Error",
                    description="This is the standard error from running your code.",
                    type="default",
                )
            )
            std_err_file.write_text(result.stderr, encoding="ascii", errors="backslashreplace")

        # Handle core dumps. We now in ubuntu need to search for CORE_DUMP_FILE_NAME.pid.
        # core_dump_file = agh_submission.evaluation_directory / CORE_DUMP_FILE_NAME
        agh_submission.delWarning("crash_detected")
        agh_submission.delError("crash_detection_issue")

        core_dump_files = [*agh_submission.evaluation_directory.glob(f"{CORE_DUMP_FILE_NAME}.*")]
        core_dump_file = core_dump_files[0] if len(core_dump_files) > 0 else None
        if core_dump_file and core_dump_file.exists():
            agh_submission.addWarning(
                "crash_detected", 'The submission crashed. Check the "Backtrace from Debug" section for more details.'
            )
            # Run gdb on the core dump

            debug_output_file = resultsDir / (test_key + ".backtrace")
            result_debug = shell.run(
                f'gdb -q {test_exe_file} {core_dump_file.name} --ex "thread apply all bt full" --batch > {debug_output_file} 2>&1',
                shell=True,
                cwd=agh_submission.evaluation_directory,
            )
            core_dump_file.unlink()

            if result_debug.returncode != 0:
                agh_submission.addError("crash_detection_issue", "**ERROR:** gdb failed to run on the core dump!")

            if debug_output_file.exists() and debug_output_file.stat().st_size > 0:
                # There is data add to the eval section.
                # debug_output_file.write_text(result_debug.stdout)
                # debug_output_file.write_text(result_debug.stderr, encoding="ascii", errors="backslashreplace")
                current_out_section.included_files.append(
                    SubmissionFileData(
                        path=debug_output_file.relative_to(agh_submission.evaluation_directory),
                        title="Backtrace from Debug",
                        type="default",
                        description="Your code had an error that caused it to crash. This is the debugging backtrace from that crash.",
                    )
                )
            else:
                # todo: Handle this better.
                agh_submission.addError(
                    "crash_detection_issue", "**Warning:** no backtrace data available from core file!\n" + str(result_debug.cmdline)
                )

        err_code = result.returncode
        if err_code:
            # current_out_section.text += f"\n\n**Warning:** Exe exited with error code: {err_code}!"
            if 124 <= err_code <= 128:
                current_out_section.addWarning("Timeout", f"Your executable took too long to run and had to be terminated: {err_code}!")
            elif err_code > 128:
                sig_name = ""
                try:
                    sig_name = signal.strsignal(err_code - 128)
                except ValueError:
                    pass

                agh_submission.setMetadata(TEST_MD_KEY, "EXE_FAULT", value=True)
                current_out_section.addError(
                    "Crash Likely", f"Exit Code: {err_code}\n\nExe exited with signal {sig_name}: {err_code - 128}"
                )
            # if err_code == 23:  # Leak sanitizer exitcode.
            #     threadWarn = EvalFile(testStdOut.with_suffix('.md'), '', '', just_text=True, unlisted=unlisted)
            #     curEFiles.insert(0, threadWarn)
            #     threadWarn.file.write_text(
            #         f'\n\n::: {{.callout-important title="EXE Issue Detected"}}\n\n**Exit Code: {err_code}**\n\n| '
            #         f'{testStdErr.read_text().replace(str(cDir.absolute()), ".").replace("\n", "\n| ")}\n\n::>
            #         # with myWarnFile.open('a') as infoFile:
            #         #   infoFile.write(f'\n - [ ] Memory Checked.\n\n')
        return (result, current_out_section)

    return run_executable


# todo: This is a good idea, but I feel that I need to get it working straightforwardly first.
#
# class MetaSingleton(type):
#     _instances: ClassVar[dict] = {}
#
#     def __call__(cls, *args, **kwargs):
#         if cls not in cls._instances:
#             cls._instances[cls] = super(MetaSingleton, cls).__call__(*args, **kwargs)  # noqa:
#             UP008
#         return cls._instances[cls]
#
#
# class AdvShell(metaclass=MetaSingleton):
#     """This class is a singleton that manages the invocation of an executable. **It must be
#     subclassed.**
#
#     This class is designed to allow for testing independent preconditions/postconditions
#     on the execution of a command. By subclassing this class the executable is
#     invoked a single time, but the preconditions/postconditions can be tested against the
#     output independently of the executable.
#
#     .. topic:: Example
#
#         .. code-block:: python
#
#             class TestSimple(AdvShell):
#                 def __init__(self):
#                     self.results = self.run(...)
#
#                 def test_success(self):
#                     assert self.results.returncode == 0, "Your executable exited with a
#                     non-zero return code."
#
#                 def test_out_length(self):
#                     assert len(self.results.stdout) > 10, "Your executable did not capture
#                     enough of the test data."
#
#                 def test_err_length(self):
#                     assert len(self.results.stderr) < 2, "Your executable was not clean in
#                     stderr."
#
#                 ...
#
#             class TestBadCLI(AdvShell):
#                 def __init__(self):
#                     self.results = self.run(<bad input>)
#
#                 def test_returncode(self):
#                     assert self.results.returncode != 0, "Your executable did not fail with a
#                     non-zero return code."
#
#                 def test_err_length(self):
#                     assert len(self.results.stderr) > 0, "Your executable did not output any
#                     error messages."
#
#                 def test_out_length(self):
#                     assert len(self.results.stdout) == 0, "Your executable may have printed the
#                     help message to stdout instead of stderr."
#                 ...
#
#
#         For each of the classes above, the self.run would only be invoked once each.
#         The tests would be run against the results of the single invocation but allow the
#         instructor
#         to indicate multiple issues within that invocation in a **pytest** appropriate manner.
#
#         .. warning::
#             THIS CLASS SHOULD NOT BE INSTANTIATED DIRECTLY, subclass it instead.
#
#     """
#
#     def __init__(self):
#         if type(self) is AdvShell:
#             raise TypeError("AdvShell class cannot be instantiated directly")
#
#     def run(self, *args, **kwargs):
#         """This method runs all the checks for the executable: Error code != 0, OS captured
#         faults, -fsanitize=leak errors, -fsanitize=thread errors."""

"""
INPUT
    command string

OUTPUT
    command is run once each test class
    output of one run is available in each function

"""


@pytest.fixture
def agh_render_output(
    agh_submission: Submission,
    shell,
    request: pytest.FixtureRequest,
    resultsDir: Path,
    agh_assignment: Assignment,
):
    request.applymarker(pytest.mark.render)

    def render(target: str | None = agh_assignment._options.output_template_name, *args: str):
        _make_sections(resultsDir, agh_assignment, agh_submission)
        cmd = ["quarto", "render"]
        if target is not None:
            cmd.append(target)
        if len(args) > 0:
            cmd.extend(args)

        # Clear all render specific errors and warnings
        agh_submission.delWarning("render warning").delError("render error").delWarning("render issue").save()

        try:
            cmd_str = " ".join(cmd)
            print(f"Executing quarto: {cmd_str}")
            res = shell.run(cmd_str, shell=True, cwd=agh_submission.evaluation_directory)
            (resultsDir / ".render.stdout.txt").write_text(f"{cmd_str}\n" + res.stdout)
            (resultsDir / ".render.stderr.txt").write_text(res.stderr)
            if res.returncode != 0:
                agh_submission.addWarning("render issue", f"Render '{cmd_str}' failed with return code {res.returncode}.").save()
                raise RuntimeError(f"quarto failed with return code {res.returncode}")
            agh_assignment.postProcessSubmissionRender(
                agh_submission, warning_callback=lambda warn: agh_submission.addWarning("render warning", warn)
            ).save()
            return res
        except Exception as e:
            agh_submission.addError("render error", f"Quarto failed with error {e}.").save()
            request.raiseerror(f"Error rendering {agh_submission.submission_file}: {e}")

    return render
