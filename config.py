import json
from pathlib import Path
from typing import Any, Dict

class ConfigManager:
    """
    Centralized configuration manager to load and provide access to system settings.
    """
    _instance = None
    _config_data: Dict[str, Any] = {}

    def __new__(cls, config_path: str = "config.json"):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._load_config(config_path)
        return cls._instance

    def _load_config(self, config_path: str) -> None:
        path = Path(config_path)
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self._config_data = json.load(f)
            except Exception as e:
                print(f"[WARNING] Failed to load config file: {e}. Using defaults.")
                self._config_data = {}
        else:
            self._config_data = {
                "default_hourly_rate": 30.65,
                "default_employee_card": "22-090",
                "default_break_duration": "00:30"
            }

    def get(self, key: str, default: Any = None) -> Any:
        return self._config_data.get(key, default)

config = ConfigManager()