from pathlib import Path
import logging
from generators.base_renderer import BaseRenderer
from domain.models import AttendanceReport
from domain.exceptions import InvalidReportDataError

# Logger setup for the HTML renderer module
logger = logging.getLogger(__name__)


class HtmlRenderer(BaseRenderer):
    """
    Concrete renderer implementation for generating HTML files from an AttendanceReport.
    Provides professional CSS styling matching the exact visual layout of the original reports,
    incorporating structured logging and robust error handling.
    """

    def render(self, report: AttendanceReport, output_path: str) -> None:
        """
        Generates the HTML content and writes it to the output path safely.
        """
        try:
            logger.info(
                f"Starting HTML rendering for report type '{getattr(report, 'report_type', 'Unknown')}' to path: {output_path}")

            if report is None:
                logger.error("Attempted to render a None report object.")
                raise InvalidReportDataError("Report object cannot be None.")

            html_content = self._generate_html(report)

            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(html_content)

            logger.info(f"HTML report successfully rendered and saved to: {output_file}")

        except Exception as e:
            logger.error(f"Critical error during HTML rendering to {output_path}: {e}", exc_info=True)
            raise InvalidReportDataError(f"HTML rendering failed: {e}") from e

    def _generate_html(self, report: AttendanceReport) -> str:
        """
        Routes the HTML generation based on the report type.
        """
        try:
            if report.report_type == "Type B":
                logger.debug("Generating Type B HTML report layout.")
                return self._render_type_b(report)
            else:
                logger.debug("Generating Type A HTML report layout.")
                return self._render_type_a(report)
        except Exception as e:
            logger.error(f"Error while generating HTML content layout: {e}", exc_info=True)
            raise InvalidReportDataError(f"Failed to generate HTML content layout: {e}") from e

    def _render_type_b(self, report: AttendanceReport) -> str:
        # Extract month and year dynamically from the first row to update the title
        month_year_str = "September 2022"
        if report.rows and report.rows[0].date:
            try:
                parts = report.rows[0].date.split("/")
                if len(parts) == 3:
                    month_num = int(parts[1])
                    year_num = "20" + parts[2] if len(parts[2]) == 2 else parts[2]
                    months_map = {
                        1: "January", 2: "February", 3: "March", 4: "April",
                        5: "May", 6: "June", 7: "July", 8: "August",
                        9: "September", 10: "October", 11: "November", 12: "December"
                    }
                    month_name = months_map.get(month_num, "")
                    if month_name:
                        month_year_str = f"{month_name} {year_num}"
            except Exception:
                pass

        report_title = f"Employee Timesheet - {month_year_str}"
        employee_card = report.employee_card or "22-090"
        summary = report.summary

        summary_html = f"""
            <table class="summary-table">
                <tr>
                    <th>Total Working Days</th>
                    <th>Total Monthly Hours</th>
                    <th>Hourly Rate</th>
                    <th>Total Payment</th>
                </tr>
                <tr>
                    <td>{summary.total_working_days if summary else 0}</td>
                    <td>{summary.total_monthly_hours:.2f}</td>
                    <td>{summary.hourly_rate:.2f}</td>
                    <td class="highlight-pay">{summary.total_payment:.2f}</td>
                </tr>
            </table>
            """

        rows_html = ""
        for row in report.rows:
            clock_in = row.clock_in if row.clock_in else "-"
            clock_out = row.clock_out if row.clock_out else "-"
            total_hours = f"{row.total_hours:.2f}" if row.total_hours > 0 else "-"
            notes = row.notes if row.notes else ""

            rows_html += f"""
                <tr>
                    <td>{row.date or ''}</td>
                    <td>{row.day_of_week or ''}</td>
                    <td>{clock_in}</td>
                    <td>{clock_out}</td>
                    <td><strong>{total_hours}</strong></td>
                    <td>{notes}</td>
                </tr>
                """

        return f"""<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>{report_title}</title>
        <style>
            @page {{
                size: A4 portrait;
                margin: 8mm;
            }}
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                background-color: #ffffff;
                color: #333;
            }}
            .container {{
                width: 100%;
                background: #ffffff;
                padding: 0;
            }}
            h2 {{
                text-align: center;
                color: #1a365d;
                font-size: 18px;
                font-weight: bold;
                margin-bottom: 2px;
            }}
            h4 {{
                text-align: center;
                color: #4a5568;
                margin-top: 0;
                margin-bottom: 8px;
                font-weight: 500;
                font-size: 13px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 2px;
                margin-bottom: 8px;
            }}
            th, td {{
                border: 1px solid #dcdcdc;
                padding: 4px 6px;
                text-align: center;
                font-size: 11px;
            }}
            th {{
                background-color: #2b6cb0;
                color: white;
                font-weight: bold;
                font-size: 11px;
            }}
            .summary-table th {{
                background-color: #2b6cb0;
            }}
            .summary-table td {{
                background-color: #ffffff;
                font-weight: bold;
            }}
            tr:nth-child(even) {{
                background-color: #f7fafc;
            }}
            .highlight-pay {{
                color: #27ae60;
            }}
            tr {{
                page-break-inside: avoid;
            }}
            thead {{
                display: table-header-group;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>{report_title}</h2>
            <h4>Employee Card: {employee_card}</h4>
            {summary_html}
            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Day of Week</th>
                        <th>Clock In</th>
                        <th>Clock Out</th>
                        <th>Total Hours</th>
                        <th>Notes</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>
    </body>
    </html>"""

    def _render_type_a(self, report: AttendanceReport) -> str:
        # Extract month/year dynamically from the first valid row if possible
        month_year_str = "Timesheet"
        if report.rows and report.rows[0].date:
            try:
                parts = report.rows[0].date.split("/")
                if len(parts) == 3:
                    month_num = int(parts[1])
                    year_num = parts[2]
                    months_map = {
                        1: "January", 2: "February", 3: "March", 4: "April",
                        5: "May", 6: "June", 7: "July", 8: "August",
                        9: "September", 10: "October", 11: "November", 12: "December"
                    }
                    month_name = months_map.get(month_num, "")
                    if month_name:
                        month_year_str = f"{month_name} {year_num} Timesheet"
            except Exception:
                pass

        report_title = f"HaNesher Manpower Ltd. - {month_year_str}"
        summary = report.summary

        rows_html = ""
        for row in report.rows:
            rows_html += f"""
                <tr>
                    <td>{row.date or ''}</td>
                    <td>{row.day_of_week or ''}</td>
                    <td>{row.location or '-'}</td>
                    <td>{row.clock_in or ''}</td>
                    <td>{row.clock_out or ''}</td>
                    <td>{row.break_duration or '00:30'}</td>
                    <td>{row.total_hours:.2f}</td>
                    <td>{row.overtime_100:.2f}</td>
                    <td>{row.overtime_125:.2f}</td>
                    <td>{row.overtime_150:.2f}</td>
                    <td>{row.saturday_hours:.2f}</td>
                </tr>
                """

        summary_html = ""
        if summary:
            summary_html = f"""
                <div class="summary-box">
                    <strong>Total Days:</strong> {summary.total_working_days} &nbsp;|&nbsp; 
                    <strong>Total Hours:</strong> {summary.total_monthly_hours:.2f} &nbsp;|&nbsp; 
                    <strong>100% Hours:</strong> {summary.total_100_hours:.2f} &nbsp;|&nbsp; 
                    <strong>125% Hours:</strong> {summary.total_125_hours:.2f} &nbsp;|&nbsp; 
                    <strong>150% Hours:</strong> {summary.total_150_hours:.2f} &nbsp;|&nbsp; 
                    <strong>Bonus:</strong> {summary.bonus} &nbsp;|&nbsp; 
                    <strong>Travel:</strong> {summary.travel}
                </div>
                """

        return f"""<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>{report_title}</title>
        <style>
            @page {{
                size: A4 portrait;
                margin: 8mm;
            }}
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                background-color: #ffffff;
                color: #333;
            }}
            h2 {{
                text-align: center;
                color: #1a365d;
                font-size: 18px;
                font-weight: bold;
                margin-bottom: 10px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 5px;
                background-color: #fff;
            }}
            th, td {{
                border: 1px solid #dcdcdc;
                padding: 4px 5px;
                text-align: center;
                font-size: 10.5px;
            }}
            th {{
                background-color: #2b6cb0;
                color: white;
                font-weight: bold;
                font-size: 10.5px;
            }}
            tr:nth-child(even) {{
                background-color: #f7fafc;
            }}
            tr {{
                page-break-inside: avoid;
            }}
            thead {{
                display: table-header-group;
            }}
            .summary-box {{
                margin-top: 10px;
                text-align: center;
                font-size: 11.5px;
                color: #2d3748;
                font-weight: 500;
                page-break-inside: avoid;
            }}
        </style>
    </head>
    <body>
        <h2>{report_title}</h2>
        <table>
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Day of Week</th>
                    <th>Location</th>
                    <th>Clock In</th>
                    <th>Clock Out</th>
                    <th>Break</th>
                    <th>Total</th>
                    <th>100%</th>
                    <th>125%</th>
                    <th>150%</th>
                    <th>Saturday</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
        {summary_html}
    </body>
    </html>"""