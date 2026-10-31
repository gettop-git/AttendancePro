from parsers.ocr import extract_text_from_pdf
from typing import Callable, List, Optional, Dict, Any
from pathlib import Path
import re
import logging
from domain.models import AttendanceReport, AttendanceRow, ReportSummary
from domain.exceptions import InvalidReportDataError
from parsers.base_parser import BaseParser

# Logger setup for the Type B parser module
logger = logging.getLogger(__name__)


class TypeBParser(BaseParser):
    """
    Concrete parser implementation for Type B (English) attendance reports.
    Inherits from BaseParser and implements the abstract methods required by the Template Method pattern,
    incorporating structured logging and error handling.
    """

    # Regex pattern matching a data row in Type B reports (e.g., 1/9/22 Thursday 08:30 12:00 3.50 or dashes for weekends)
    ROW_PATTERN = re.compile(
        r"(?P<date>\d{1,2}/\d{1,2}/\d{2,4})\s+"
        r"(?P<day_of_week>[A-Za-z]+)\s+"
        r"(?P<clock_in>\d{2}:\d{2}|-)\s+"
        r"(?P<clock_out>\d{2}:\d{2}|-)\s+"
        r"(?P<total_hours>[\d.]+|-\s*)"
    )

    # Regex pattern matching employee card metadata
    EMPLOYEE_CARD_PATTERN = re.compile(r"Employee\s*Card:\s*(?P<card>[\w\-]+)", re.IGNORECASE)

    def __init__(self, ocr_extractor: Callable[[Path], str] = extract_text_from_pdf) -> None:
        """
        Initializes the Type B parser with an OCR extractor function.
        """
        super().__init__(ocr_extractor=ocr_extractor, report_type="Type B")
        logger.debug("TypeBParser initialized successfully.")

    def parse(self, file_path: Path) -> AttendanceReport:
        """
        Overrides the base parse method to also extract Type B specific metadata like employee_card,
        with robust logging and error handling.
        """
        try:
            file_path = Path(file_path)
            logger.info(f"Starting Type B parsing process for file: {file_path}")

            if not file_path.exists():
                error_msg = f"Target file not found at: {file_path}"
                logger.error(error_msg)
                raise FileNotFoundError(error_msg)

            raw_text = self._ocr_extractor(file_path)
            if not raw_text:
                logger.warning(f"Extracted raw text is empty for file: {file_path}")

            lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

            # Extract employee card if present in header metadata
            employee_card = self._extract_employee_card(lines)
            if employee_card:
                logger.debug(f"Extracted employee card: {employee_card}")

            # Run the standard template method flow from BaseParser
            report = super().parse(file_path)
            report.employee_card = employee_card

            logger.info("Type B parsing and metadata extraction completed successfully.")
            return report

        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Critical error during Type B parsing for file {file_path}: {e}", exc_info=True)
            raise InvalidReportDataError(f"Type B parsing failed for {file_path}: {e}") from e

    def _extract_employee_card(self, lines: List[str]) -> Optional[str]:
        """
        Extracts the employee card identifier from the header lines.
        """
        try:
            for line in lines:
                match = self.EMPLOYEE_CARD_PATTERN.search(line)
                if match:
                    return match.group("card")
            return None
        except Exception as e:
            logger.warning(f"Error while extracting employee card: {e}")
            return None

    def _is_header_line(self, line: str) -> bool:
        """
        Determines if a given line is part of table headers, titles, summary headers, or metadata.
        """
        line_lower = line.lower()
        return (
                "timesheet" in line_lower or
                "employee card" in line_lower or
                "total working days" in line_lower or
                "total monthly hours" in line_lower or
                "hourly rate" in line_lower or
                "total payment" in line_lower or
                ("date" in line_lower and "day of week" in line_lower)
        )

    def _parse_summary(self, lines: List[str]) -> Optional[ReportSummary]:
        """
        Parses top-summary fields for Type B reports (Total Working Days, Total Monthly Hours, Hourly Rate, Total Payment) safely.
        """
        try:
            total_days = 0
            monthly_hours = 0.0
            hourly_rate = 0.0
            total_payment = 0.0

            # Scan lines to extract summary values robustly based on preceding labels
            for idx, line in enumerate(lines):
                line_lower = line.lower()
                if "total working days" in line_lower and idx + 1 < len(lines):
                    try:
                        total_days = int(lines[idx + 1].strip())
                    except ValueError:
                        pass
                if "total monthly hours" in line_lower and idx + 1 < len(lines):
                    try:
                        monthly_hours = float(lines[idx + 1].strip())
                    except ValueError:
                        pass
                if "hourly rate" in line_lower and idx + 1 < len(lines):
                    try:
                        rate_str = lines[idx + 1].strip().replace("■", "").replace(",", "")
                        hourly_rate = float(rate_str)
                    except ValueError:
                        pass
                if "total payment" in line_lower and idx + 1 < len(lines):
                    try:
                        pay_str = lines[idx + 1].strip().replace("■", "").replace(",", "")
                        total_payment = float(pay_str)
                    except ValueError:
                        pass

            logger.debug("Type B summary successfully parsed.")
            return ReportSummary(
                total_working_days=total_days,
                total_monthly_hours=monthly_hours,
                hourly_rate=hourly_rate,
                total_payment=total_payment
            )
        except Exception as e:
            logger.error(f"Error occurred while parsing Type B summary: {e}", exc_info=True)
            raise InvalidReportDataError(f"Failed to parse Type B summary: {e}") from e

    def _parse_row(self, line: str) -> Optional[AttendanceRow]:
        """
        Parses a single row line for Type B reports into an AttendanceRow object.
        Gracefully handles missing punches or weekend dashes ('-').
        """
        try:
            match = self.ROW_PATTERN.search(line)
            if not match:
                return None

            data = match.groupdict()
            clock_in = data.get("clock_in", "-")
            clock_out = data.get("clock_out", "-")
            total_hours_str = data.get("total_hours", "0.0").strip()

            is_missing = (clock_in == "-" or clock_out == "-" or total_hours_str == "-")
            total_hours = 0.0 if is_missing else float(total_hours_str)

            return AttendanceRow(
                date=data.get("date"),
                day_of_week=data.get("day_of_week"),
                clock_in=None if clock_in == "-" else clock_in,
                clock_out=None if clock_out == "-" else clock_out,
                total_hours=total_hours,
                is_missing_punch=is_missing,
                is_overtime_hazard=False
            )
        except Exception as e:
            logger.warning(f"Failed to parse Type B row line ('{line}'): {e}")
            return None