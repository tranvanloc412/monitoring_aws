import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from threading import Lock
from .alarm_config import AlarmConfig, MetricConfig
from utils.utils import load_yaml

logger = logging.getLogger(__name__)


class AlarmConfigManager:
    _instance: Optional["AlarmConfigManager"] = None
    _lock = Lock()

    def __new__(cls) -> "AlarmConfigManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialize()
            return cls._instance

    def _initialize(self) -> None:
        """Initialize instance attributes with proper type hints."""
        self.alarm_configs: Dict[str, List[AlarmConfig]] = {}
        self.category_configs: Dict[str, Dict[str, Any]] = {}
        self.custom_configs: Dict[str, Any] = {}

    def load_configs(
        self,
        alarm_config_path: Path,
        category_config_path: Path,
        custom_config_path: Path,
    ) -> None:
        """
        Load all configuration files into the instance attributes.

        Args:
            alarm_config_path: Path to alarm configuration file
            category_config_path: Path to category configuration file
            custom_config_path: Path to custom configuration file

        Raises:
            FileNotFoundError: If any config file is not found
            ValueError: If config files contain invalid data
        """
        self._validate_paths(
            alarm_config_path, category_config_path, custom_config_path
        )

        if not self.alarm_configs:
            self.alarm_configs = self._load_alarm_configs(alarm_config_path)
        if not self.category_configs:
            self.category_configs = self._load_category_configs(category_config_path)
        if not self.custom_configs:
            self.custom_configs = self._load_custom_configs(custom_config_path)

    def _load_alarm_configs(self, path: Path) -> Dict[str, List[AlarmConfig]]:
        try:
            data = load_yaml(path)
            alarm_configs = {
                resource_type: [
                    AlarmConfig(
                        metric=MetricConfig(
                            name=config["metric"]["name"],
                            namespace=config["metric"]["namespace"],
                        ),
                        statistic=config["statistic"],
                        comparison_operator=config["comparison_operator"],
                        unit=config["unit"],
                        period=config["period"],
                        evaluation_periods=config["evaluation_periods"],
                    )
                    for config in configs
                ]
                for resource_type, configs in data.items()
            }
            return alarm_configs
        except Exception as e:
            logger.error(f"Error loading alarm configs: {e}")
            raise

    def _load_category_configs(self, path: Path) -> Dict[str, Dict[str, Any]]:
        try:
            return load_yaml(path)
        except Exception as e:
            logger.error(f"Error loading category configs: {e}")
            raise

    def _load_custom_configs(self, path: Path) -> Dict[str, Any]:
        try:
            return load_yaml(path)
        except Exception as e:
            logger.error(f"Error loading custom configs: {e}")
            raise

    def get_alarm_configs(self) -> Dict[str, List[AlarmConfig]]:
        return self.alarm_configs

    def get_category_configs(self) -> Dict[str, Dict[str, Any]]:
        return self.category_configs

    def get_custom_configs(self) -> Dict[str, Any]:
        return self.custom_configs

    def _validate_paths(self, *paths: Path) -> None:
        """Validate that all provided paths exist."""
        for path in paths:
            if not path.exists():
                raise FileNotFoundError(f"Config file not found: {path}")
