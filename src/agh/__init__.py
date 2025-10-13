from rich import console
from rich.theme import Theme

from .agh_data import Assignment
from .agh_data import OutputSectionData
from .agh_data import Submission
from .agh_data import SubmissionFileData
from .core import start

__version__ = "0.2.5"

default_theme = Theme({"info": "b cyan", "warning": "b r yellow", "danger": "bold r red"})
main_console: console.Console = console.Console(theme=default_theme)

__all__ = ["Assignment", "OutputSectionData", "Submission", "SubmissionFileData", "__version__", "start"]
