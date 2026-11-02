import argparse
from pathlib import Path
import logging
from parsers.classifier import DocumentClassifier
from parsers.type_a_parser import TypeAParser
from parsers.type_b_parser import TypeBParser
from transformation.type_a_strategy import TypeATransformationStrategy
from transformation.type_b_strategy import TypeBTransformationStrategy
from generators.html_renderer import HtmlRenderer
from generators.pdf_renderer import PdfRenderer
from domain.exceptions import AttendanceSystemError, InvalidReportDataError

# Configure root logger for the application CLI
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """
    Main interactive entry point for the Attendance Report Processing CLI.
    Handles file validation, document classification, parsing, transformation,
    and rendering with robust structured logging and error handling.
    """
    try:
        parser = argparse.ArgumentParser(description="Interactive Attendance Report Processing CLI")
        parser.add_argument("file", type=str, help="Path to the input PDF attendance report")
        parser.add_argument("--output", type=str, default="output", help="Directory for output files")

        args = parser.parse_args()
        file_path = Path(args.file).expanduser().resolve()
        if not file_path.exists():
            parser.error(f"Input file does not exist: {file_path}")

        if not file_path.is_file():
            parser.error(f"Input path is not a file: {file_path}")

        logger.info(f"CLI invoked for file: {file_path}")

        if not file_path.exists():
            error_msg = f"File not found: {file_path}"
            logger.error(error_msg)
            print(f"[ERROR] {error_msg}")
            return

        output_dir = Path(args.output)
        output_dir.mkdir(exist_ok=True, parents=True)

        print(f"\n[INFO] Processing file: {file_path.name}...")
        logger.info(f"Starting classification for {file_path.name}")

        doc_type = DocumentClassifier.classify(file_path)
        print(f"[INFO] Document classified as: {doc_type}")
        logger.info(f"Document successfully classified as type: {doc_type}")

        # Parse and Transform based on document type
        if doc_type == "type_a":
            logger.debug("Executing Type A parsing and transformation pipeline.")
            report = TypeAParser().parse(file_path)
            report = TypeATransformationStrategy().transform(report)
            company_prefix = "HaNesher"
        else:
            logger.debug("Executing Type B parsing and transformation pipeline.")
            report = TypeBParser().parse(file_path)
            report = TypeBTransformationStrategy().transform(report)
            company_prefix = "Employee"

        # Extract month, year, and employee card dynamically from the generated report data
        month_str = "Report"
        year_str = "2022"
        if report.rows and report.rows[0].date:
            try:
                parts = report.rows[0].date.split("/")
                if len(parts) == 3:
                    month_num = int(parts[1])
                    year_str = "20" + parts[2] if len(parts[2]) == 2 else parts[2]
                    months_map = {
                        1: "January", 2: "February", 3: "March", 4: "April",
                        5: "May", 6: "June", 7: "July", 8: "August",
                        9: "September", 10: "October", 11: "November", 12: "December"
                    }
                    month_str = months_map.get(month_num, f"Month{month_num}")
            except Exception as date_parse_err:
                logger.warning(f"Could not dynamically parse month/year from date string: {date_parse_err}")

        card_str = report.employee_card.replace("-", "_") if report.employee_card else "22_090"

        # Construct the dynamic file name based on company prefix, month, year, and employee card
        dynamic_filename = f"{company_prefix}_{month_str}_{year_str}_Card_{card_str}"

        # Interactive prompt for export format selection in English
        print("\n--- Export Format Selection ---")
        user_choice = input("Enter the desired export format [type html or pdf]: ").strip().lower()

        while user_choice not in ["html", "pdf"]:
            print("[WARNING] Invalid choice. Please type 'html' or 'pdf' only.")
            logger.warning(f"User entered invalid export choice: '{user_choice}'")
            user_choice = input("Enter the desired export format [type html or pdf]: ").strip().lower()

        # Route and render according to user's interactive response
        if user_choice == "pdf":
            renderer = PdfRenderer()
            out_file = output_dir / f"{dynamic_filename}.pdf"
        else:
            renderer = HtmlRenderer()
            out_file = output_dir / f"{dynamic_filename}.html"

        logger.info(f"Rendering report using {renderer.__class__.__name__} to: {out_file}")
        renderer.render(report, str(out_file))
        print(f"\n[SUCCESS] File successfully exported to: {out_file}")
        logger.info("CLI execution completed successfully.")

    except (AttendanceSystemError, InvalidReportDataError) as biz_err:
        logger.error(f"Business logic error encountered in CLI: {biz_err}", exc_info=True)
        print(f"\n[ERROR] Business validation failed: {biz_err}")
    except Exception as e:
        logger.error(f"Unexpected critical error in CLI execution: {e}", exc_info=True)
        print(f"\n[ERROR] An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()