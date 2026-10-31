import logging
from domain.models import AttendanceReport
from domain.exceptions import AttendanceSystemError, TransformationStrategyError
from transformation.type_a_strategy import TypeATransformationStrategy
from transformation.type_b_strategy import TypeBTransformationStrategy

# Logger setup for the transformation service module
logger = logging.getLogger(__name__)


class TransformationService:
    """
    Service responsible for selecting the correct transformation strategy
    based on the report type and executing it without breaking the immutability contract,
    while ensuring structured logging and robust error handling.
    """

    def __init__(self) -> None:
        """
        Initializes the service by registering the available transformation strategies.
        """
        self._strategies = {
            "Type A": TypeATransformationStrategy(),
            "Type B": TypeBTransformationStrategy(),
        }
        logger.debug("TransformationService initialized with Type A and Type B strategies.")

    def transform(self, report: AttendanceReport) -> AttendanceReport:
        """
        Selects the appropriate strategy based on the report type, executes the transformation,
        and logs success or handles errors securely.
        """
        try:
            # Validate input report existence and report type
            if report is None:
                logger.error("Attempted to transform a None report object.")
                raise AttendanceSystemError("Report object cannot be None.")

            logger.info(f"Selecting strategy for report type: {report.report_type}")
            strategy = self._strategies.get(report.report_type)

            if not strategy:
                error_msg = f"Unsupported report type for transformation: {report.report_type}"
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Delegate transformation to the selected strategy
            transformed_report = strategy.transform(report)
            logger.info(f"Successfully processed report of type: {report.report_type}")

            return transformed_report

        except AttendanceSystemError as ase:
            logger.warning(f"Business system error during transformation service execution: {ase}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in TransformationService: {e}", exc_info=True)
            raise TransformationStrategyError(f"Transformation service failed: {e}") from e