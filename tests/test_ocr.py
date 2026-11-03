import subprocess

import pytest

import parsers.ocr as ocr_module
from parsers.ocr import MIN_EMBEDDED_WORDS, extract_text_from_pdf


def _pdf(tmp_path):
    pdf = tmp_path / "report.pdf"
    pdf.write_bytes(b"%PDF")
    return pdf


def test_uses_embedded_text_when_available(tmp_path, monkeypatch):
    long_text = "word " * (MIN_EMBEDDED_WORDS + 5)
    monkeypatch.setattr(ocr_module, "_extract_embedded_text", lambda path: long_text)

    def ocr_must_not_run(*args, **kwargs):
        raise AssertionError("OCR should not run when the PDF has embedded text")

    monkeypatch.setattr(ocr_module, "convert_from_path", ocr_must_not_run)
    assert extract_text_from_pdf(_pdf(tmp_path)) == long_text


def test_falls_back_to_ocr_when_no_embedded_text(tmp_path, monkeypatch):
    monkeypatch.setattr(ocr_module, "_extract_embedded_text", lambda path: "too short")
    monkeypatch.setattr(ocr_module, "convert_from_path", lambda path: ["page1", "page2"])
    monkeypatch.setattr(
        ocr_module.pytesseract, "image_to_string", lambda image, lang="eng": f"text of {image}"
    )
    assert extract_text_from_pdf(_pdf(tmp_path)) == "text of page1\ntext of page2"


def test_missing_pdftotext_returns_empty_text(tmp_path, monkeypatch):
    def tool_missing(*args, **kwargs):
        raise FileNotFoundError("pdftotext")

    monkeypatch.setattr(subprocess, "run", tool_missing)
    assert ocr_module._extract_embedded_text(_pdf(tmp_path)) == ""


def test_missing_file_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        extract_text_from_pdf(tmp_path / "missing.pdf")