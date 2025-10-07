from .agh_data import Assignment
from .agh_data import Submission
from .core import start

__version__ = "0.2.4"

from .agh_data import Assignment, Submission, SubmissionFileData, OutputSectionData

__all__ = [
    "__version__",
    "Assignment",
    "Submission",
    "SubmissionFileData",
    "OutputSectionData",
]
