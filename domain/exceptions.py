class AttendanceSystemError(Exception):
    """Base exception for all attendance system errors."""
    pass


class InvalidReportDataError(AttendanceSystemError):
    """Raised when report data, summary metrics, or rows are invalid or malformed."""
    pass


class TransformationStrategyError(AttendanceSystemError):
    """Raised when an attendance transformation strategy fails to process a report."""
    pass