import pytest

from domain.exceptions import InvalidReportDataError
from parsers.factory import ParserFactory
from parsers.type_a_parser import TypeAParser
from parsers.type_b_parser import TypeBParser
from tests.sample_data import TYPE_A_TEXT, TYPE_B_TEXT


def _pdf(tmp_path):
    pdf = tmp_path / "report.pdf"
    pdf.write_bytes(b"%PDF")
    return pdf


# ---------------- Type A ----------------

def test_type_a_parses_rows(tmp_path):
    report = TypeAParser(ocr_extractor=lambda p: TYPE_A_TEXT).parse(_pdf(tmp_path))
    assert report.report_type == "Type A"
    assert len(report.rows) == 3
    first = report.rows[0]
    assert (first.date, first.clock_in, first.clock_out, first.total_hours) == ("05/03/2023", "08:00", "17:00", 8.5)
    assert report.rows[2].saturday_hours == 4.0


def test_type_a_parses_summary(tmp_path):
    summary = TypeAParser(ocr_extractor=lambda p: TYPE_A_TEXT).parse(_pdf(tmp_path)).summary
    assert summary.total_working_days == 3
    assert summary.total_monthly_hours == 21.5
    assert summary.total_125_hours == 1.0
    assert summary.travel == 30.0


def test_type_a_missing_summary_raises(tmp_path):
    text_without_summary = "\n".join(TYPE_A_TEXT.splitlines()[:-1])
    with pytest.raises(InvalidReportDataError, match="summary"):
        TypeAParser(ocr_extractor=lambda p: text_without_summary).parse(_pdf(tmp_path))


# ---------------- Type B ----------------

def test_type_b_parses_rows_and_card(tmp_path):
    report = TypeBParser(ocr_extractor=lambda p: TYPE_B_TEXT).parse(_pdf(tmp_path))
    assert report.report_type == "Type B"
    assert report.employee_card == "22-090"
    assert len(report.rows) == 3
    assert report.rows[0].total_hours == 8.5
    # The Saturday row has dashes instead of times.
    assert report.rows[2].clock_in is None and report.rows[2].total_hours == 0.0


def test_type_b_parses_summary(tmp_path):
    summary = TypeBParser(ocr_extractor=lambda p: TYPE_B_TEXT).parse(_pdf(tmp_path)).summary
    assert summary.total_working_days == 21
    assert summary.total_monthly_hours == 180.5
    assert summary.hourly_rate == 30.65
    assert summary.total_payment == 5531.33


def test_type_b_unreadable_summary_value_raises(tmp_path):
    bad_text = TYPE_B_TEXT.replace("\n21\n", "\nabc\n")
    with pytest.raises(InvalidReportDataError, match="total working days"):
        TypeBParser(ocr_extractor=lambda p: bad_text).parse(_pdf(tmp_path))


def test_type_b_missing_summary_value_raises(tmp_path):
    bad_text = TYPE_B_TEXT.replace("Total Payment\n5531.33\n", "")
    with pytest.raises(InvalidReportDataError, match="total payment"):
        TypeBParser(ocr_extractor=lambda p: bad_text).parse(_pdf(tmp_path))


# ---------------- Shared behavior ----------------

@pytest.mark.parametrize("parser_class", [TypeAParser, TypeBParser])
def test_text_without_rows_raises(parser_class, tmp_path):
    with pytest.raises(InvalidReportDataError):
        parser_class(ocr_extractor=lambda p: "nothing useful here").parse(_pdf(tmp_path))


@pytest.mark.parametrize("parser_class", [TypeAParser, TypeBParser])
def test_missing_file_raises_file_not_found(parser_class, tmp_path):
    with pytest.raises(FileNotFoundError):
        parser_class(ocr_extractor=lambda p: "").parse(tmp_path / "missing.pdf")


# ---------------- Factory ----------------

@pytest.mark.parametrize("file_type, expected_class", [("type_a", TypeAParser), ("type_b", TypeBParser)])
def test_factory_returns_matching_parser(file_type, expected_class):
    assert isinstance(ParserFactory.get_parser(file_type), expected_class)


def test_factory_unknown_type_raises():
    with pytest.raises(ValueError):
        ParserFactory.get_parser("type_z")


def test_factory_passes_custom_ocr_extractor(tmp_path):
    parser = ParserFactory.get_parser("type_b", ocr_extractor=lambda p: TYPE_B_TEXT)
    assert parser.parse(_pdf(tmp_path)).employee_card == "22-090"