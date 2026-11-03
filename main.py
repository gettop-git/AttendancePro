import logging
import sys
from pathlib import Path

from parsers.classifier import DocumentClassifier
from parsers.factory import ParserFactory
from parsers.ocr import extract_text_from_pdf
from config import config
from transformation.service import TransformationService
from transformation.type_a_strategy import TypeATransformationStrategy
from transformation.type_b_strategy import TypeBTransformationStrategy
from generators.html_renderer import HtmlRenderer
from generators.pdf_renderer import PdfRenderer
from domain.exceptions import AttendanceSystemError, InvalidReportDataError

logger = logging.getLogger(__name__)

DEFAULT_INPUT = "input_pdfs/sample_report.pdf"
DEFAULT_OUTPUT_DIR = "output"


def setup_logging(verbose: bool = False) -> None:
    """
    Configure logging. Called only when the program is actually run.

    By default the technical log is hidden (the user sees the short messages
    printed by _notify). With verbose=True the full technical log is shown.
    """
    logging.basicConfig(
        level=logging.INFO if verbose else logging.CRITICAL,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def _notify(message: str, level: str = "INFO") -> None:
    """Single place for reporting progress: log it and show it to the user."""
    logger.log(getattr(logging, level), message)
    print(f"[{level}] {message}")


def validate_input(input_pdf_path: str) -> Path:
    path = Path(input_pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found at: {path}")
    return path


def classify(path: Path) -> str:
    doc_type = DocumentClassifier.classify(path)
    _notify(f"Document classified as: {doc_type}")
    return doc_type


def parse(path: Path, doc_type: str):
    parser = ParserFactory.get_parser(doc_type, ocr_extractor=extract_text_from_pdf)
    report = parser.parse(path)
    _notify(f"Parsed {len(report.rows)} attendance rows.")
    return report


def build_transformation_service() -> TransformationService:
    """Create the strategies here and hand them to the service."""
    return TransformationService(
        {
            "Type A": TypeATransformationStrategy(config),
            "Type B": TypeBTransformationStrategy(config),
        }
    )


def transform(report):
    transformed = build_transformation_service().transform(report)
    _notify("Report transformed.")
    return transformed


def get_renderer(use_pdf: bool):
    return PdfRenderer() if use_pdf else HtmlRenderer()


def build_output_path(input_path: Path, output_dir: str, use_pdf: bool) -> Path:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    extension = "pdf" if use_pdf else "html"
    return directory / f"{input_path.stem}_transformed.{extension}"


def build_report(input_pdf_path: str):
    """Validate -> classify -> parse -> transform. Returns the transformed report."""
    path = validate_input(input_pdf_path)
    _notify(f"Processing file: {path.name}")

    doc_type = classify(path)
    report = parse(path, doc_type)
    return transform(report)


def process_attendance_report(
    input_pdf_path: str, output_dir: str, use_pdf_output: bool = False
) -> None:
    """Full pipeline: build the report, then render it to HTML or PDF."""
    try:
        report = build_report(input_pdf_path)

        output_path = build_output_path(Path(input_pdf_path), output_dir, use_pdf_output)
        get_renderer(use_pdf_output).render(report, str(output_path))
        _notify(f"Output generated at: {output_path}")

    except (AttendanceSystemError, InvalidReportDataError, FileNotFoundError) as err:
        _notify(f"Processing failed: {err}", "ERROR")
        raise
    except Exception as err:
        _notify(f"Unexpected error: {err}", "ERROR")
        raise AttendanceSystemError(f"Pipeline failed: {err}") from err


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--verbose"]
    setup_logging(verbose="--verbose" in sys.argv)
    target_pdf = args[0] if args else DEFAULT_INPUT
    try:
        process_attendance_report(target_pdf, DEFAULT_OUTPUT_DIR)
    except Exception:
        sys.exit(1)