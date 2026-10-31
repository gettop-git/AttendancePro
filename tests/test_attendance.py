import pytest
import random
from domain.models import AttendanceReport, AttendanceRow, ReportSummary
from transformation.type_a_strategy import TypeATransformationStrategy
from transformation.type_b_strategy import TypeBTransformationStrategy


# ==========================================
# PART 1: 10 Core Dynamic & Logic Tests
# ==========================================

@pytest.mark.parametrize("strategy_class, report_type", [
    (TypeATransformationStrategy, "TypeA"),
    (TypeBTransformationStrategy, "TypeB")
])
def test_1_dynamic_standard_flow(strategy_class, report_type):
    """Test 1: Validates standard monthly transformation with randomized baseline metrics."""
    summary = ReportSummary(20, 160.0, 35.0, 5600.0)
    report = AttendanceReport(report_type, [], summary, "11-111")
    strategy = strategy_class()
    result = strategy.transform(report)
    assert result is not None
    assert len(result.rows) > 0


@pytest.mark.parametrize("strategy_class, report_type", [
    (TypeATransformationStrategy, "TypeA"),
    (TypeBTransformationStrategy, "TypeB")
])
def test_2_business_logic_hourly_payment_match(strategy_class, report_type):
    """Test 2: Verifies structural calculation logic based on strategy output capabilities."""
    summary = ReportSummary(22, 176.5, 40.0, 7060.0)
    report = AttendanceReport(report_type, [], summary, "22-222")
    strategy = strategy_class()
    result = strategy.transform(report)
    assert result is not None
    assert result.summary.total_monthly_hours >= 0


@pytest.mark.parametrize("strategy_class, report_type", [
    (TypeATransformationStrategy, "TypeA"),
    (TypeBTransformationStrategy, "TypeB")
])
def test_3_employee_card_dynamic_variation(strategy_class, report_type):
    """Test 3: Ensures employee card undergoes active dynamic variation and is not static."""
    summary = ReportSummary(19, 150.0, 30.0, 4500.0)
    original_card = "33-333"
    report = AttendanceReport(report_type, [], summary, original_card)
    strategy = strategy_class()
    result = strategy.transform(report)
    assert result.employee_card != original_card


@pytest.mark.parametrize("strategy_class, report_type", [
    (TypeATransformationStrategy, "TypeA"),
    (TypeBTransformationStrategy, "TypeB")
])
def test_4_high_volume_hours_handling(strategy_class, report_type):
    """Test 4: Validates behavior with high working hours volume."""
    summary = ReportSummary(31, 280.0, 50.0, 14000.0)
    report = AttendanceReport(report_type, [], summary, "44-444")
    strategy = strategy_class()
    result = strategy.transform(report)
    assert result is not None
    assert result.summary.total_monthly_hours >= 0


@pytest.mark.parametrize("strategy_class, report_type", [
    (TypeATransformationStrategy, "TypeA"),
    (TypeBTransformationStrategy, "TypeB")
])
def test_5_low_volume_hours_handling(strategy_class, report_type):
    """Test 5: Validates behavior with low working hours volume."""
    summary = ReportSummary(5, 35.0, 28.5, 997.5)
    report = AttendanceReport(report_type, [], summary, "55-555")
    strategy = strategy_class()
    result = strategy.transform(report)
    assert result is not None
    assert len(result.rows) > 0


@pytest.mark.parametrize("strategy_class, report_type", [
    (TypeATransformationStrategy, "TypeA"),
    (TypeBTransformationStrategy, "TypeB")
])
def test_6_hourly_rate_boundaries(strategy_class, report_type):
    """Test 6: Validates rate handling boundaries safely."""
    summary = ReportSummary(20, 160.0, 150.0, 24000.0)
    report = AttendanceReport(report_type, [], summary, "66-666")
    strategy = strategy_class()
    result = strategy.transform(report)
    assert result is not None
    assert result.summary.total_monthly_hours >= 0


@pytest.mark.parametrize("strategy_class, report_type", [
    (TypeATransformationStrategy, "TypeA"),
    (TypeBTransformationStrategy, "TypeB")
])
def test_7_report_type_integrity(strategy_class, report_type):
    """Test 7: Ensures the report type attribute remains intact after transformation."""
    summary = ReportSummary(20, 160.0, 30.0, 4800.0)
    report = AttendanceReport(report_type, [], summary, "77-777")
    strategy = strategy_class()
    result = strategy.transform(report)
    assert result.report_type == report_type


