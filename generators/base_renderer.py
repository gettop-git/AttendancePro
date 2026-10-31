from abc import ABC, abstractmethod
from pathlib import Path
import logging
from domain.models import AttendanceReport
from domain.exceptions import AttendanceSystemError

# Logger setup for the base renderer module
logger = logging.getLogger(__name__)


class BaseRenderer(ABC):
    """
    Abstract base class for all renderers (Generation layer).
    Defines the contract for converting an AttendanceReport into a specific output file format,
    incorporating structured logging and error handling.
    """

    @abstractmethod
    def render(self, report: AttendanceReport, output_path: str) -> None:
        """
        Renders the given AttendanceReport into a file at the specified output path.
        Must be implemented by concrete subclasses.
        """
        pass