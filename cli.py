import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# Single source of defaults. config.json overrides any of these values.
DEFAULT_CONFIG = {
    "synthetic_data": {
        "enabled": True,
        # Working days and period
        "min_working_days": 10,
        "max_working_days": 22,
        "year_range": 3,
        # Shift generation
        "start_tolerance_minutes": 15,
        "end_tolerance_minutes": 30,
        "duration_tolerance_minutes": 30,
        "break_tolerance_minutes": 0,
        "default_break_duration": "00:30",
        "time_interval_minutes": 15,
        "max_generation_attempts": 500,
        # Type B: pay variation and vacation days
        "hourly_rate_variation_percent": 10,
        "vacation_days_min": 3,
        "vacation_days_max": 4,
        # Validation
        "rounding_tolerance": 0.01,
    }
}


class ConfigManager:
    """Loads, validates and provides access to system configuration."""

    def __init__(self, config_path: str | None = None):
        self.config_path = (
            Path(config_path)
            if config_path
            else Path(__file__).resolve().parent / "config.json"
        )

        self._config_data = self._load_config()

    def _load_config(self) -> dict[str, Any]:
        if not self.config_path.exists():
            logger.info("Configuration file not found. Using defaults.")
            return DEFAULT_CONFIG.copy()

        try:
            with self.config_path.open("r", encoding="utf-8") as file:
                loaded_config = json.load(file)

            if not isinstance(loaded_config, dict):
                raise ValueError("Configuration must be a JSON object.")

            return self._merge_with_defaults(loaded_config)

        except (json.JSONDecodeError, OSError, ValueError) as error:
            logger.warning(
                "Failed to load configuration: %s. Using defaults.",
                error,
            )
            return DEFAULT_CONFIG.copy()

    @staticmethod
    def _merge_with_defaults(
        loaded_config: dict[str, Any],
    ) -> dict[str, Any]:
        config = DEFAULT_CONFIG.copy()

        for key, value in loaded_config.items():
            if (
                isinstance(value, dict)
                and isinstance(config.get(key), dict)
            ):
                config[key] = {**config[key], **value}
            else:
                config[key] = value

        return config

    def get(self, key: str, default: Any = None) -> Any:
        return self._config_data.get(key, default)

    def get_section(self, section: str) -> dict[str, Any]:
        value = self._config_data.get(section, {})
        return value.copy() if isinstance(value, dict) else {}


config = ConfigManager()