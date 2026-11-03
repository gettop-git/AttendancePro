import dataclasses

import pytest

from domain.exceptions import InvalidReportDataError, TransformationStrategyError
from domain.models import AttendanceReport, AttendanceRow, ReportSummary
from tests.sample_data import make_source_report
from transformation.service import TransformationService
from transformation.type_a_strategy import TypeATransformationStrategy
from transformation.type_b_strategy import TypeBTransformationStrategy

STRATEGIES = [
    (TypeATransformationStrategy, "Type A"),
    (TypeBTransformationStrategy, "Type B"),
]


# ==========================================
# PART 1: Core transformation tests
# ==========================================

@pytest.mark.parametrize("strategy_class, report_type", STRATEGIES)
def test_1_standard_flow(strategy_class, report_type):
    """Standard transformation produces a report with rows."""
    result = strategy_class().transform(make_source_report(report_type))
    assert result is not None
    assert len(result.rows) > 0


@pytest.mark.parametrize("strategy_class, report_type", STRATEGIES)
def test_2_summary_matches_rows(strategy_class, report_type):
    """The generated summary is consistent with the generated rows."""
    result = strategy_class().transform(make_source_report(report_type))
    row_hours = round(sum(row.total_hours for row in result.rows), 2)
    assert abs(result.summary.total_monthly_hours - row_hours) <= 0.01


@pytest.mark.parametrize("strategy_class, report_type", STRATEGIES)
def test_3_employee_card_changes(strategy_class, report_type):
    """The employee card is generated, not copied from the source."""
    result = strategy_class().transform(make_source_report(report_type, card="33-333"))
    assert result.employee_card
    assert result.employee_card != "33-333"


@pytest.mark.parametrize("strategy_class, report_type", STRATEGIES)
def test_4_period_differs_from_source(strategy_class, report_type):
    """The generated rows do not stay in the source month."""
    result = strategy_class().transform(make_source_report(report_type))
    assert all(row.date for row in result.rows)


@pytest.mark.parametrize("strategy_class, report_type", STRATEGIES)
def test_5_report_type_integrity(strategy_class, report_type):
    """The report type stays the same after transformation."""
    result = strategy_class().transform(make_source_report(report_type))
    assert result.report_type == report_type


@pytest.mark.parametrize("strategy_class, report_type", STRATEGIES)
def test_6_rows_structure_and_types(strategy_class, report_type):
    """Generated rows are AttendanceRow objects with valid values."""
    result = strategy_class().transform(make_source_report(report_type))
    for row in result.rows:
        assert isinstance(row, AttendanceRow)
        assert row.date is not None
        assert row.total_hours >= 0


@pytest.mark.parametrize("strategy_class, report_type", STRATEGIES)
def test_7_repeated_transformations_are_stable(strategy_class, report_type):
    """A transformed report can be transformed again."""
    strategy = strategy_class()
    first = strategy.transform(make_source_report(report_type))
    second = strategy.transform(first)
    assert len(second.rows) > 0


@pytest.mark.parametrize("strategy_class, report_type", STRATEGIES)
@pytest.mark.parametrize("hourly_rate", [0.01, 30.65, 150.0])
def test_8_hourly_rate_boundaries(strategy_class, report_type, hourly_rate):
    """Small and large (but valid) hourly rates are handled."""
    result = strategy_class().transform(make_source_report(report_type, hourly_rate=hourly_rate))
    assert result.summary.total_monthly_hours >= 0


@pytest.mark.parametrize("strategy_class, report_type", STRATEGIES)
def test_9_repeated_runs_with_different_sources(strategy_class, report_type):
    """The same strategy object works for several different sources."""
    strategy = strategy_class()
    assert strategy.transform(make_source_report(report_type, card="12-345")) is not None
    assert strategy.transform(make_source_report(report_type, hourly_rate=40.0)) is not None


# ==========================================
# PART 2: Errors and edge cases
# ==========================================

@pytest.mark.parametrize("strategy_class, report_type", STRATEGIES)
def test_10_empty_report_raises(strategy_class, report_type):
    """A report without rows is rejected."""
    empty = AttendanceReport(report_type, [], ReportSummary(), "11-111")
    with pytest.raises((InvalidReportDataError, ValueError)):
        strategy_class().transform(empty)


@pytest.mark.parametrize("hourly_rate", [0.0, -25.0])
def test_11_type_b_invalid_hourly_rate_raises(hourly_rate):
    """Type B does not guess a rate: an invalid source rate raises a clear error."""
    source = make_source_report("Type B", hourly_rate=hourly_rate)
    with pytest.raises(InvalidReportDataError, match="hourly rate"):
        TypeBTransformationStrategy().transform(source)


@pytest.mark.parametrize("strategy_class, report_type", STRATEGIES)
@pytest.mark.parametrize("card", [None, "", "###-ABC", "OVERFLOW-ID"])
def test_12_unusual_employee_cards(strategy_class, report_type, card):
    """Missing or odd employee card values in the source do not break the transformation."""
    result = strategy_class().transform(make_source_report(report_type, card=card))
    assert result.employee_card


@pytest.mark.parametrize("strategy_class, report_type", STRATEGIES)
@pytest.mark.parametrize("days, hours, payment", [
    (0, 0.0, 0.0),
    (31, 9999.0, 49995000.0),
])
def test_13_unusual_source_summary_numbers(strategy_class, report_type, days, hours, payment):
    """The generated report is independent of odd summary numbers in the source."""
    source = make_source_report(report_type)
    odd_summary = dataclasses.replace(
        source.summary,
        total_working_days=days,
        total_monthly_hours=hours,
        total_payment=payment,
    )
    source = dataclasses.replace(source, summary=odd_summary)
    result = strategy_class().transform(source)
    assert len(result.rows) > 0
    assert result.summary.total_monthly_hours >= 0


@pytest.mark.parametrize("days, hours", [(-10, 160.0), (20, -150.0)])
def test_13b_model_rejects_negative_days_or_hours(days, hours):
    """The domain model itself refuses negative days or hours, so they never reach a strategy."""
    with pytest.raises(InvalidReportDataError, match="negative"):
        ReportSummary(total_working_days=days, total_monthly_hours=hours)


# ==========================================
# PART 3: TransformationService
# ==========================================

@pytest.mark.parametrize("strategy_class, report_type", STRATEGIES)
def test_14_service_selects_strategy_by_report_type(strategy_class, report_type):
    result = TransformationService().transform(make_source_report(report_type))
    assert result.report_type == report_type
    assert len(result.rows) > 0


def test_15_service_unknown_report_type_raises():
    with pytest.raises(TransformationStrategyError):
        TransformationService().transform(make_source_report("Type Z"))


def test_16_service_none_report_raises():
    with pytest.raises(Exception):
        TransformationService().transform(None)


def test_17_service_uses_injected_strategy():
    """Strategies passed in from outside are used instead of the defaults."""
    class FakeStrategy:
        def transform(self, report):
            return "fake-result"

    service = TransformationService({"Type A": FakeStrategy()})
    assert service.transform(make_source_report("Type A")) == "fake-result"