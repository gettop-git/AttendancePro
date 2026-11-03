import argparse
import logging
from pathlib import Path

from main import build_report, get_renderer, setup_logging
from domain.exceptions import AttendanceSystemError, InvalidReportDataError

logger = logging.getLogger(__name__)

COMPANY_PREFIXES = {"Type A": "HaNesher", "Type B": "Employee"}

MONTHS = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December",
}


def month_and_year(report) -> tuple[str, str]:
    """Extract month name and year from the first row's date (dd/mm/yy[yy]). No defaults."""
    if not report.rows or not report.rows[0].date:
        raise InvalidReportDataError("Cannot build a file name: the first row has no date.")
    date_text = report.rows[0].date
    try:
        _, month_num, raw_year = date_text.split("/")
        month = MONTHS[int(month_num)]
    except (ValueError, KeyError) as err:
        raise InvalidReportDataError(f"Cannot read month/year from the date {date_text!r}.") from err
    year = "20" + raw_year if len(raw_year) == 2 else raw_year
    return month, year


def build_filename(report) -> str:
    """Build a name like HaNesher_July_2023_Card_22_090."""
    prefix = COMPANY_PREFIXES.get(report.report_type)
    if prefix is None:
        raise InvalidReportDataError(f"Unknown report type: {report.report_type!r}")
    if not report.employee_card:
        raise InvalidReportDataError("Cannot build a file name: the report has no employee card number.")
    month, year = month_and_year(report)
    card = report.employee_card.replace("-", "_")
    return f"{prefix}_{month}_{year}_Card_{card}"


def ask_export_format() -> str:
    print("\n--- Export Format Selection ---")
    while True:
        choice = input("Enter the desired export format [type html or pdf]: ").strip().lower()
        if choice in ("html", "pdf"):
            return choice
        logger.warning(f"Invalid export choice: '{choice}'")
        print("[WARNING] Invalid choice. Please type 'html' or 'pdf' only.")


def parse_args():
    parser = argparse.ArgumentParser(description="Interactive Attendance Report Processing CLI")
    parser.add_argument("file", type=str, help="Path to the input PDF attendance report")
    parser.add_argument("--output", type=str, default="output", help="Directory for output files")
    parser.add_argument("--verbose", action="store_true", help="Show full error details (traceback) when something fails")
    args = parser.parse_args()

    file_path = Path(args.file).expanduser().resolve()
    if not file_path.is_file():
        parser.error(f"Input path is not an existing file: {file_path}")
    return file_path, Path(args.output), args.verbose


def main():
    verbose = False
    try:
        file_path, output_dir, verbose = parse_args()
        setup_logging(verbose)
        output_dir.mkdir(exist_ok=True, parents=True)

        report = build_report(str(file_path))

        export_format = ask_export_format()
        out_file = output_dir / f"{build_filename(report)}.{export_format}"

        get_renderer(export_format == "pdf").render(report, str(out_file))
        print(f"\n[SUCCESS] File successfully exported to: {out_file}")

    except (AttendanceSystemError, InvalidReportDataError) as err:
        logger.error(f"Business logic error: {err}", exc_info=verbose)
        print(f"\n[ERROR] Business validation failed: {err}")
    except Exception as err:
        logger.error(f"Unexpected error: {err}", exc_info=verbose)
        print(f"\n[ERROR] An unexpected error occurred: {err}")


if __name__ == "__main__":
    main()