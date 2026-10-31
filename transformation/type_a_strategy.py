from datetime import datetime, timedelta
from typing import List
import random
import logging
from domain.models import AttendanceReport, AttendanceRow, ReportSummary
from domain.exceptions import TransformationStrategyError, InvalidReportDataError
from transformation.base_strategy import BaseTransformationStrategy

# Logger setup for the transformation strategy module
logger = logging.getLogger(__name__)


class TypeATransformationStrategy(BaseTransformationStrategy):
    """
    Transformation strategy for Type A attendance reports.
    Dynamically randomizes the month, year, dates, days of the week, locations,
    and shift hours on every single execution to ensure true and varied data generation.
    """

    def _calculate_hours(self, clock_in: str, clock_out: str, break_duration: str) -> float:
        """
        Calculates net working hours based on clock-in, clock-out, and break duration.
        """
        try:
            FMT = "%H:%M"
            t_in = datetime.strptime(clock_in, FMT)
            t_out = datetime.strptime(clock_out, FMT)
            diff_seconds = (t_out - t_in).total_seconds()

            break_parts = break_duration.split(":")
            break_seconds = int(break_parts[0]) * 3600 + int(break_parts[1]) * 60

            net_seconds = max(0.0, diff_seconds - break_seconds)
            return round(net_seconds / 3600.0, 2)
        except Exception:
            return 0.0

    def transform(self, report: AttendanceReport) -> AttendanceReport:
        """
        Transforms a Type A attendance report with structured logging and error handling,
        generating dynamic rows and summaries.
        """
        try:
            logger.info(
                f"Starting Type A transformation for report type: {report.report_type} with employee card: {getattr(report, 'employee_card', 'N/A')}")

            # Validate input report object integrity
            if report is None:
                raise InvalidReportDataError("Report object is None for Type A transformation.")

            rng = random.Random()

            # Randomize target year and month for the report
            year = rng.choice([2022, 2023])
            month = rng.randint(1, 12)

            # Determine the number of days in the selected month
            if month in [1, 3, 5, 7, 8, 10, 12]:
                days_in_month = 31
            elif month in [4, 6, 9, 11]:
                days_in_month = 30
            else:
                days_in_month = 29 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 28

            new_rows: List[AttendanceRow] = []
            total_days = 0
            total_monthly_hours = 0.0
            total_100 = 0.0
            total_125 = 0.0
            total_150 = 0.0
            total_saturday = 0.0

            # Retrieve default break duration from configuration manager
            default_break = self.config.get("default_break_duration", "00:30")

            # Iterate through each day of the month to generate attendance records
            for day in range(1, days_in_month + 1):
                current_date_obj = datetime(year, month, day)
                date_str = f"{day:02d}/{month:02d}/{str(year)[-2:]}"
                day_of_week = current_date_obj.strftime("%A")

                is_saturday = (day_of_week == "Saturday")

                if is_saturday:
                    # Saturday fixed shift rules
                    clock_in = "08:00"
                    clock_out = "15:00"
                    break_dur = default_break
                    net_hours = self._calculate_hours(clock_in, clock_out, break_dur)

                    regular_hrs = 0.0
                    ot_125 = 0.0
                    ot_150 = 0.0
                    saturday_hrs = net_hours
                else:
                    total_days += 1

                    # Randomize weekday shift times
                    in_hour = rng.choice([7, 8])
                    in_minute = rng.choice([0, 15, 30, 45])
                    if in_hour == 7 and in_minute < 30:
                        in_minute = 30
                    clock_in = f"{in_hour:02d}:{in_minute:02d}"

                    shift_hours = rng.choice([7.5, 8.0, 8.5, 9.0, 9.5])

                    in_dt = datetime.strptime(clock_in, "%H:%M")
                    total_minutes = int((shift_hours + 0.5) * 60)
                    out_dt = in_dt + timedelta(minutes=total_minutes)
                    clock_out = out_dt.strftime("%H:%M")
                    break_dur = default_break

                    net_hours = self._calculate_hours(clock_in, clock_out, break_dur)

                    # Calculate overtime tiers
                    if net_hours <= 8.0:
                        regular_hrs = net_hours
                        ot_125 = 0.0
                        ot_150 = 0.0
                    elif net_hours <= 10.0:
                        regular_hrs = 8.0
                        ot_125 = round(net_hours - 8.0, 2)
                        ot_150 = 0.0
                    else:
                        regular_hrs = 8.0
                        ot_125 = 2.0
                        ot_150 = round(net_hours - 10.0, 2)

                    saturday_hrs = 0.0

                total_monthly_hours += net_hours
                total_100 += regular_hrs
                total_125 += ot_125
                total_150 += ot_150
                total_saturday += saturday_hrs

                # Append newly generated row to the rows list
                new_rows.append(AttendanceRow(
                    date=date_str,
                    day_of_week=day_of_week,
                    location=rng.choice(["Garden", "Galilion", "Sheet", "Main-Branch"]),
                    clock_in=clock_in,
                    clock_out=clock_out,
                    break_duration=break_dur,
                    total_hours=net_hours,
                    overtime_100=regular_hrs,
                    overtime_125=ot_125,
                    overtime_150=ot_150,
                    saturday_hours=saturday_hrs,
                    is_missing_punch=False,
                    is_overtime_hazard=False
                ))

            # Compile summary statistics for the report
            new_summary = ReportSummary(
                total_working_days=total_days,
                total_monthly_hours=round(total_monthly_hours, 2),
                total_100_hours=round(total_100, 2),
                total_125_hours=round(total_125, 2),
                total_150_hours=round(total_150, 2),
                bonus=report.summary.bonus if report.summary else 0.0,
                travel=report.summary.travel if report.summary else 0.0
            )

            logger.info("Type A transformation completed successfully.")
            return AttendanceReport(
                report_type=report.report_type,
                rows=new_rows,
                summary=new_summary
            )

        except InvalidReportDataError as jde:
            logger.warning(f"Validation warning in Type A transformation: {jde}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during Type A transformation: {e}", exc_info=True)
            raise TransformationStrategyError(f"Type A transformation failed: {e}") from e