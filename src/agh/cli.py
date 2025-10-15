# PYTHON_ARGCOMPLETE_OK
"""
Module that contains the command line app.

Why does this file exist, and why not put this in __main__?

  You might be tempted to import things from __main__ later, but that will cause
  problems: the code will get executed twice:

  - When you run `python -magh` python will execute
    ``__main__.py`` as a script. That means there will not be any
    ``agh.__main__`` in ``sys.modules``.
  - When you import __main__ it will get executed again (as a module) because
    there"s no ``agh.__main__`` in ``sys.modules``.

  Also see (1) from http://click.pocoo.org/5/setuptools/#setuptools-integration
"""

import argparse
import asyncio
import datetime
import functools
import re
import sys
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from urllib import parse

import argcomplete
import rich.progress
import rich.table
from rich.markdown import Markdown
from rich_argparse import RichHelpFormatter

from agh import Assignment
from agh import Submission
from agh import __version__
from agh import main_console
from agh.agh_data import DataclassJson
from agh.agh_data import GraderOptions
from agh.agh_data import SubmissionFileData

META_KEY_RUN_OUTPUT = "Execution output"

console = main_console
print = console.print

cur_date = datetime.datetime.now(tz=datetime.timezone.utc)
cur_date = cur_date.astimezone()

all_sub_parsers: list[tuple[str, argparse.ArgumentParser]] = []


class MyArgParser(argparse.ArgumentParser):
    __doc__ = argparse.ArgumentParser.__doc__

    # This class makes it so that subparsers are added to a global list.
    # This is necessary because we need to add the subparsers to the help text.
    # It also adds a formatter_class to the subparsers.

    @functools.wraps(argparse.ArgumentParser.add_subparsers)
    def add_subparsers(self, *args, **kwargs):
        ret_val = super().add_subparsers(*args, **kwargs)
        ret_val.original_add_parser = ret_val.add_parser

        @functools.wraps(ret_val.add_parser)
        def new_add_parser(*args, **kwargs):
            global all_sub_parsers
            if "formatter_class" not in kwargs:
                kwargs["formatter_class"] = RichHelpFormatter
            if "conflict_handler" not in kwargs:
                kwargs["conflict_handler"] = "resolve"
            new_parser = ret_val.original_add_parser(*args, **kwargs)
            all_sub_parsers.append((args[0], new_parser))
            return new_parser

        ret_val.add_parser = new_add_parser
        return ret_val


