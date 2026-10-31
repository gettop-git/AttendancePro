from pathlib import Path
import logging
from parsers.ocr import extract_text_from_pdf
from domain.exceptions import InvalidReportDataError

# Logger setup for the document classifier module
logger = logging.getLogger(__name__)


class DocumentClassifier:
    """
    Robust multi-feature document classifier that analyzes text content
    using a combination of unique fields, column headers, and structural layout patterns,
    incorporating structured logging and robust error handling.
    """

    @staticmethod
    def classify(file_path: Path) -> str:
        """
        Classifies the given PDF report into 'type_a' or 'type_b'
        based on an aggregate score of multiple distinct features and fields.
        """
        try:
            file_path = Path(file_path)
            logger.info(f"Starting document classification for file: {file_path}")

            if not file_path.exists():
                error_msg = f"Target file not found at: {file_path}"
                logger.error(error_msg)
                raise FileNotFoundError(error_msg)

            raw_text = extract_text_from_pdf(file_path)
            if not raw_text:
                logger.warning(f"Extracted raw text is empty for file: {file_path}")

            text_lower = raw_text.lower()

            score_type_a = 0
            score_type_b = 0

            # --- Type A Features (HaNesher / Detailed columns & bottom summary) ---
            type_a_keywords = [
                "break", "100%", "125%", "150%", "saturday",
                "location", "hanesher", "manpower", "travel:"
            ]
            for keyword in type_a_keywords:
                if keyword in text_lower:
                    score_type_a += 1

            # Strong unique structural signatures for Type A
            if "total days:" in text_lower or "100% hours:" in text_lower:
              score_type_a += 3

            # --- Type B Features (Employee Timesheet / Top summary & metadata) ---
            type_b_keywords = [
                "employee card", "hourly rate", "total payment",
                "total working days", "total monthly hours"
            ]
            for keyword in type_b_keywords:
                if keyword in text_lower:
                    score_type_b += 1

            # Strong unique structural signatures for Type B
            if "employee card:" in text_lower:
                score_type_b += 3

            logger.debug(f"Classification scores computed - Type A: {score_type_a}, Type B: {score_type_b}")

            # Decision making based on aggregate score comparison
            if score_type_a > score_type_b:
                logger.info(f"File {file_path} successfully classified as 'type_a'.")
                return "type_a"
            else:
                logger.info(f"File {file_path} successfully classified as 'type_b'.")
                return "type_b"

        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Critical error during document classification for {file_path}: {e}", exc_info=True)
            raise InvalidReportDataError(f"Classification failed for {file_path}: {e}") from e