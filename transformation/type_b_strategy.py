
import calendar
import logging
import random
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Tuple

from domain.models import AttendanceReport, AttendanceRow, ReportSummary
from transformation.base_strategy import BaseTransformationStrategy

logger = logging.getLogger(__name__)


class TypeBTransformationStrategy(BaseTransformationStrategy):

    DEFAULT_SETTINGS = {
        "min_working_days": 10,
        "max_working_days": 22,
        "start_tolerance_minutes": 15,
        "end_tolerance_minutes": 30,
        "duration_tolerance_minutes": 30,
        "time_interval_minutes": 15,
        "year_range": 3,
        "default_hourly_rate": 30.65,
        "hourly_rate_variation_percent": 10,
        "vacation_probability": 0.15,
    }

    def transform(self, report: AttendanceReport) -> AttendanceReport:
        if report is None or not report.rows:
            raise ValueError("Cannot transform an empty report.")

        self.source_report = report
        self.settings = self._get_settings()

        self.constraints = self._analyze_constraints(report)

        year, month = self._generate_period(report)

        rows = self._generate_rows(year, month)

        summary = self._generate_summary(rows, report)

        result = AttendanceReport(
            report_type=report.report_type,
            rows=rows,
            summary=summary,
            employee_card=self._generate_employee_card(),
            title=f"Employee Timesheet - {calendar.month_name[month]} {year}"
        )

        self._validate_result(result, year, month)

        return result

    def _get_settings(self) -> Dict[str, Any]:
        if hasattr(self.config, "get_section"):
            configured = self.config.get_section("synthetic_data")
        elif isinstance(self.config, dict):
            configured = self.config.get("synthetic_data", {})
        else:
            configured = {}

        settings = self.DEFAULT_SETTINGS.copy()
        settings.update(configured or {})

        return settings

    def _analyze_constraints(self, report: AttendanceReport) -> Dict[str, Any]:
        valid_rows = [
            row for row in report.rows
            if row.clock_in and row.clock_out
        ]

        if not valid_rows:
            raise ValueError(
                "Cannot generate Type B report: "
                "source report has no valid working hours."
            )

        starts = []
        ends = []
        durations = []

        for row in valid_rows:
            start = self._time_to_minutes(row.clock_in)
            end = self._time_to_minutes(row.clock_out)

            if end <= start:
                continue

            starts.append(start)
            ends.append(end)
            durations.append(end - start)

        if not starts:
            raise ValueError("No valid shifts found in source report.")

        tolerance_start = self.settings["start_tolerance_minutes"]
        tolerance_end = self.settings["end_tolerance_minutes"]
        tolerance_duration = self.settings["duration_tolerance_minutes"]

        return {
            "min_start": max(0, min(starts) - tolerance_start),
            "max_start": min(1439, max(starts) + tolerance_start),
            "min_end": max(1, min(ends) - tolerance_end),
            "max_end": min(1440, max(ends) + tolerance_end),
            "min_duration": max(1, min(durations) - tolerance_duration),
            "max_duration": max(durations) + tolerance_duration,
        }

    def _generate_period(self, report: AttendanceReport) -> Tuple[int, int]:
        current_year = datetime.now().year
        year_range = self.settings["year_range"]

        source_period = self._get_source_period(report)

        possible_periods = []

        for year in range(current_year, current_year + year_range + 1):
            for month in range(1, 13):
                if source_period == (year, month):
                    continue

                possible_periods.append((year, month))

        if not possible_periods:
            raise ValueError("Could not generate a new reporting period.")

        return random.choice(possible_periods)

    def _get_source_period(self, report: AttendanceReport):
        if report.title:
            import re

            match = re.search(
                r"(January|February|March|April|May|June|July|"
                r"August|September|October|November|December)\s+(\d{4})",
                report.title,
                re.IGNORECASE
            )

            if match:
                month_number = list(calendar.month_name).index(
                    match.group(1).capitalize()
                )
                return int(match.group(2)), month_number

        for row in report.rows:
            if row.date:
                try:
                    parsed = self._parse_date(row.date)
                    return parsed.year, parsed.month
                except ValueError:
                    continue

        return None

    def _generate_rows(self, year: int, month: int) -> List[AttendanceRow]:
        days_in_month = calendar.monthrange(year, month)[1]

        # All days except Saturdays can potentially be working days.
        possible_working_days = [
            day
            for day in range(1, days_in_month + 1)
            if date(year, month, day).weekday() != 5
        ]

        # Choose only 3 or 4 additional vacation days.
        vacation_days_count = min(
            random.randint(3, 4),
            max(0, len(possible_working_days) - 1)
        )

        vacation_days = set(
            random.sample(possible_working_days, vacation_days_count)
        )

        rows = []

        for day in range(1, days_in_month + 1):
            current_date = date(year, month, day)

            date_string = current_date.strftime("%d/%m/%y")
            weekday_string = current_date.strftime("%A")

            # Saturday is always a day off.
            if current_date.weekday() == 5:
                rows.append(
                    self._create_day_off_row(
                        date_string,
                        weekday_string
                    )
                )
                continue

            # Only 3-4 additional days off.
            if day in vacation_days:
                rows.append(
                    self._create_day_off_row(
                        date_string,
                        weekday_string
                    )
                )
                continue

            # Generate a working day.
            clock_in, clock_out, total_hours = self._generate_shift()

            rows.append(
                AttendanceRow(
                    date=date_string,
                    day_of_week=weekday_string,
                    clock_in=clock_in,
                    clock_out=clock_out,
                    total_hours=total_hours,
                    notes=None,
                    is_missing_punch=False,
                    is_overtime_hazard=False
                )
            )

        return rows

    def _create_day_off_row(
        self,
        date_string: str,
        weekday_string: str
    ) -> AttendanceRow:
        return AttendanceRow(
            date=date_string,
            day_of_week=weekday_string,
            clock_in="-",
            clock_out="-",
            total_hours=0.0,
            notes=None,
            is_missing_punch=False,
            is_overtime_hazard=False
        )

    def _generate_shift(self) -> Tuple[str, str, float]:
        interval = self.settings["time_interval_minutes"]

        min_start = self.constraints["min_start"]
        max_start = self.constraints["max_start"]

        min_end = self.constraints["min_end"]
        max_end = self.constraints["max_end"]

        min_duration = self.constraints["min_duration"]
        max_duration = self.constraints["max_duration"]

        possible_shifts = []

        first_start = (
            (min_start + interval - 1) // interval
        ) * interval

        last_start = (max_start // interval) * interval

        for start in range(first_start, last_start + 1, interval):
            for duration in range(
                ((min_duration + interval - 1) // interval) * interval,
                (max_duration // interval) * interval + 1,
                interval
            ):
                end = start + duration

                if min_end <= end <= max_end and end <= 1440:
                    possible_shifts.append((start, end))

        if not possible_shifts:
            raise ValueError(
                "No valid shifts can be generated from source constraints."
            )

        start, end = random.choice(possible_shifts)

        clock_in = self._minutes_to_time(start)
        clock_out = self._minutes_to_time(end)

        total_hours = round((end - start) / 60, 2)

        return clock_in, clock_out, total_hours

    def _generate_summary(
        self,
        rows: List[AttendanceRow],
        source_report: AttendanceReport
    ) -> ReportSummary:

        working_rows = [
            row for row in rows
            if row.clock_in not in (None, "-")
            and row.clock_out not in (None, "-")
        ]

        total_working_days = len(working_rows)

        total_monthly_hours = round(
            sum(row.total_hours for row in working_rows),
            2
        )

        source_rate = 0.0

        if source_report.summary:
            source_rate = source_report.summary.hourly_rate

        if source_rate <= 0:
            source_rate = self.settings["default_hourly_rate"]

        variation = self.settings["hourly_rate_variation_percent"] / 100

        hourly_rate = round(
            source_rate * random.uniform(1 - variation, 1 + variation),
            2
        )

        total_payment = round(
            total_monthly_hours * hourly_rate,
            2
        )

        return ReportSummary(
            total_working_days=total_working_days,
            total_monthly_hours=total_monthly_hours,
            hourly_rate=hourly_rate,
            total_payment=total_payment
        )

    def _generate_employee_card(self) -> str:
        return f"{random.randint(10, 99)}-{random.randint(0, 999):03d}"

    def _validate_result(
        self,
        report: AttendanceReport,
        year: int,
        month: int
    ) -> None:

        expected_days = calendar.monthrange(year, month)[1]

        if len(report.rows) != expected_days:
            raise ValueError(
                "Generated report does not contain all days of the month."
            )

        seen_dates = set()
        working_days = 0
        total_hours = 0.0

        interval = self.settings["time_interval_minutes"]

        for row in report.rows:
            parsed_date = self._parse_date(row.date)

            if parsed_date.year != year or parsed_date.month != month:
                raise ValueError("Generated row has an incorrect date.")

            if parsed_date in seen_dates:
                raise ValueError("Duplicate date found.")

            seen_dates.add(parsed_date)

            if row.day_of_week != parsed_date.strftime("%A"):
                raise ValueError("Incorrect weekday.")

            if parsed_date.weekday() == 5:
                if row.clock_in != "-" or row.clock_out != "-":
                    raise ValueError("Saturday must be a day off.")

            is_day_off = row.clock_in == "-" and row.clock_out == "-"

            if is_day_off:
                if row.total_hours != 0:
                    raise ValueError("Day off must have zero working hours.")
                continue

            if not row.clock_in or not row.clock_out:
                raise ValueError("Working day has missing punch.")

            start = self._time_to_minutes(row.clock_in)
            end = self._time_to_minutes(row.clock_out)

            if start % interval != 0 or end % interval != 0:
                raise ValueError("Generated time does not match interval.")

            if end <= start:
                raise ValueError("Clock out must be after clock in.")

            calculated_hours = round((end - start) / 60, 2)

            if abs(calculated_hours - row.total_hours) > 0.01:
                raise ValueError("Incorrect total hours in row.")

            working_days += 1
            total_hours += row.total_hours

        if working_days != report.summary.total_working_days:
            raise ValueError("Working days summary does not match rows.")

        if round(total_hours, 2) != report.summary.total_monthly_hours:
            raise ValueError("Monthly hours summary does not match rows.")

        expected_payment = round(
            report.summary.total_monthly_hours *
            report.summary.hourly_rate,
            2
        )

        if abs(expected_payment - report.summary.total_payment) > 0.01:
            raise ValueError("Incorrect total payment.")

    @staticmethod
    def _parse_date(value: str) -> date:
        for fmt in ("%d/%m/%y", "%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue

        raise ValueError(f"Unsupported date format: {value}")

    @staticmethod
    def _time_to_minutes(value: str) -> int:
        parsed = datetime.strptime(value, "%H:%M")
        return parsed.hour * 60 + parsed.minute

    @staticmethod
    def _minutes_to_time(value: int) -> str:
        hours, minutes = divmod(value, 60)
        return f"{hours:02d}:{minutes:02d}"
