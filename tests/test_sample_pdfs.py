"""Runs the real sample PDFs in input_pdfs/ through the pipeline."""
import shutil
from pathlib import Path

import pytest

from main import build_report
from parsers.classifier import DocumentClassifier
from parsers.factory import ParserFactory
from parsers.ocr import extract_text_from_pdf

SAMPLES = sorted((Path(__file__).resolve().parent.parent / "input_pdfs").glob("*.pdf"))

# These tests read the text stored inside the PDFs, which needs pdftotext (part of Poppler).
pytestmark = pytest.mark.skipif(
    not SAMPLES or shutil.which("pdftotext") is None,
    reason="no sample PDFs in input_pdfs/ or pdftotext is not installed",
)


def _expected_type(pdf_path):
    return "type_a" if pdf_path.name.startswith("hanesher") else "type_b"


@pytest.mark.parametrize("pdf_path", SAMPLES, ids=lambda path: path.name)
def test_sample_is_classified_correctly(pdf_path):
    assert DocumentClassifier.classify(pdf_path) == _expected_type(pdf_path)


@pytest.mark.parametrize("pdf_path", SAMPLES, ids=lambda path: path.name)
def test_sample_is_parsed_with_summary(pdf_path):
    parser = ParserFactory.get_parser(_expected_type(pdf_path), ocr_extractor=extract_text_from_pdf)
    report = parser.parse(pdf_path)
    assert len(report.rows) > 0
    assert report.summary.total_working_days > 0
    assert report.summary.total_monthly_hours > 0
    if report.report_type == "Type B":
        assert report.summary.hourly_rate > 0
        assert report.summary.total_payment > 0


@pytest.mark.parametrize("pdf_path", SAMPLES, ids=lambda path: path.name)
def test_sample_goes_through_the_whole_pipeline(pdf_path):
    report = build_report(str(pdf_path))
    assert len(report.rows) > 0