from abc import ABC, abstractmethod
from domain.models import AttendanceReport
from config import config as app_config  # Import the global configuration under an alias
import logging

# Setup a central logger for the base class and strategies
logger = logging.getLogger(__name__)


class BaseTransformationStrategy(ABC):
    """
    Abstract base class for transformation strategies.
    Defines the contract for transforming attendance rows and summary deterministically,
    and provides shared access to centralized configuration settings for all subclasses.
    """

    def __init__(self, config=None) -> None:
        """
        Initializes the strategy with either an injected configuration (e.g., for testing)
        or the default application configuration manager.
        """
        self.config = config if config is not None else app_config
        logger.debug(f"Initialized {self.__class__.__name__} with configuration.")

    @abstractmethod
    def transform(self, report: AttendanceReport) -> AttendanceReport:
        """
        Takes an existing AttendanceReport and returns a new transformed AttendanceReport.
        Original report and rows remain unchanged (immutability).
        """
        pass