import pytest

import parsers.classifier as classifier_module
from domain.exceptions import InvalidReportDataError
from parsers.classifier import DocumentClassifier
from tests.sample_data import NOT_A_REPORT_TEXT, TYPE_A_TEXT, TYPE_B_TEXT


def _classify(text, tmp_path, monkeypatch):
    """Runs the classifier on a dummy file whose OCR text is `text`."""
    pdf = tmp_path / "report.pdf"
    pdf.write_bytes(b"%PDF")
    monkeypatch.setattr(classifier_module, "extract_text_from_pdf", lambda path: text)
    return DocumentClassifier.classify(pdf)


def test_classifies_type_a(tmp_path, monkeypatch):
    assert _classify(TYPE_A_TEXT, tmp_path, monkeypatch) == "type_a"


def test_classifies_type_b(tmp_path, monkeypatch):
    assert _classify(TYPE_B_TEXT, tmp_path, monkeypatch) == "type_b"


def test_non_report_text_raises_clear_error(tmp_path, monkeypatch):
    with pytest.raises(InvalidReportDataError, match="does not look like an attendance report"):
        _classify(NOT_A_REPORT_TEXT, tmp_path, monkeypatch)


def test_empty_text_raises_clear_error(tmp_path, monkeypatch):
    with pytest.raises(InvalidReportDataError):
        _classify("", tmp_path, monkeypatch)


def test_missing_file_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        DocumentClassifier.classify(tmp_path / "does_not_exist.pdf")