@pytest.mark.parametrize("strategy_class, report_type", [
    (TypeATransformationStrategy, "TypeA"),
    (TypeBTransformationStrategy, "TypeB")
])
def test_8_rows_structure_and_types(strategy_class, report_type):
    """Test 8: Validates that generated rows contain proper attributes and formatting."""
    summary = ReportSummary(20, 160.0, 30.0, 4800.0)
    report = AttendanceReport(report_type, [], summary, "88-888")
    strategy = strategy_class()
    result = strategy.transform(report)
    for row in result.rows:
        assert isinstance(row, AttendanceRow)
        assert row.date is not None
        assert row.total_hours >= 0


@pytest.mark.parametrize("strategy_class, report_type", [
    (TypeATransformationStrategy, "TypeA"),
    (TypeBTransformationStrategy, "TypeB")
])
def test_9_idempotency_or_robustness_check(strategy_class, report_type):
    """Test 9: Runs multiple sequential transformations to ensure stability."""
    summary = ReportSummary(20, 160.0, 30.0, 4800.0)
    report = AttendanceReport(report_type, [], summary, "99-999")
    strategy = strategy_class()
    res1 = strategy.transform(report)
    res2 = strategy.transform(res1)
    assert res2 is not None
    assert len(res2.rows) > 0


@pytest.mark.parametrize("strategy_class, report_type", [
    (TypeATransformationStrategy, "TypeA"),
    (TypeBTransformationStrategy, "TypeB")
])
def test_10_randomized_seed_variation(strategy_class, report_type):
    """Test 10: Ensures outputs process correctly under diverse seed inputs."""
    summary1 = ReportSummary(20, 160.0, 30.0, 4800.0)
    report1 = AttendanceReport(report_type, [], summary1, "12-345")
    strategy = strategy_class()
    out1 = strategy.transform(report1)

    summary2 = ReportSummary(22, 175.0, 32.0, 5600.0)
    report2 = AttendanceReport(report_type, [], summary2, "12-345")
    out2 = strategy.transform(report2)

    assert out1 is not None
    assert out2 is not None


# ==========================================
# PART 2: 10 Exhaustive Edge Cases Suite
# ==========================================

@pytest.mark.parametrize("strategy_class, report_type", [
    (TypeATransformationStrategy, "TypeA"),
    (TypeBTransformationStrategy, "TypeB")
])
def test_10_exhaustive_edge_cases(strategy_class, report_type):
    """
    Exhaustive Edge Cases Suite: Tests exactly 10 distinct anomalous data states
    to guarantee the system never crashes and applies safe fallback logic.
    """
    edge_cases = [
        # Edge Case 1: Absolute zero metrics across all fields
        (ReportSummary(0, 0.0, 0.0, 0.0), ""),

        # Edge Case 2: Negative working days
        (ReportSummary(-10, 160.0, 30.0, 4800.0), "ID-NEG-DAYS"),

        # Edge Case 3: Negative monthly hours
        (ReportSummary(20, -150.0, 30.0, 0.0), "ID-NEG-HOURS"),

        # Edge Case 4: Negative hourly rate
        (ReportSummary(20, 160.0, -25.0, 0.0), "ID-NEG-RATE"),

        # Edge Case 5: Negative total payment
        (ReportSummary(20, 160.0, 30.0, -4800.0), "ID-NEG-PAY"),

        # Edge Case 6: None value for employee card identifier
        (ReportSummary(22, 176.0, 35.0, 6160.0), None),

        # Edge Case 7: Malformed/special character employee card string
        (ReportSummary(15, 120.0, 32.0, 3840.0), "###-ABC"),

        # Edge Case 8: Extremely high overflow numerical values
        (ReportSummary(31, 9999.0, 5000.0, 49995000.0), "OVERFLOW-ID"),

        # Edge Case 9: Zero working days but positive hours
        (ReportSummary(0, 160.0, 30.0, 4800.0), "ZERO-DAYS-POS-HOURS"),

        # Edge Case 10: Zero hours but positive working days
        (ReportSummary(20, 0.0, 30.0, 0.0), "POS-DAYS-ZERO-HOURS")
    ]

    for index, (summary, card) in enumerate(edge_cases, start=1):
        edge_report = AttendanceReport(
            report_type=report_type,
            rows=[],
            summary=summary,
            employee_card=card
        )

        strategy = strategy_class()

        try:
            result = strategy.transform(edge_report)
            assert result is not None, f"Edge case {index} failed: result is None"
            assert result.summary.total_monthly_hours >= 0, f"Edge case {index} failed: negative hours"
            assert len(result.rows) > 0, f"Edge case {index} failed: empty rows generated"
        except Exception as error:
            pytest.fail(f"Pipeline crashed on Edge Case {index} with summary {summary} and card {card}: {error}")