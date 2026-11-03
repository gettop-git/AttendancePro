import calendar
import logging
import random

from datetime import date, datetime
from typing import Any

from domain.models import AttendanceReport, AttendanceRow, ReportSummary
from domain.exceptions import (
    TransformationStrategyError,
    InvalidReportDataError,
)
from transformation.base_strategy import BaseTransformationStrategy
from config import DEFAULT_CONFIG


logger = logging.getLogger(__name__)


class TypeATransformationStrategy(BaseTransformationStrategy):
    """
    Generates independent synthetic attendance reports for Type A.

    Source data is used only to derive reasonable constraints.
    Generated dates, shifts and employee details are independent.
    """

    def transform(self, report: AttendanceReport) -> AttendanceReport:
        try:
            if report is None or not report.rows:
                raise InvalidReportDataError(
                    "Source report is empty or missing."
                )

            logger.info("Starting Type A transformation.")

            rng = random.Random()
            settings = self._get_settings()

            constraints = self._analyze_constraints(
                report,
                settings,
            )

            year, month = self._generate_period(
                report,
                rng,
                settings,
            )

            new_rows = self._generate_rows(
                constraints=constraints,
                year=year,
                month=month,
                rng=rng,
                settings=settings,
            )

            new_summary = self._generate_summary(new_rows)

            new_report = AttendanceReport(
                report_type=report.report_type,
                rows=new_rows,
                summary=new_summary,
                employee_card=self._generate_employee_card(
                    year,
                    rng,
                ),
                title=f"Attendance Report - {month:02d}/{year}",
            )

            self._validate_result(new_report, settings)

            logger.info(
                "Type A transformation completed successfully. "
                "Generated %s working days.",
                len(new_rows),
            )

            return new_report

        except (InvalidReportDataError, TransformationStrategyError):
            raise

        except Exception as error:
            logger.exception("Type A transformation failed.")
            raise TransformationStrategyError(
                f"Type A transformation failed: {error}"
            ) from error

    # ---------------------------------------------------------
    # Configuration
    # ---------------------------------------------------------

    def _get_settings(self) -> dict[str, Any]:
        settings = dict(DEFAULT_CONFIG["synthetic_data"])

        if hasattr(self.config, "get_section"):
            configured = self.config.get_section("synthetic_data")
        else:
            configured = self.config.get("synthetic_data", {})

        if isinstance(configured, dict):
            settings.update(configured)

        return settings

    # ---------------------------------------------------------
    # Source analysis
    # ---------------------------------------------------------

    def _analyze_constraints(
        self,
        report: AttendanceReport,
        settings: dict[str, Any],
    ) -> dict[str, Any]:

        valid_rows = [
            row for row in report.rows
            if row.clock_in and row.clock_out
        ]

        if not valid_rows:
            raise InvalidReportDataError(
                "No valid attendance records were found."
            )

        starts = []
        ends = []
        durations = []
        breaks = []
        locations = []

        source_has_saturday_work = False

        for row in valid_rows:
            try:
                start = self._time_to_minutes(row.clock_in)
                end = self._time_to_minutes(row.clock_out)

                if end <= start:
                    logger.warning(
                        "Ignoring invalid time range: %s - %s",
                        row.clock_in,
                        row.clock_out,
                    )
                    continue

                break_minutes = (
                    self._duration_to_minutes(row.break_duration)
                    if row.break_duration
                    else self._duration_to_minutes(
                        settings["default_break_duration"]
                    )
                )

                net_minutes = end - start - break_minutes

                if net_minutes <= 0:
                    continue

                starts.append(start)
                ends.append(end)
                durations.append(net_minutes)
                breaks.append(break_minutes)

                if row.location:
                    locations.append(row.location)

                if row.saturday_hours > 0:
                    source_has_saturday_work = True
                elif row.date and self._is_saturday(row.date):
                    source_has_saturday_work = True

            except (ValueError, TypeError):
                logger.warning(
                    "Ignoring invalid source row: %s",
                    row.date,
                )

        if not durations:
            raise InvalidReportDataError(
                "Could not derive valid attendance constraints."
            )

        start_tolerance = int(
            settings["start_tolerance_minutes"]
        )
        end_tolerance = int(
            settings["end_tolerance_minutes"]
        )
        duration_tolerance = int(
            settings["duration_tolerance_minutes"]
        )
        break_tolerance = int(
            settings["break_tolerance_minutes"]
        )

        min_start = max(0, min(starts) - start_tolerance)
        max_start = min(1439, max(starts) + start_tolerance)

        min_end = max(0, min(ends) - end_tolerance)
        max_end = min(1439, max(ends) + end_tolerance)

        min_duration = max(
            1,
            min(durations) - duration_tolerance,
        )
        max_duration = max(durations) + duration_tolerance

        min_break = max(
            0,
            min(breaks) - break_tolerance,
        )
        max_break = max(breaks) + break_tolerance

        if not locations:
            raise InvalidReportDataError(
                "No valid work locations were found in the source."
            )

        return {
            "min_start": min_start,
            "max_start": max_start,
            "min_end": min_end,
            "max_end": max_end,
            "min_duration": min_duration,
            "max_duration": max_duration,
            "min_break": min_break,
            "max_break": max_break,
            "has_saturday_work": source_has_saturday_work,
            "locations": list(set(locations)),
        }

    # ---------------------------------------------------------
    # Reporting period
    # ---------------------------------------------------------

    @staticmethod
    def _generate_period(
        report: AttendanceReport,
        rng: random.Random,
        settings: dict[str, Any],
    ) -> tuple[int, int]:

        current_year = date.today().year
        year_range = int(settings["year_range"])

        source_period = None

        if report.title:
            import re

            match = re.search(
                r"([A-Za-z]+)\s+(\d{4})",
                report.title,
            )

            if match:
                try:
                    source_month = datetime.strptime(
                        match.group(1),
                        "%B",
                    ).month
                    source_period = (
                        int(match.group(2)),
                        source_month,
                    )
                except ValueError:
                    logger.warning(
                        f"Could not read the source period from title: {report.title!r}"
                    )

        possible_periods = [
            (year, month)
            for year in range(
                current_year,
                current_year + year_range + 1,
            )
            for month in range(1, 13)
            if (year, month) != source_period
        ]

        if not possible_periods:
            raise InvalidReportDataError(
                "Could not generate a new reporting period."
            )

        return rng.choice(possible_periods)

    # ---------------------------------------------------------
    # Working days
    # ---------------------------------------------------------

    def _generate_rows(
        self,
        constraints: dict[str, Any],
        year: int,
        month: int,
        rng: random.Random,
        settings: dict[str, Any],
    ) -> list[AttendanceRow]:

        days_in_month = calendar.monthrange(year, month)[1]

        eligible_dates = [
            datetime(year, month, day)
            for day in range(1, days_in_month + 1)
            if (
                datetime(year, month, day).weekday() != 5
                or constraints["has_saturday_work"]
            )
        ]

        min_days = int(settings["min_working_days"])
        max_days = int(settings["max_working_days"])

        if min_days < 1 or max_days < min_days:
            raise InvalidReportDataError(
                "Invalid working-day configuration."
            )

        max_days = min(max_days, len(eligible_dates))

        if min_days > max_days:
            raise InvalidReportDataError(
                "Not enough eligible dates in the generated month."
            )

        logger.debug(f"min_days: {min_days}")
        logger.debug(f"max_days: {max_days}")

        working_days_count = rng.randint(min_days, max_days)

        logger.debug(f"selected working days: {working_days_count}")

        selected_dates = sorted(
            rng.sample(eligible_dates, working_days_count)
        )

        rows = []

        for date_obj in selected_dates:
            shift = self._generate_shift(
                constraints,
                rng,
                settings,
            )

            net_hours = shift["total_hours"]
            is_saturday = date_obj.weekday() == 5

            if is_saturday:
                regular = 0.0
                overtime_125 = 0.0
                overtime_150 = 0.0
                saturday_hours = net_hours
            else:
                regular, overtime_125, overtime_150 = (
                    self._calculate_overtime(net_hours)
                )
                saturday_hours = 0.0

            rows.append(
                AttendanceRow(
                    date=date_obj.strftime("%d/%m/%Y"),
                    day_of_week=date_obj.strftime("%A"),
                    location=rng.choice(
                        constraints["locations"]
                    ),
                    clock_in=shift["clock_in"],
                    clock_out=shift["clock_out"],
                    break_duration=shift["break_duration"],
                    total_hours=net_hours,
                    overtime_100=regular,
                    overtime_125=overtime_125,
                    overtime_150=overtime_150,
                    saturday_hours=saturday_hours,
                    is_missing_punch=False,
                    is_overtime_hazard=False,
                )
            )

        return rows

    # ---------------------------------------------------------
    # Shift generation
    # ---------------------------------------------------------

    def _generate_shift(
            self,
            constraints: dict[str, Any],
            rng: random.Random,
            settings: dict[str, Any],
    ) -> dict[str, Any]:

        interval = int(settings["time_interval_minutes"])
        max_attempts = int(settings["max_generation_attempts"])

        min_start = (
                            (constraints["min_start"] + interval - 1)
                            // interval
                    ) * interval

        max_start = (
                            constraints["max_start"] // interval
                    ) * interval

        min_duration = (
                               (constraints["min_duration"] + interval - 1)
                               // interval
                       ) * interval

        max_duration = (
                               constraints["max_duration"] // interval
                       ) * interval

        min_break = (
                            (constraints["min_break"] + interval - 1)
                            // interval
                    ) * interval

        max_break = (
                            constraints["max_break"] // interval
                    ) * interval

        if min_start > max_start:
            raise InvalidReportDataError(
                f"No valid start times in {interval}-minute intervals."
            )

        if min_duration > max_duration:
            raise InvalidReportDataError(
                f"No valid durations in {interval}-minute intervals."
            )

        if min_break > max_break:
            raise InvalidReportDataError(
                f"No valid breaks in {interval}-minute intervals."
            )

        for _ in range(max_attempts):

            start = rng.randrange(
                min_start,
                max_start + 1,
                interval,
            )

            duration = rng.randrange(
                min_duration,
                max_duration + 1,
                interval,
            )

            break_minutes = rng.randrange(
                min_break,
                max_break + 1,
                interval,
            )

            end = start + duration + break_minutes

            if not (
                    constraints["min_end"]
                    <= end
                    <= constraints["max_end"]
            ):
                continue

            if end >= 24 * 60:
                continue

            return {
                "clock_in": self._minutes_to_time(start),
                "clock_out": self._minutes_to_time(end),
                "break_duration": self._minutes_to_duration(
                    break_minutes
                ),
                "total_hours": round(duration / 60, 2),
            }

        raise InvalidReportDataError(
            f"Could not generate a valid {interval}-minute shift."
        )

    # ---------------------------------------------------------
    # Overtime
    # ---------------------------------------------------------

    @staticmethod
    def _calculate_overtime(
        total_hours: float,
    ) -> tuple[float, float, float]:
        """
        TEMPORARY allocation.

        Until the actual Type A overtime rules are supplied,
        weekday hours are classified as 100%.

        Saturday hours are handled separately in _generate_rows.
        """

        return round(total_hours, 2), 0.0, 0.0

    # ---------------------------------------------------------
    # Summary
    # ---------------------------------------------------------

    @staticmethod
    def _generate_summary(
        rows: list[AttendanceRow],
    ) -> ReportSummary:

        return ReportSummary(
            total_working_days=len(
                [row for row in rows if row.total_hours > 0]
            ),
            total_monthly_hours=round(
                sum(row.total_hours for row in rows),
                2,
            ),
            total_100_hours=round(
                sum(row.overtime_100 for row in rows),
                2,
            ),
            total_125_hours=round(
                sum(row.overtime_125 for row in rows),
                2,
            ),
            total_150_hours=round(
                sum(row.overtime_150 for row in rows),
                2,
            ),
            bonus=0.0,
            travel=0.0,
            hourly_rate=0.0,
            total_payment=0.0,
        )

    # ---------------------------------------------------------
    # Employee identification
    # ---------------------------------------------------------

    @staticmethod
    def _generate_employee_card(
        year: int,
        rng: random.Random,
    ) -> str:

        return f"{year % 100:02d}-{rng.randint(0, 999):03d}"

    # ---------------------------------------------------------
    # Validation
    # ---------------------------------------------------------

    def _validate_result(
        self,
        report: AttendanceReport,
        settings: dict[str, Any],
    ) -> None:

        tolerance = settings["rounding_tolerance"]

        if not report.rows:
            raise InvalidReportDataError(
                "Generated report contains no working days."
            )

        seen_dates = set()

        for row in report.rows:

            if row.date in seen_dates:
                raise InvalidReportDataError(
                    f"Duplicate attendance date: {row.date}"
                )

            seen_dates.add(row.date)

            if row.total_hours <= 0:
                raise InvalidReportDataError(
                    "Generated working row has invalid hours."
                )

            start = self._time_to_minutes(row.clock_in)
            end = self._time_to_minutes(row.clock_out)
            break_minutes = self._duration_to_minutes(
                row.break_duration
            )

            calculated_minutes = end - start - break_minutes
            calculated_hours = round(
                calculated_minutes / 60,
                2,
            )

            if calculated_minutes <= 0:
                raise InvalidReportDataError(
                    f"Invalid shift on {row.date}."
                )

            if abs(calculated_hours - row.total_hours) > tolerance:
                raise InvalidReportDataError(
                    f"Time calculation mismatch on {row.date}."
                )

            parts = (
                row.overtime_100
                + row.overtime_125
                + row.overtime_150
                + row.saturday_hours
            )

            if abs(parts - row.total_hours) > tolerance:
                raise InvalidReportDataError(
                    f"Overtime calculation mismatch on {row.date}."
                )

        summary = report.summary

        if summary is None:
            raise InvalidReportDataError(
                "Generated report has no summary."
            )

        actual_hours = round(
            sum(row.total_hours for row in report.rows),
            2,
        )

        if abs(
            actual_hours - summary.total_monthly_hours
        ) > tolerance:
            raise InvalidReportDataError(
                "Monthly total does not match attendance rows."
            )

        actual_days = len(
            [row for row in report.rows if row.total_hours > 0]
        )

        if actual_days != summary.total_working_days:
            raise InvalidReportDataError(
                "Working-day count does not match attendance rows."
            )

    # ---------------------------------------------------------
    # Date and time helpers
    # ---------------------------------------------------------

    @staticmethod
    def _time_to_minutes(value: str) -> int:
        parsed = datetime.strptime(value.strip(), "%H:%M")
        return parsed.hour * 60 + parsed.minute

    @staticmethod
    def _minutes_to_time(value: int) -> str:
        hours, minutes = divmod(value, 60)

        if hours >= 24:
            raise ValueError("Time exceeds one day.")

        return f"{hours:02d}:{minutes:02d}"

    @staticmethod
    def _duration_to_minutes(value: str) -> int:
        hours, minutes = map(int, value.strip().split(":"))

        if hours < 0 or not 0 <= minutes < 60:
            raise ValueError(
                f"Invalid duration: {value}"
            )

        return hours * 60 + minutes

    @staticmethod
    def _minutes_to_duration(value: int) -> str:
        hours, minutes = divmod(value, 60)
        return f"{hours:02d}:{minutes:02d}"

    @staticmethod
    def _is_saturday(date_str: str) -> bool:

        for date_format in (
            "%d/%m/%Y",
            "%d/%m/%y",
            "%Y-%m-%d",
        ):
            try:
                date_obj = datetime.strptime(
                    date_str.strip(),
                    date_format,
                )
                return date_obj.weekday() == 5

            except ValueError:
                continue

        raise ValueError(
            f"Unsupported date format: {date_str}"
        )