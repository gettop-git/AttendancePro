from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Callable
import logging
from domain.models import AttendanceReport, AttendanceRow, ReportSummary
from domain.exceptions import AttendanceSystemError, InvalidReportDataError
from parsers.ocr import extract_text_from_pdf

# Logger setup for the base parser module
logger = logging.getLogger(__name__)


class BaseParser(ABC):
    """
    Abstract base class for all file parsers implementing the Template Method pattern.
    Defines the shared parsing flow while delegating specific extraction steps to subclasses,
    incorporating robust structured logging and error handling.
    """

    def __init__(self, ocr_extractor: Callable[[Path], str] = extract_text_from_pdf, report_type: str = "General") -> None:
        """
        Initializes the base parser with a dependency-injected OCR extractor and report type.
        """
        self._ocr_extractor = ocr_extractor
        self.report_type = report_type
        logger.debug(f"Initialized {self.__class__.__name__} with report type: {report_type}")

    def parse(self, file_path: Path) -> AttendanceReport:
        """
        Shared parsing flow (Template Method) identical for every report type:
        Extracts text via OCR, cleans lines, parses summary, and extracts valid rows safely.
        """
        try:
            file_path = Path(file_path)
            logger.info(f"Starting parsing process for file: {file_path} using parser: {self.__class__.__name__}")

            if not file_path.exists():
                error_msg = f"Target file not found at: {file_path}"
                logger.error(error_msg)
                raise FileNotFoundError(error_msg)

            # Extract raw text and split into cleaned lines
            raw_text = self._ocr_extractor(file_path)
            if not raw_text:
                logger.warning(f"Extracted raw text is empty for file: {file_path}")

            lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

            # Parse summary using subclass implementation
            summary = self._parse_summary(lines)
            if summary is None:
                logger.warning(f"Summary could not be parsed or returned None for file: {file_path}")

            # Iterate through lines, filtering headers and noise, and parse rows
            rows: List[AttendanceRow] = []
            for line_idx, line in enumerate(lines, start=1):
                try:
                    if self._is_header_line(line) or self._is_noise(line):
                        continue
                    row = self._parse_row(line)
                    if row:
                        rows.append(row)
                except Exception as row_err:
                    logger.warning(f"Failed to parse line {line_idx} ('{line}'): {row_err}")

            logger.info(f"Successfully completed parsing for file: {file_path}. Extracted {len(rows)} valid rows.")
            return AttendanceReport(
                report_type=self.report_type,
                rows=rows,
                summary=summary
            )

        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Critical error during parsing file {file_path}: {e}", exc_info=True)
            raise InvalidReportDataError(f"Parsing failed for {file_path}: {e}") from e

    def _is_noise(self, line: str) -> bool:
        """
        Filters out OCR artifacts or empty/irrelevant short lines.
        Shared utility method for all parsers.
        """
        return len(line) < 3

    @abstractmethod
    def _parse_summary(self, lines: List[str]) -> Optional[ReportSummary]:
        """
        Parses the report summary from the extracted text lines.
        Must be implemented by concrete subclasses.
        """
        pass

    @abstractmethod
    def _parse_row(self, line: str) -> Optional[AttendanceRow]:
        """
        Parses a single text line into an AttendanceRow object.
        Must be implemented by concrete subclasses.
        """
        pass

    @abstractmethod
    def _is_header_line(self, line: str) -> bool:
        """
        Determines if a given line is a header or metadata line that should be skipped.
        Must be implemented by concrete subclasses.
        """
        pass