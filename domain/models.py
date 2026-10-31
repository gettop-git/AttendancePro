from dataclasses import dataclass, field
from typing import List, Optional
import logging
from domain.exceptions import InvalidReportDataError

# Logger setup for the domain models module
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AttendanceRow:
    """
    Represents a single attendance row. Defined as frozen to ensure immutability,
    forcing the transformation process to generate new rows instead of mutating the original ones.
    Supports fields from both Type A and Type B formats.
    """
    date: Optional[str] = None
    day_of_week: Optional[str] = None
    location: Optional[str] = None  # Relevant for Type A
    clock_in: Optional[str] = None
    clock_out: Optional[str] = None
    break_duration: Optional[str] = None  # Relevant for Type A
    total_hours: float = 0.0

    # Overtime and specific hours (mainly Type A)
    overtime_100: float = 0.0
    overtime_125: float = 0.0
    overtime_150: float = 0.0
    saturday_hours: float = 0.0

    # Specific fields for Type B or general flags
    notes: Optional[str] = None  # Relevant for Type B
    is_missing_punch: bool = False
    is_overtime_hazard: bool = False

    def __post_init__(self) -> None:
        """
        Validates row data integrity upon initialization.
        """
        if self.total_hours < 0.0:
            logger.warning(f"Negative total hours detected in row: {self.total_hours}")
            raise InvalidReportDataError("Total hours cannot be negative.")


@dataclass(frozen=True)
class ReportSummary:
    """
    Aggregates summary data for the report, supporting both top-summary fields (Type B)
    and bottom-summary fields (Type A) under a unified contract.
    """
    total_working_days: int = 0
    total_monthly_hours: float = 0.0

    # Unique fields for Format A (Bottom summary)
    total_100_hours: float = 0.0
    total_125_hours: float = 0.0
    total_150_hours: float = 0.0
    bonus: float = 0.0
    travel: float = 0.0

    # Unique fields for Format B (Top summary / Payment details)
    hourly_rate: float = 0.0
    total_payment: float = 0.0

    def __post_init__(self) -> None:
        """
        Validates summary data integrity upon initialization.
        """
        if self.total_working_days < 0 or self.total_monthly_hours < 0.0:
            logger.warning(f"Invalid summary metrics detected - Days: {self.total_working_days}, Hours: {self.total_monthly_hours}")
            raise InvalidReportDataError("Summary working days and monthly hours cannot be negative.")


@dataclass
class AttendanceReport:
    """
    The central contract of the system.
    Once raw text is parsed into this object, all subsequent stages
    (transformation and rendering) operate exclusively on it without knowing
    the original PDF type or parser implementation.
    """
    report_type: str  # e.g., 'Type A' or 'Type B'
    rows: List[AttendanceRow] = field(default_factory=list)
    summary: Optional[ReportSummary] = None
    employee_card: Optional[str] = None  # Relevant for Type B (e.g., '22-090')
    title: Optional[str] = None  # Report main header title

    def __post_init__(self) -> None:
        """
        Validates report integrity upon initialization.
        """
        if not self.report_type:
            logger.error("Attempted to initialize AttendanceReport with empty report_type.")
            raise InvalidReportDataError("Report type cannot be empty.")
        logger.debug(f"AttendanceReport initialized for type: {self.report_type} with {len(self.rows)} rows.")