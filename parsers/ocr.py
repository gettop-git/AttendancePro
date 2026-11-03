from pathlib import Path
import logging
import subprocess
import pytesseract
from pdf2image import convert_from_path
from domain.exceptions import AttendanceSystemError

# Logger setup for the OCR extraction module
logger = logging.getLogger(__name__)

# A PDF with at least this many words of embedded text is read directly (no OCR needed).
MIN_EMBEDDED_WORDS = 20


def _extract_embedded_text(pdf_path: Path) -> str:
    """
    Reads the text that is stored inside the PDF itself, keeping the table layout
    (one table row per line). Uses `pdftotext` from Poppler, which is already
    required by pdf2image. Returns "" if the tool is missing or fails.
    """
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", str(pdf_path), "-"],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            check=True,
        )
        return result.stdout
    except (OSError, subprocess.SubprocessError) as e:
        logger.warning(f"Could not read embedded text with pdftotext ({e}); falling back to OCR.")
        return ""


def extract_text_from_pdf(pdf_path: Path, lang: str = "eng") -> str:
    """
    Converts a PDF file into images and extracts raw text using Tesseract OCR,
    incorporating structured logging and robust error handling.

    :param pdf_path: Path object pointing to the target PDF file.
    :param lang: Language code for OCR processing (default is 'eng').
    :return: Extracted raw text string from the PDF.
    """
    try:
        pdf_path = Path(pdf_path)
        logger.info(f"Starting OCR text extraction for file: {pdf_path} with language: {lang}")

        if not pdf_path.exists():
            error_msg = f"Target PDF file not found at: {pdf_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        # Prefer the text stored inside the PDF: it is exact, while OCR can misread
        # white-on-color table headers and currency symbols. Scanned PDFs have no
        # such text, so they fall through to OCR below.
        embedded_text = _extract_embedded_text(pdf_path)
        if len(embedded_text.split()) >= MIN_EMBEDDED_WORDS:
            logger.info(f"Using the embedded text of: {pdf_path}")
            return embedded_text
        logger.info(f"No usable embedded text in {pdf_path}; using OCR.")

        # Convert PDF pages into memory images
        images = convert_from_path(pdf_path)
        if not images:
            logger.warning(f"No images were generated from PDF file: {pdf_path}")

        extracted_text = []
        for index, image in enumerate(images, start=1):
            # Perform OCR recognition on each page image
            text = pytesseract.image_to_string(image, lang=lang)
            extracted_text.append(text)
            logger.debug(f"Successfully processed OCR for page {index} of {pdf_path}")

        full_text = "\n".join(extracted_text)
        logger.info(f"OCR text extraction completed successfully for: {pdf_path}")
        return full_text

    except FileNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Critical error during OCR extraction for {pdf_path}: {e}", exc_info=True)
        raise AttendanceSystemError(f"OCR extraction failed for {pdf_path}: {e}") from e