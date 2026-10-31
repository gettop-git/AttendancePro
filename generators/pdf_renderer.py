from pathlib import Path
import logging
from generators.base_renderer import BaseRenderer
from generators.html_renderer import HtmlRenderer
from domain.models import AttendanceReport
from domain.exceptions import InvalidReportDataError, AttendanceSystemError
from xhtml2pdf import pisa

# Logger setup for the PDF renderer module
logger = logging.getLogger(__name__)


class PdfRenderer(BaseRenderer):
    """
    Concrete renderer implementation for generating PDF files from an AttendanceReport.
    Leverages HtmlRenderer to build the layout first, then converts it to PDF using xhtml2pdf,
    incorporating structured logging and robust error handling.
    """

    def __init__(self) -> None:
        """
        Initializes the PDF renderer with an instance of HtmlRenderer.
        """
        self._html_renderer = HtmlRenderer()
        logger.debug("PdfRenderer initialized successfully.")

    def render(self, report: AttendanceReport, output_path: str) -> None:
        """
        Renders the AttendanceReport into a PDF file at output_path safely.
        """
        output_path_obj = Path(output_path)
        temp_html_path = output_path_obj.with_suffix(".html")

        try:
            logger.info(f"Starting PDF rendering process for output path: {output_path}")

            if report is None:
                logger.error("Attempted to render a None report object to PDF.")
                raise InvalidReportDataError("Report object cannot be None.")

            # Step 1: Render intermediate HTML using HtmlRenderer
            logger.debug(f"Rendering intermediate HTML to temporary path: {temp_html_path}")
            self._html_renderer.render(report, str(temp_html_path))

            # Step 2: Convert HTML to PDF using xhtml2pdf
            try:
                with open(temp_html_path, "r", encoding="utf-8") as html_file:
                    html_content = html_file.read()

                output_path_obj.parent.mkdir(exist_ok=True, parents=True)

                with open(output_path, "wb") as pdf_file:
                    pisa_status = pisa.CreatePDF(html_content, dest=pdf_file)

                if pisa_status.err:
                    warning_msg = "PDF generated with some errors/warnings by pisa."
                    logger.warning(warning_msg)
                else:
                    logger.info(f"PDF successfully created at: {output_path}")

            except Exception as pdf_conv_err:
                logger.error(f"Failed during HTML to PDF conversion step: {pdf_conv_err}", exc_info=True)
                raise AttendanceSystemError(f"HTML to PDF conversion failed: {pdf_conv_err}") from pdf_conv_err

        except (InvalidReportDataError, AttendanceSystemError):
            raise
        except Exception as e:
            logger.error(f"Critical error during PDF rendering to {output_path}: {e}", exc_info=True)
            raise InvalidReportDataError(f"PDF rendering failed: {e}") from e

        finally:
            # Clean up the temporary HTML file so only the requested PDF remains
            try:
                if temp_html_path.exists():
                    temp_html_path.unlink(missing_ok=True)
                    logger.debug(f"Temporary HTML file cleaned up at: {temp_html_path}")
            except Exception as cleanup_err:
                logger.warning(f"Failed to clean up temporary HTML file {temp_html_path}: {cleanup_err}")