class FullHelp(argparse.Action):
    """This is a argparse action that prints the full help text."""

    def __init__(self, option_strings, dest=argparse.SUPPRESS, default=argparse.SUPPRESS, help=None, nargs=0, **kwargs):
        if nargs != 0:
            raise ValueError("nargs not allowed")
        super().__init__(option_strings, dest=dest, nargs=nargs, default=default, help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        parser.print_help()
        for name, cur_sub_parser in all_sub_parsers:
            # console.print(Panel(cur_sub_parser.format_help(),title=f"[bold]Subcommand: {name}", expand=False,
            # style="b", ))
            console.rule(('>' * 5) + f"  [b red]{name}[/] ", align='left')
            cur_sub_parser.print_help()
        parser.exit(0)


def SubFileCompleter(property: str, prefix: str, **kwargs):
    try:
        assignment = Assignment.load()
        directory: Path = getattr(assignment, property)
        cur_dir = Path.cwd()
        if not directory.exists():
            argcomplete.warn("No submission directory found. Cannot complete submission files.")
        ret_val = [
            str(glob_item)
            for glob_item in directory.relative_to(cur_dir, walk_up=True).glob("*", case_sensitive=False)
            if glob_item.is_file()
        ]
        # with console.capture() as capture:
        #     console.print(f"[bold green]Found {len(ret_val)} files in {directory}.")
        #     console.log(property, prefix, ret_val)
        # (cur_dir/'autocomplete_test.txt').write_text(capture.get())
        return ret_val
    except FileNotFoundError:
        argcomplete.warn("No assignment found. Cannot complete submission files.")


def submissionCompleter(*args, **kwargs):
    # return ['Bob','Tom']
    try:
        ret_val = [str(subm.evaluation_directory.resolve().relative_to(Path.cwd(), walk_up=True)) for subm in
                   Assignment.load().Submissions]
        return ret_val
    except Exception as e:
        argcomplete.warn("No assignment found. Cannot complete submission files.")
        argcomplete.warn(e)
        return ["Bob"]


# console.log(SubFileCompleter("unprocessed_dir", ''))

parser = MyArgParser(
    description="agh --- Assignment Grading Helper", prog="agh", formatter_class=RichHelpFormatter,
    conflict_handler="resolve"
)
parser.add_argument("--version", action="version", version=__version__)
parser.add_argument("-H", "--full-help", action=FullHelp, help="Show full (all options) help")

subparsers = parser.add_subparsers(dest="command", help="Assignment/Submission/etc. commands")

################################################################################
################################################################################
# Status command (default)
################################################################################
################################################################################
status_parser = subparsers.add_parser("status", help="Show status of all elements of the assignment.")
status_parser.add_argument("-d", "--details", action="store_true", help="Show debugging details.", default=False)

################################################################################
################################################################################
# Assignment command
################################################################################
################################################################################

assignment_sub_parser = subparsers.add_parser("assignment", help="Assignment commands",
                                              formatter_class=RichHelpFormatter)
assignment_subparsers = assignment_sub_parser.add_subparsers(dest="assignment_command", help="Assignment commands")

# assignment > new assignment command
assignment_new_parser = assignment_subparsers.add_parser("new", help="Create new assignment",
                                                         formatter_class=RichHelpFormatter)
assignment_new_parser.add_argument("name", help="Assignment name", type=str).completer = lambda **kwargs: [
    f"Assignment {Path.cwd().name}"]
assignment_new_parser.add_argument("course", help="Course code", type=str).completer = lambda **kwargs: [
    f"CSCI-{Path.cwd().parent.name}"]
assignment_new_parser.add_argument("term", help="Term",
                                   choices=["Fall", "Spring", "Maymester", "Summer I", "Summer II"], type=str)
assignment_new_parser.add_argument("-y", "--year", help="Year", type=int, default=cur_date.year)
assignment_new_parser.add_argument("-a", "--anon", help="Anonymize names", action=argparse.BooleanOptionalAction,
                                   default=True)

# assignment > info command
assignment_info_parser = assignment_subparsers.add_parser("info", help="Show assignment info")
assignment_info_parser.add_argument("-d", "--details", action="store_true", help="Show debugging details.")

# Add required files command
assign_add_required_parser = assignment_subparsers.add_parser("add-required", help="Add required files")
assign_add_required_parser.add_argument("files", nargs="+", help="Required file names", type=Path)
assign_add_required_parser.add_argument("type", help="Type of the required file", type=str).completer = lambda \
        **kwargs: [
    "txt",
    "py",
    "c",
    "cpp",
    "java",
    "default",
    "make",
]
assign_add_required_parser.add_argument("-d", "--description", help="Description of the required files", type=str,
                                        default="")
assign_add_required_parser.add_argument("-t", "--title", help="Title of the required files", type=str, default="")
assign_add_required_parser.add_argument(
    "-i", "--include-in-output", help="Include in output", action=argparse.BooleanOptionalAction, default=True
)

# Add optional files command
assign_add_optional_parser = assignment_subparsers.add_parser("add-optional", help="Add optional files")
assign_add_optional_parser.add_argument("files", nargs="+", help="Optional file names")
assign_add_optional_parser.add_argument("type", help="Type of the required file", type=str).completer = lambda \
        **kwargs: [
    "txt",
    "py",
    "c",
    "cpp",
    "java",
    "make",
    "default",
]
assign_add_optional_parser.add_argument("-d", "--description", help="Description of the optional files", type=str,
                                        default="")
assign_add_optional_parser.add_argument("-t", "--title", help="Title of the optional files", type=str, default="")
assign_add_optional_parser.add_argument(
    "-i", "--include-in-output", help="Include in output", action=argparse.BooleanOptionalAction, default=True
)

################################################################################
################################################################################
# Submission command
################################################################################
################################################################################
sub_subparser = subparsers.add_parser("submission", help="Submission commands", formatter_class=RichHelpFormatter)
sub_subparsers = sub_subparser.add_subparsers(dest="sub_command", help="Submission commands")

# submission > add command
sub_add_subparser = sub_subparsers.add_parser("add", help="Add a submission file.")
sub_add_subparser.add_argument("files", nargs="+", help="Submission files to add",
                               type=Path).completer = functools.partial(
    SubFileCompleter, "unprocessed_dir"
)
sub_add_subparser.add_argument("-a", "--anonymous", dest="override_anon", action="store_true",
                               help="Override the assignment default and make this submission anonymous.",
                               default=None)
sub_add_subparser.add_argument("-n", "--non-anonymous", dest="override_anon", action="store_false",
                               help="Override the assignment default and make this submission non-anonymous.",
                               default=None)

# submission > fix command
sub_fix_subparser = sub_subparsers.add_parser(
    "fix", help="Fix a submission. Try this if you accidentally deleted something. This may re-create links etc."
)
sub_fix_subparser.add_argument("submissions", nargs="+", help="Submissions to fix",
                               type=str).completer = submissionCompleter

################################################################################
################################################################################
# ETC
################################################################################
################################################################################
# Add run command
run_parser = subparsers.add_parser("run", help="Run submission files. This executes build, test, and render.")
run_parser.add_argument(
    "-s", "--submission", dest="submissions", nargs="+", help="Submissions to run (build, test, render).", type=Path,
    default=None
).completer = submissionCompleter
run_parser.add_argument("-v", "--verbose", dest="verbose", action="store_true", help="Verbose output.", default=False)

# Add test command
test_parser = subparsers.add_parser("test",
                                    help="Test submission files. This just runs the tests for the given submissions.")
test_parser.add_argument(
    "-s", "--submission", dest="submissions", nargs="+", help="Submissions to run (build, test, render).", type=Path,
    default=None
).completer = submissionCompleter
test_parser.add_argument("-v", "--verbose", dest="verbose", action="store_true", help="Verbose output.", default=False)

# Add build command
build_parser = subparsers.add_parser("build", help="Build submission files")
build_parser.add_argument(
    "-s", "--submission", dest="submissions", nargs="+", help="Submissions to run (build, test, render).", type=Path,
    default=None
).completer = submissionCompleter
build_parser.add_argument("-v", "--verbose", dest="verbose", action="store_true", help="Verbose output.", default=False)

# Add render command
render_parser = subparsers.add_parser("render", help="Render submission files")
render_parser.add_argument(
    "-s", "--submission", dest="submissions", nargs="+", help="Submissions to run (build, test, render).", type=Path,
    default=None
).completer = submissionCompleter
render_parser.add_argument("-v", "--verbose", dest="verbose", action="store_true", help="Verbose output.",
                           default=False)

argcomplete.autocomplete(parser)


def display_assignment_info(cli_args: argparse.Namespace):
    assignment = Assignment.load()
    console.print(f'[label]Assignment "{assignment.name}"')
    console.print(
        f"[label]Course:[/] {assignment.course}, [label]Term:[/] {assignment._grade_period}, [label]Year:[/] "
        f"{assignment.year}")
    submissions = list(assignment.Submissions)
    console.print(f"[label]Submissions:[/] {len(submissions)}")

    files_table = rich.table.Table(title="[label][req]Required[/req]/[opt]Optional[/opt] Files", expand=True,
                                   show_lines=True)
    files_table.add_column("Link", justify="center")
    files_table.add_column("Output", justify="center")
    files_table.add_column("Name", justify="left")
    files_table.add_column("Type", justify="center")
    files_table.add_column("Title", justify="left")
    files_table.add_column("Description", justify="left", overflow="fold")

    def add_submission_file(required_file: SubmissionFileData, style: str = ""):
        pth: Path = assignment.assignment_description_dir / required_file.path.name
        pth = pth.resolve()
        files_table.add_row(
            f"[link agh-edit:{parse.quote(str(pth))}] :notebook: [/]",
            ":white_check_mark:" if required_file.include_in_output else ":x:",
            f"[{style}]{required_file.path.name}",
            required_file.type,
            required_file.title,
            Markdown(required_file.description),
        )

    for required_file in assignment.required_files.values():
        add_submission_file(required_file, "req")
    for optional_file in assignment.optional_files.values():
        add_submission_file(optional_file, "opt")

    console.print(files_table)

    if cli_args.details:
        console.log(assignment, submissions)


def display_submission_info(cli_args: argparse.Namespace, assignment: Assignment):
    # todo: "[error] Add links to the editable output files."
    console.print("[error] Add links to the editable output files.")
    console.rule("[bold dark_green]Submission Info")
    submission_table = rich.table.Table(title="Submissions")
    submission_table.add_column("Err", justify="center")
    submission_table.add_column("Warn", justify="center")
    submission_table.add_column("Output", justify="center")
    submission_table.add_column("Name", justify="left")

    for submission in assignment.Submissions:
        warnings = submission.warnings
        has_warnings = warnings is not None and len(warnings) > 0
        if warnings:
            warning_str = "\n".join(warnings)
            warnings = f"[link {parse.quote(warning_str)}] :exclamation: [/]"
        else:
            warnings = ":thumbsup:"

        errors = submission.errors
        has_errors = errors is not None and len(errors) > 0
        if errors:
            errors_str = "\n".join(errors)
            errors = f"[link {parse.quote(errors_str)}] :x: [/]"
        else:
            errors = ":+1:"

        output = submission.main_output_file
        has_output = output is not None
        if output:
            output = f"[link file://{output}] :notebook: [/]"
        else:
            output = ":-1:"

        sub_color = "green"
        match (has_errors, has_warnings, has_output):
            case (True, _, _):
                sub_color = "red"
            case (False, True, _):
                sub_color = "orange"
            case (False, False, False):
                sub_color = "yellow"
            case (False, False, True):
                sub_color = "green"
        submission_table.add_row(errors, warnings, output, f"[bold {sub_color}] {submission.name} [/]")

    console.print(submission_table)


def get_current_assignment() -> Assignment:
    try:
        ret_val = Assignment.load()
        return ret_val
    except FileNotFoundError:
        console.print("[error]No assignment found.")
        sys.exit(1)


def handleAssignmentCmd(cli_args: argparse.Namespace):
    match cli_args.assignment_command:
        case "new":
            try:
                if Assignment.load(None) is not None or (Path.cwd() / "src" / "agh").exists():
                    print(f'[error]Assignment "{cli_args.name}" already exists.')
                    sys.exit(1)
            except FileNotFoundError:
                pass
            with console.status("Creating assignment", spinner="dots"):
                console.print(f'[bold green]Creating assignment "{cli_args.name}"')
                new_assignment = Assignment(_name=cli_args.name, _course=cli_args.course, _grade_period=cli_args.term,
                                            _year=cli_args.year, _options=GraderOptions(anonymize_names=cli_args.anon))
                console.print(f"[bold green]saving {new_assignment.name}.")
                new_assignment.save()
                console.print("[bold green]Creating directories.")
                new_assignment.createMissingDirectories()
                console.print(f'[bold green]Assignment "{new_assignment.name}" created successfully.')
        case "info":
            display_assignment_info(cli_args)
        case "add-required" | "add-optional":
            assignment = get_current_assignment()
            if len(cli_args.files) > 1 and (len(cli_args.title) or len(cli_args.description)):
                console.log("[error]Cannot specify a title or description when adding multiple files.")

            # So that the same code can be used for both add-required and add-optional
            #  (the only difference is the method used to add the file) curry the method to use.
            method = None
            if cli_args.assignment_command == "add-required":
                method = assignment.addRequiredFile
            else:
                method = assignment.addOptionalFile

            # For each file call the method curried from above.
            for cur_file in cli_args.files:
                method(SubmissionFileData(path=Path(cur_file), title=cli_args.title, description=cli_args.description,
                                          include_in_output=cli_args.include_in_output, type=cli_args.type))
                console.print(f"[bold green]Added file '{cur_file}'")
            assignment.save()
        case _:
            console.log(cli_args, style="error")


def handleSubmissionCmd(cli_args: argparse.Namespace):
    """Handle the submission command sub-command processing.
    This should be called when command is "submission".
    """
    match cli_args.sub_command:
        case "add":
            with console.status(f"Adding submission{'s' if len(cli_args.files) > 1 else ''}...", spinner="dots"):
                console.print("Loading assignment.")
                assignment = get_current_assignment()
                console.print(f"Adding {len(cli_args.files)} submissions.")
                # console.log(cli_args, style="error")
                for cur_file in cli_args.files:
                    console.print(f"Adding {cur_file}")
                    assignment.AddSubmission(cur_file, override_anon=cli_args.override_anon).save()
                assignment.save()
        case "fix":
            with console.status("Fixing submissions...", spinner="dots"):
                console.print("Loading assignment.")
                assignment = get_current_assignment()
                console.print(f"Fixing {len(cli_args.submissions)} submissions.")
                for cur_file in cli_args.submissions:
                    console.print(f"Fixing {cur_file}")
                    cur_subm_dir = assignment.eval_dir / cur_file
                    if not cur_subm_dir.exists():
                        console.print(f"[error]No submission directory found for {cur_file}.")
                    cur_subm = Submission.load(cur_subm_dir)
                    cur_subm.fix(assignment=assignment)
                    assignment.PostProcessSubmission(cur_subm).save()
        case _:
            console.log(cli_args, style="error")


@dataclass(kw_only=True)
class RunOutputInfo(DataclassJson):
    """Dataclass for storing the output of a run command."""

    output: list[str] | None = field(default_factory=list)
    error: list[str] | None = field(default_factory=list)
    collected: int | None = None
    return_code: int | None = None


async def parse_pytest_output(
    assignment: Assignment, submission: Submission, proc: asyncio.subprocess.Process, progress: rich.progress.Progress,
    task_id
):
    output_info = RunOutputInfo()

    async def error_collector():
        while True:
            error_line = await proc.stderr.readline()
            if not error_line:
                break
            error_line = error_line.decode().strip()
            output_info.error.append(error_line)

    err_coll_task = asyncio.create_task(error_collector(), name=f"{submission.name} error stream collector.")
    while True:
        line = await proc.stdout.readline()
        if not line:
            break
        line = line.decode().strip()
        output_info.output.append(line)
        if "collecting ..." in line:
            match = re.search(r"collected (\d+) items", line)
            if match:
                output_info.collected = int(match.group(1))
                progress.update(task_id, total=output_info.collected)
        elif " PASSED " in line or " FAILED " in line or " SKIPPED " in line:
            progress.update(task_id, advance=1)
        progress.update(task_id, description=line)
    await proc.wait()
    await err_coll_task

    output_info.return_code = proc.returncode

    # Set the metadata for this run in the assignment.
    assignment.setMetadata(META_KEY_RUN_OUTPUT, submission.name, value=output_info.asdict())
    assignment.save()
    return proc.returncode


async def run_pytest(
    assignment: Assignment, submission: Submission, progress: rich.progress.Progress, extra_pytest_args: str = ""
) -> tuple[Submission, bool]:
    """Run pytest on the given submission.

    :type assignment: Assignment
    :param assignment: The current assignment object.
    :param submission: The submission object that is being tested.
    :param progress: The progress bar object.
    :param extra_pytest_args: Extra pytest arguments to pass to pytest. Used for -m "not build and not render" etc.
    :return: A tuple containing the submission object and a boolean indicating whether the test was successful.
    :rtype: tuple[Submission, bool]
    """

    # The pytest command, when wanting to run on a specific directory or file, expects the path to the testing
    # directory.
    # This resolves that path relative to the submission directory.
    tests_path = submission.evaluation_directory / assignment.tests_dir.name
    if not tests_path.exists():
        task_id = progress.add_task("Testing...", total=1)
        progress.update(
            task_id,
            advance=1,
            completed=True,
            description=f"[error]Tests directory '{tests_path.absolute()}'not found. Perhaps run fix on "
                        f"{submission.name} first?",
        )
        return submission, False

    # Setup the progress bar.
    task_id = progress.add_task(f"Testing {tests_path.absolute()}...", total=None)

    # Run pytest.
    proc = await asyncio.create_subprocess_shell(
        f"pytest -v -p agh-pytest-plugin {extra_pytest_args} {tests_path.absolute()}/*",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    return_code = await parse_pytest_output(assignment, submission, proc, progress, task_id)
    return submission, return_code == 0


async def execute_pytest_on_submissions(cli_args: argparse.Namespace, assignment: Assignment,
                                        extra_pytest_args: str = ""):
    """This function asynchronously runs pytest on all submissions specified.

    It provides a progress bar for each submission to indicate the progress of the tests.

    :param cli_args: The command line arguments.
    :param assignment: The assignment object.
    :param extra_pytest_args: Extra pytest arguments to pass to pytest. Used for `-m "not build and not render"` etc.
    :return: None
    """
    # If there are no submissions specified, run on all submissions.
    if cli_args.submissions is None:
        cli_args.submissions = list(assignment.Submissions)
    else:
        # The CLI submissions provide the directory for the submission. We convert
        #  to the submission objects and report any that don't exist.
        submission_list = []
        for submission in cli_args.submissions:
            try:
                submission_list.append(Submission.load(submission))
            except FileNotFoundError:
                console.print(f"[error]No submission found for {submission}")
                continue
            except Exception as e:
                console.print(f"[error]Error loading submission {submission}: {e}")
                continue
        cli_args.submissions = submission_list

    if len(cli_args.submissions) == 0:
        console.print("[error]No submissions found.")
        return
    else:
        console.print(f"Running tests on {len(cli_args.submissions)} submissions.")

    with rich.progress.Progress(
        rich.progress.SpinnerColumn(spinner_name="dots"),
        *rich.progress.Progress.get_default_columns(),
        rich.progress.TimeRemainingColumn(),
    ) as progress:
        tasks = [run_pytest(assignment, submission, progress, extra_pytest_args=extra_pytest_args) for submission in
                 cli_args.submissions]
        results = await asyncio.gather(*tasks)

    for submission, success in results:
        if success:
            console.print(f"[green]Tests passed for {submission.name}[/green]")
        else:
            console.print(f"[red]Tests failed for {submission.name}[/red]")
            if cli_args.verbose:
                console.print("[bold label]Output:[/]")
                for line in assignment.getMetadata(META_KEY_RUN_OUTPUT, submission.name, "output", default=[]):
                    console.print(line)
                console.print("[bold label]Errors:[/]")
                err_lines = assignment.getMetadata(META_KEY_RUN_OUTPUT, submission.name, "error", default=[])
                if err_lines:
                    for line in err_lines:
                        console.print(line, style="error")


def run(args=None):
    """Entry point for console_scripts"""

    if args is None:
        args = sys.argv[1:]
        if len(args) == 0:
            args = ["status"]
    cli_args = parser.parse_args(args=args)
    console.rule(f"[b i]agh[/] - Assignment Grading Helper - Version: [b i]{__version__}")
    match cli_args.command:
        case "status":
            assignment = get_current_assignment()
            display_assignment_info(cli_args)
            display_submission_info(cli_args, assignment)
        case "assignment":
            handleAssignmentCmd(cli_args)
        case "submission":
            handleSubmissionCmd(cli_args)
        case "run":
            assignment = get_current_assignment()
            asyncio.run(execute_pytest_on_submissions(cli_args, assignment))
        case "test":
            assignment = get_current_assignment()
            asyncio.run(
                execute_pytest_on_submissions(cli_args, assignment, extra_pytest_args='-m "not build and not render"'))
        case "build":
            assignment = get_current_assignment()
            asyncio.run(execute_pytest_on_submissions(cli_args, assignment, extra_pytest_args='-m "build"'))
        case "render":
            assignment = get_current_assignment()
            asyncio.run(execute_pytest_on_submissions(cli_args, assignment, extra_pytest_args='-m "render"'))
        case _:
            console.log(cli_args, style="error")
    # print(start(args))
    parser.exit(0)

# todo: create custom url scheme so I can run things from links in the output.
#   To create a custom URL scheme in Ubuntu that executes a command in the terminal, you need to define a desktop
#   entry for the scheme and create a script to handle the URL.
#   1. Create a Handler Script:
#   First, create a script that will receive the custom URL and execute the desired command. For example,
#   let's create a script named my-custom-handler.sh in your home directory:
#   Code
#   >>>
#   #!/bin/bash
#   # Extract the command from the URL (e.g., mycommand://echo%20hello)
#   # Replace 'mycommand://' with your desired scheme
#   COMMAND=$(echo "$1" | sed 's/^mycommand:\/\///')
#   # Decode URL-encoded characters (e.g., %20 to space)
#   COMMAND=$(echo -e "$(echo "$COMMAND" | sed 's/+/ /g;s/%\(..\)/\\x\1/g')")
#   # Open a new terminal and execute the command
#   gnome-terminal -- bash -c "$COMMAND; exec bash"
#   # Or use xterm, konsole, etc., depending on your terminal emulator
#   # xterm -e "$COMMAND"
#   <<<
#   Make the script executable:
#   > chmod +x ~/my-custom-handler.sh
#   2. Create a Desktop Entry:
#   Next, create a .desktop file to define your custom URL scheme. Create a file named mycommand-handler.desktop in
#   ~/.local/share/applications/:
#   Code
#   >>>
#   [Desktop Entry]
#   Name=My Custom Command Handler
#   Exec=/home/your_username/my-custom-handler.sh %u
#   Terminal=false
#   Type=Application
#   MimeType=x-scheme-handler/mycommand;
#   Replace /home/your_username/my-custom-handler.sh with the actual path to your script.
#   3. Update MIME Types Database:
#   Update the system's MIME types database to recognize your new scheme:
#   Code
#   > sudo update-desktop-database
#   I THINK that you can just use `update-desktop-database` for user only change.
#   4. Test the Custom URL Scheme:
#   Now, you can test your custom URL scheme. Open your web browser or any application that supports opening URLs and
#   enter a URL like:
#   Code
#   >>>
#   mycommand://echo%20hello
#   This should launch a new terminal window and execute the echo hello command. You can replace echo%20hello with
#   any URL-encoded command you wish to run.
