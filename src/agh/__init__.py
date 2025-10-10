from rich import console

from .agh_data import Assignment
from .agh_data import OutputSectionData
from .agh_data import Submission
from .agh_data import SubmissionFileData
from .core import start

__version__ = "0.2.5"

main_console: console.Console = console.Console()

__all__ = ["Assignment", "OutputSectionData", "Submission", "SubmissionFileData", "__version__", "start"]
