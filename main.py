from pathlib import Path
import sys
import logging

from parsers.classifier import DocumentClassifier
from parsers.factory import ParserFactory
from transformation.service import TransformationService
from generators.html_renderer import HtmlRenderer
from generators.pdf_renderer import PdfRenderer
from domain.exceptions import AttendanceSystemError, InvalidReportDataError

# Configure root logger for the main pipeline execution
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def process_attendance_report(input_pdf_path: str, output_dir: str, use_pdf_output: bool = False) -> None:
    """
    Main pipeline function:
    1. Classifies the input PDF (Type A or Type B).
    2. Instantiates the correct parser using ParserFactory and parses the file into an AttendanceReport model.
    3. Transforms the report data deterministically using TransformationService.
    4. Renders the final transformed report into HTML or PDF format.
    """
    try:
        input_path = Path(input_pdf_path)
        output_directory = Path(output_dir)
        output_directory.mkdir(parents=True, exist_ok=True)

        logger.info(f"Starting attendance report pipeline for: {input_path}")
        print(f"[INFO] Processing file: {input_path.name}...")

        if not input_path.exists():
            error_msg = f"Input file not found at: {input_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        # Step 1: Classify document type ('type_a' or 'type_b')
        logger.info("Executing Step 1: Document classification.")
        doc_type_key = DocumentClassifier.classify(input_path)
        print(f"[INFO] Document classified as: {doc_type_key}")
        logger.info(f"Document successfully classified as: {doc_type_key}")

        # Step 2: Get the correct parser from ParserFactory and parse raw text into AttendanceReport
        logger.info(f"Executing Step 2: Instantiating parser for type '{doc_type_key}' and parsing report.")
        parser = ParserFactory.get_parser(doc_type_key)
        report = parser.parse(input_path)
        print(f"[INFO] Successfully parsed {len(report.rows)} attendance rows.")
        logger.info(f"Successfully parsed {len(report.rows)} rows from input file.")

        # Step 3: Transform report data deterministically
        logger.info("Executing Step 3: Transforming report data.")
        transformation_service = TransformationService()
        transformed_report = transformation_service.transform(report)
        print(f"[INFO] Report successfully transformed.")
        logger.info("Report transformation completed successfully.")

        # Step 4: Render to output file (HTML or PDF)
        file_extension = "pdf" if use_pdf_output else "html"
        output_file_path = output_directory / f"{input_path.stem}_transformed.{file_extension}"

        logger.info(f"Executing Step 4: Rendering report to {file_extension.upper()} format at {output_file_path}")
        if use_pdf_output:
            renderer = PdfRenderer()
        else:
            renderer = HtmlRenderer()

        renderer.render(transformed_report, str(output_file_path))
        print(f"[SUCCESS] Output generated successfully at: {output_file_path}\n")
        logger.info(f"Pipeline finished successfully. Output saved to: {output_file_path}")

    except (AttendanceSystemError, InvalidReportDataError, FileNotFoundError) as biz_err:
        logger.error(f"Business logic or file error during pipeline execution: {biz_err}", exc_info=True)
        print(f"[ERROR] Processing failed: {biz_err}")
        raise
    except Exception as e:
        logger.error(f"Unexpected critical error in pipeline execution: {e}", exc_info=True)
        print(f"[ERROR] An unexpected error occurred: {e}")
        raise AttendanceSystemError(f"Pipeline failed: {e}") from e


if __name__ == "__main__":
    # Example usage execution flow
    # Pass input file path as argument or use default paths for testing
    if len(sys.argv) > 1:
        target_pdf = sys.argv[1]
    else:
        # Default placeholder path for testing
        target_pdf = "input_pdfs/sample_report.pdf"

    output_folder = "output"

    try:
        process_attendance_report(target_pdf, output_folder, use_pdf_output=False)
    except Exception as e:
        print(f"[ERROR] Pipeline terminated with error.")