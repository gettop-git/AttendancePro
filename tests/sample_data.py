"""Shared sample data for the tests (no real PDFs or OCR needed)."""
from domain.models import AttendanceReport, AttendanceRow, ReportSummary

TYPE_A_TEXT = """HaNesher Manpower Ltd. - March 2023 Timesheet
Date Day of Week Location Clock In Clock Out Break Total Hours 100% 125% 150% Saturday
05/03/2023 Sunday HQ 08:00 17:00 00:30 8.50 8.50 0 0 0
06/03/2023 Monday HQ 08:00 17:30 00:30 9.00 8.00 1.00 0 0
11/03/2023 Saturday HQ 09:00 13:00 00:00 4.00 0 0 0 4.00
Total Days: 3 | Total Hours: 21.50 | 100% Hours: 16.50 | 125% Hours: 1.00 | 150% Hours: 0 | Bonus: 0 | Travel: 30
"""

# Type B text in the same layout as the real PDFs: a header row with the four column
# names, then one row with the four values (the "■" is the currency sign).
TYPE_B_HEADER_ROW = "   Total Working Days     Total Monthly Hours     Hourly Rate     Total Payment"
TYPE_B_VALUE_ROW = "          21                     180.50               ■30.65          ■5,532.33"

TYPE_B_TEXT = f"""                     Employee Timesheet - March 2023
                              Employee Card: 22-090

{TYPE_B_HEADER_ROW}

{TYPE_B_VALUE_ROW}

 Date          Day of Week      Clock In     Clock Out     Total Hours     Notes
05/03/23       Sunday           08:00        17:00         8.50
06/03/23       Monday           08:00        17:00         8.50
11/03/23       Saturday         -            -             -
"""

NOT_A_REPORT_TEXT = "Pizza recipe: flour, water, yeast. Bake for 20 minutes."


def make_source_report(report_type, hourly_rate=30.65, card="11-111"):
    """A small, valid source report that the transformation strategies can work with."""
    rows = [
        AttendanceRow(
            date=f"{day:02d}/03/2023",
            day_of_week="Day",
            location="HQ",
            clock_in="08:00",
            clock_out="17:00",
            break_duration="00:30",
            total_hours=8.5,
            overtime_100=8.5,
        )
        for day in (5, 6, 7, 8, 9)
    ]
    summary = ReportSummary(
        total_working_days=5,
        total_monthly_hours=42.5,
        total_100_hours=42.5,
        hourly_rate=hourly_rate,
        total_payment=round(42.5 * hourly_rate, 2),
    )
    title = "Employee Timesheet - March 2023" if report_type == "Type B" else "Attendance Report - 03/2023"
    return AttendanceReport(
        report_type=report_type, rows=rows, summary=summary, employee_card=card, title=title
    )