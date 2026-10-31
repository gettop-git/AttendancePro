from typing import Dict, Type
import logging
from parsers.base_parser import BaseParser
from parsers.type_a_parser import TypeAParser
from parsers.type_b_parser import TypeBParser
from domain.exceptions import AttendanceSystemError

# Logger setup for the parser factory module
logger = logging.getLogger(__name__)


class ParserFactory:
    """
    Factory class responsible for instantiating concrete parsers.
    Uses a mapping registry to encapsulate parser creation without conditional branching,
    incorporating structured logging and error handling.
    """

    # Internal registry mapping file type identifiers to their concrete parser classes
    _PARSERS: Dict[str, Type[BaseParser]] = {
        "type_a": TypeAParser,
        "type_b": TypeBParser,
    }

    @classmethod
    def get_parser(cls, file_type: str) -> BaseParser:
        """
        Retrieves and instantiates the appropriate parser instance based on the given file type safely.

        :param file_type: String identifier representing the file format (e.g., 'type_a', 'type_b').
        :return: An instance inheriting from BaseParser.
        :raises ValueError: If the requested parser type is not supported in the registry.
        """
        try:
            logger.info(f"Requesting parser instance for file type: '{file_type}'")

            if not file_type:
                logger.error("File type parameter is empty or None.")
                raise AttendanceSystemError("File type cannot be empty.")

            normalized_type = file_type.lower().strip()
            parser_cls = cls._PARSERS.get(normalized_type)

            if not parser_cls:
                error_msg = f"Unsupported parser type: {file_type}"
                logger.error(error_msg)
                raise ValueError(error_msg)

            logger.debug(f"Successfully instantiated parser for type: {normalized_type}")
            return parser_cls()

        except (ValueError, AttendanceSystemError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error in ParserFactory for file type '{file_type}': {e}", exc_info=True)
            raise AttendanceSystemError(f"Parser factory failed to instantiate parser for {file_type}: {e}") from e