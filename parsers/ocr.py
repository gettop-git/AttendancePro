from pathlib import Path
import logging
import pytesseract
from pdf2image import convert_from_path
from domain.exceptions import AttendanceSystemError

# Logger setup for the OCR extraction module
logger = logging.getLogger(__name__)


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