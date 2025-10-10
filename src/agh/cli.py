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
import datetime
import functools
import sys
from pathlib import Path

import argcomplete
from rich_argparse import RichHelpFormatter

from agh import Assignment
from agh import Submission
from agh import __version__
from agh import main_console
from agh.agh_data import GraderOptions

console = main_console
print = console.print

cur_date = datetime.datetime.now(tz=datetime.timezone.utc)
cur_date = cur_date.astimezone()

all_sub_parsers = []


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
            np = ret_val.original_add_parser(*args, **kwargs)
            all_sub_parsers.append(np)
            return np

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
        for cur_sub_parser in all_sub_parsers:
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


# console.log(SubFileCompleter("unprocessed_dir", ''))

parser = MyArgParser(
    description="agh --- Assignment Grading Helper", prog="agh", formatter_class=RichHelpFormatter, conflict_handler="resolve"
)
parser.add_argument("--version", action="version", version=__version__)
parser.add_argument("-H", "--full-help", action=FullHelp, help="Show full (all options) help")

subparsers = parser.add_subparsers(dest="command", help="Assignment/Submission/etc. commands")

# Status command (default)
status_parser = subparsers.add_parser("status", help="Show status of all elements of the assignment.")

assignment_sub_parser = subparsers.add_parser("assignment", help="Assignment commands", formatter_class=RichHelpFormatter)
assignment_subparsers = assignment_sub_parser.add_subparsers(dest="assignment_command", help="Assignment commands")

# assignment > new assignment command
assignment_new_parser = assignment_subparsers.add_parser("new", help="Create new assignment", formatter_class=RichHelpFormatter)
assignment_new_parser.add_argument("name", help="Assignment name", type=str).completer = lambda **kwargs: [f"Assignment {Path.cwd().name}"]
assignment_new_parser.add_argument("course", help="Course code", type=str).completer = lambda **kwargs: [f"CSCI-{Path.cwd().parent.name}"]
assignment_new_parser.add_argument("term", help="Term", choices=["Fall", "Spring", "Maymester", "Summer I", "Summer II"], type=str)
assignment_new_parser.add_argument("-y", "--year", help="Year", type=int, default=cur_date.year)
assignment_new_parser.add_argument("-a", "--anon", help="Anonymize names", action=argparse.BooleanOptionalAction, default=True)

# assignment > info command
assignment_info_parser = assignment_subparsers.add_parser("info", help="Show assignment info")
assignment_info_parser.add_argument("-d", "--details", action="store_true", help="Show debugging details.")

# Add required files command
assign_add_required_parser = assignment_subparsers.add_parser("add-required", help="Add required files")
assign_add_required_parser.add_argument("files", nargs="+", help="Required file names", type=Path)
assign_add_required_parser.add_argument("-d", "--description", help="Description of the required files", type=str, default="")
assign_add_required_parser.add_argument("-t", "--title", help="Title of the required files", type=str, default="")
assign_add_required_parser.add_argument(
    "-i", "--include-in-output", help="Include in output", action=argparse.BooleanOptionalAction, default=True
)

# Add optional files command
assign_add_optional_parser = assignment_subparsers.add_parser("add-optional", help="Add optional files")
assign_add_optional_parser.add_argument("files", nargs="+", help="Optional file names")
assign_add_optional_parser.add_argument("-d", "--description", help="Description of the optional files", type=str, default="")
assign_add_required_parser.add_argument("-t", "--title", help="Title of the optional files", type=str, default="")
assign_add_required_parser.add_argument(
    "-i", "--include-in-output", help="Include in output", action=argparse.BooleanOptionalAction, default=False
)

sub_subparser = subparsers.add_parser("submission", help="Submission commands", formatter_class=RichHelpFormatter)
sub_subparsers = sub_subparser.add_subparsers(dest="sub_command", help="Submission commands")

# submission > add command
sub_add_subparser = sub_subparsers.add_parser("add", help="Add a submission file.")
sub_add_subparser.add_argument("files", nargs="+", help="Submission files to add", type=Path).completer = functools.partial(
    SubFileCompleter, "unprocessed_dir"
)

# submission > fix command
sub_fix_subparser = sub_subparsers.add_parser(
    "fix", help="Fix a submission. Try this if you accidentally deleted something. This may re-create links etc."
)
sub_fix_subparser.add_argument("files", nargs="+", help="Submission files to add", type=str).completer = lambda **kwargs: [
    subm.evaluation_directory.name for subm in get_current_assignment().Submissions
]


argcomplete.autocomplete(parser)


def display_assignment_info(cli_args: argparse.Namespace):
    assignment = Assignment.load()
    console.print(f'[bold green]Assignment "{assignment.name}"')
    console.print(
        f"[bold green]Course:[/] {assignment.course}, [bold green]Term:[/] "
        f"{assignment._grade_period}, [bold green]Year:[/] {assignment.year}"
    )
    submissions = list(assignment.Submissions)
    console.print(f"[bold green]Submissions:[/] {len(submissions)}")
    if cli_args.details:
        console.log(assignment, submissions)


def get_current_assignment() -> Assignment:
    try:
        ret_val = Assignment.load()
        return ret_val
    except FileNotFoundError:
        console.print("[error]No assignment found.")
        sys.exit(1)


def run(args=None):
    """Entry point for console_scripts"""
    if args is None:
        args = sys.argv[1:]
        if len(args) == 0:
            args = ["-H"]
    cli_args = parser.parse_args(args=args)
    console.rule(f"[b i]agh[/] - Assignment Grading Helper - Version: [b i]{__version__}")
    # console.print(f'[purple bold underline]agh[/] version [white]{__version__}')
    match cli_args.command:
        case "assignment":
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
                        new_assignment = Assignment(
                            _name=cli_args.name,
                            _course=cli_args.course,
                            _grade_period=cli_args.term,
                            _year=cli_args.year,
                            _options=GraderOptions(anonymize_names=cli_args.anon),
                        )
                        console.print(f"[bold green]saving {new_assignment.name}.")
                        new_assignment.save()
                        console.print("[bold green]Creating directories.")
                        new_assignment.createMissingDirectories()
                        console.print(f'[bold green]Assignment "{new_assignment.name}" created successfully.')
                case "info":
                    display_assignment_info(cli_args)
                case _:
                    console.log(cli_args)
        case "submission":
            match cli_args.sub_command:
                case "add":
                    with console.status(f"Adding submission{'s' if len(cli_args.files) > 1 else ''}...", spinner="dots"):
                        console.print("Loading assignment.")
                        assignment = get_current_assignment()
                        console.print(f"Adding {len(cli_args.files)} submissions.")
                        for cur_file in cli_args.files:
                            console.print(f"Adding {cur_file}")
                            assignment.AddSubmission(cur_file).save()
                case "fix":
                    with console.status("Fixing submissions...", spinner="dots"):
                        console.print("Loading assignment.")
                        assignment = get_current_assignment()
                        console.print(f"Fixing {len(cli_args.files)} submissions.")
                        for cur_file in cli_args.files:
                            console.print(f"Fixing {cur_file}")
                            cur_subm_dir = assignment.eval_dir / cur_file
                            if not cur_subm_dir.exists():
                                console.print(f"[error]No submission directory found for {cur_file}.")
                            cur_subm = Submission.load(cur_subm_dir)
                            cur_subm.fix(assignment=assignment)
                            assignment.PostProcessSubmission(cur_subm).save()

        case _:
            console.log(cli_args)
    # print(start(args))
    parser.exit(0)
