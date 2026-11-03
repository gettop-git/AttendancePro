from parsers.ocr import extract_text_from_pdf
from typing import Callable, List, Optional, Dict, Any
from pathlib import Path
import re
import logging
from domain.models import AttendanceReport, AttendanceRow, ReportSummary
from domain.exceptions import InvalidReportDataError
from parsers.base_parser import BaseParser

# Logger setup for the Type A parser module
logger = logging.getLogger(__name__)


class TypeAParser(BaseParser):
    """
    Concrete parser implementation for Type A attendance reports.
    Inherits from BaseParser and implements the abstract methods required by the Template Method pattern,
    incorporating structured logging and error handling.
    """

    # Regex pattern matching a standard data row in Type A reports
    ROW_PATTERN = re.compile(
        r"(?P<date>\d{2}/\d{2}/\d{4})\s+"
        r"(?P<day_of_week>[A-Za-z]+)\s+"
        r"(?P<location>[\w\-]+)\s+"
        r"(?P<clock_in>\d{2}:\d{2})\s+"
        r"(?P<clock_out>\d{2}:\d{2})\s+"
        r"(?P<break_duration>\d{2}:\d{2})\s+"
        r"(?P<total_hours>[\d.]+)\s+"
        r"(?P<overtime_100>[\d.]+)\s+"
        r"(?P<overtime_125>[\d.]+)\s+"
        r"(?P<overtime_150>[\d.]+)\s+"
        r"(?P<saturday_hours>[\d.]+)"
    )

    # Regex pattern matching the bottom summary line in Type A reports
    SUMMARY_PATTERN = re.compile(
        r"Total\s*Days:\s*(?P<total_working_days>\d+)\s*\|\s*"
        r"Total\s*Hours:\s*(?P<total_monthly_hours>[\d.]+)\s*\|\s*"
        r"100%\s*Hours:\s*(?P<total_100_hours>[\d.]+)\s*\|\s*"
        r"125%\s*Hours:\s*(?P<total_125_hours>[\d.]+)\s*\|\s*"
        r"150%\s*Hours:\s*(?P<total_150_hours>[\d.]+)\s*\|\s*"
        r"Bonus:\s*(?P<bonus>[\d.]+)\s*\|\s*"
        r"Travel:\s*(?P<travel>[\d.]+)",
        re.IGNORECASE
    )

    def __init__(self, ocr_extractor: Callable[[Path], str] = extract_text_from_pdf) -> None:
        """
        Initializes the Type A parser with an OCR extractor function.
        """
        super().__init__(ocr_extractor=ocr_extractor, report_type="Type A")
        logger.debug("TypeAParser initialized successfully.")

    def _is_header_line(self, line: str) -> bool:
        """
        Determines if a given line is part of the table headers, title, or metadata.
        """
        line_lower = line.lower()
        is_header = (
            "timesheet" in line_lower or
            "date" in line_lower or
            "day of week" in line_lower or
            "manpower" in line_lower or
            "total" in line_lower and "days:" not in line_lower
        )
        return is_header

    def _parse_summary(self, lines: List[str]) -> Optional[ReportSummary]:
        """
        Scans the text lines to locate and parse the bottom summary line of Type A reports.
        """
        try:
            for line in lines:
                match = self.SUMMARY_PATTERN.search(line)
                if match:
                    data = match.groupdict()
                    logger.debug("Type A summary successfully parsed.")
                    return ReportSummary(
                        total_working_days=int(data["total_working_days"]),
                        total_monthly_hours=float(data["total_monthly_hours"]),
                        total_100_hours=float(data["total_100_hours"]),
                        total_125_hours=float(data["total_125_hours"]),
                        total_150_hours=float(data["total_150_hours"]),
                        bonus=float(data["bonus"]),
                        travel=float(data["travel"])
                    )

            raise InvalidReportDataError(
                "The summary line (Total Days / Total Hours / ... / Travel) was not found in the report."
            )
        except InvalidReportDataError:
            raise
        except Exception as e:
            logger.error(f"Error occurred while parsing Type A summary: {e}", exc_info=True)
            raise InvalidReportDataError(f"Failed to parse Type A summary: {e}") from e

    def _parse_row(self, line: str) -> Optional[AttendanceRow]:
        """
        Parses a single row line using the regex pattern into an AttendanceRow object.
        """
        try:
            match = self.ROW_PATTERN.search(line)
            if not match:
                return None

            data = match.groupdict()
            return AttendanceRow(
                date=data.get("date"),
                day_of_week=data.get("day_of_week"),
                location=data.get("location"),
                clock_in=data.get("clock_in"),
                clock_out=data.get("clock_out"),
                break_duration=data.get("break_duration"),
                total_hours=float(data.get("total_hours", 0.0)),
                overtime_100=float(data.get("overtime_100", 0.0)),
                overtime_125=float(data.get("overtime_125", 0.0)),
                overtime_150=float(data.get("overtime_150", 0.0)),
                saturday_hours=float(data.get("saturday_hours", 0.0)),
                is_missing_punch=False,
                is_overtime_hazard=False
            )
        except Exception as e:
            logger.warning(f"Failed to parse Type A row line ('{line}'): {e}")
            return None