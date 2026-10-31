from datetime import datetime, timedelta
from typing import List
import random
import logging
from domain.models import AttendanceReport, AttendanceRow, ReportSummary
from domain.exceptions import TransformationStrategyError, InvalidReportDataError
from transformation.base_strategy import BaseTransformationStrategy

# Logger setup for the Type B transformation strategy module
logger = logging.getLogger(__name__)


class TypeBTransformationStrategy(BaseTransformationStrategy):
    """
    Transformation strategy for Type B reports.
    Applies deep and dynamic randomization across all report fields (including employee cards,
    hourly rates, work hours, days off, and notes) to ensure unique and varied outputs on every execution.
    """

    def transform(self, report: AttendanceReport) -> AttendanceReport:
        """
        Transforms a Type B attendance report with structured logging and error handling,
        applying wide-ranging dynamic randomization across days, rows, wages, and cards.
        """
        try:
            logger.info(
                f"Starting Type B transformation for report type: {report.report_type} with employee card: {getattr(report, 'employee_card', 'N/A')}")

            # Validate input report object integrity
            if report is None:
                raise InvalidReportDataError("Report object is None for Type B transformation.")

            # Initialize random generator without a fixed seed to guarantee full variability on every run
            rng = random.Random()

            # Randomly choose a year and month for complete structural variation
            year = rng.choice([2022, 2023, 2024])
            month = rng.randint(1, 12)

            # Calculate the number of days in the randomly selected month
            if month in [1, 3, 5, 7, 8, 10, 12]:
                days_in_month = 31
            elif month in [4, 6, 9, 11]:
                days_in_month = 30
            else:
                days_in_month = 29 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 28

            new_rows: List[AttendanceRow] = []
            total_working_days = 0
            total_monthly_hours = 0.0

            # Generate rows for each day of the randomized month
            for day in range(1, days_in_month + 1):
                current_date_obj = datetime(year, month, day)
                date_str = f"{day}/{month}/{str(year)[-2:]}"
                day_of_week = current_date_obj.strftime("%A")

                is_saturday = (day_of_week == "Saturday")

                if is_saturday:
                    clock_in = None
                    clock_out = None
                    net_hours = 0.0
                    is_missing = True
                    notes = ""
                else:
                    # Dynamic randomized chance for days off or leaves
                    if rng.random() < 0.12 and day > 2:
                        clock_in = None
                        clock_out = None
                        net_hours = 0.0
                        is_missing = True
                        notes = rng.choice(["Day off", "Sick leave", "Vacation", ""])
                    else:
                        total_working_days += 1

                        # Variable and diverse morning clock-in times
                        in_hour = rng.choice([7, 8, 9, 10])
                        in_minute = rng.choice([0, 10, 15, 20, 30, 45])
                        clock_in = f"{in_hour:02d}:{in_minute:02d}"

                        # Broad variation of shift lengths (short to long shifts)
                        shift_hours = rng.choice([3.5, 4.0, 5.5, 6.0, 7.5, 8.0, 8.5, 9.0, 9.5])

                        in_dt = datetime.strptime(clock_in, "%H:%M")
                        out_dt = in_dt + timedelta(minutes=int(shift_hours * 60))
                        clock_out = out_dt.strftime("%H:%M")

                        net_hours = shift_hours
                        is_missing = False
                        notes = rng.choice(["", "", "Field work", "Office", "Client meeting", "Remote", "Project work"])

                total_monthly_hours += net_hours

                # Append generated attendance row to the list
                new_rows.append(AttendanceRow(
                    date=date_str,
                    day_of_week=day_of_week,
                    clock_in=clock_in,
                    clock_out=clock_out,
                    total_hours=round(net_hours, 2),
                    notes=notes,
                    is_missing_punch=is_missing,
                    is_overtime_hazard=False
                ))

            # --- Deep and full variation on wages, rates, and employee cards ---

            # 1. Wide and true variation on the hourly rate (changes significantly on every run)
            base_rate = report.summary.hourly_rate if (
                        report.summary and report.summary.hourly_rate > 0) else self.config.get("default_hourly_rate",
                                                                                                30.65)
            rate_variation = rng.uniform(-4.0, 12.0)
            hourly_rate = round(max(28.0, base_rate + rate_variation), 2)

            total_payment = round(total_monthly_hours * hourly_rate, 2)

            new_summary = ReportSummary(
                total_working_days=total_working_days,
                total_monthly_hours=round(total_monthly_hours, 2),
                hourly_rate=hourly_rate,
                total_payment=total_payment
            )

            # 2. True dynamic variation on the employee card (randomized dynamically on every run)
            original_card = report.employee_card if report.employee_card else self.config.get("default_employee_card",
                                                                                              "22-090")
            card_digits = "".join(filter(str.isdigit, original_card))
            if card_digits:
                base_num = int(card_digits)
                new_card_num = base_num + rng.randint(-15, 35)
                dynamic_card = f"{abs(new_card_num):02d}-{rng.randint(10, 99)}"
            else:
                dynamic_card = f"{rng.randint(10, 40)}-{rng.randint(100, 999)}"

            logger.info("Type B transformation completed successfully.")
            return AttendanceReport(
                report_type=report.report_type,
                rows=new_rows,
                summary=new_summary,
                employee_card=dynamic_card
            )

        except InvalidReportDataError as jde:
            logger.warning(f"Validation warning in Type B transformation: {jde}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during Type B transformation: {e}", exc_info=True)
            raise TransformationStrategyError(f"Type B transformation failed: {e}") from e