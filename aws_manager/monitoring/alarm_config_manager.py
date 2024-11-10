import logging
from pathlib import Path
from typing import Dict, List, Any, Union
from .alarm_config import AlarmConfig, MetricConfig
from utils.utils import load_yaml

logger = logging.getLogger(__name__)


class AlarmConfigManager:
    def __init__(
        self,
        alarm_config_path: Path,
        category_config_path: Path,
        custom_config_path: Path,
    ):
        self.alarm_configs: Dict[str, List[AlarmConfig]] = {}
        self.category_configs: Dict[str, Dict[str, Any]] = {}
        self.custom_configs: Dict[str, Any] = {}

        self._load_configs(alarm_config_path, category_config_path, custom_config_path)

    def _load_configs(
        self,
        alarm_config_path: Path,
        category_config_path: Path,
        custom_config_path: Path,
    ) -> None:
        """Load all configuration files"""
        self._load_alarm_configs(alarm_config_path)
        self._load_category_configs(category_config_path)
        self._load_custom_configs(custom_config_path)

    def _load_alarm_configs(self, path: Path) -> None:
        """Load and parse alarm configurations from YAML."""
        try:
            data = load_yaml(path)
            for resource_type, configs in data.items():
                self.alarm_configs[resource_type] = [
                    AlarmConfig(
                        metric=MetricConfig(
                            name=config["metric"]["name"],
                            namespace=config["metric"]["namespace"],
                            # dimensions=config["metric"]["dimensions"],
                        ),
                        statistic=config["statistic"],
                        comparison_operator=config["comparison_operator"],
                        unit=config["unit"],
                        period=config["period"],
                        evaluation_periods=config["evaluation_periods"],
                        # name=config["name"],
                    )
                    for config in configs
                ]
        except Exception as e:
            logger.error(f"Error loading alarm configs: {e}")
            raise

    def _load_category_configs(self, path: Path) -> None:
        """Load category-specific configurations."""
        try:
            self.category_configs = load_yaml(path)
        except Exception as e:
            logger.error(f"Error loading category configs: {e}")
            raise

    def _load_custom_configs(self, path: Path) -> None:
        """Load custom alarm configurations."""
        try:
            self.custom_configs = load_yaml(path)
        except Exception as e:
            logger.error(f"Error loading custom configs: {e}")
            raise

    def get_category_config(
        self, category: str
    ) -> Dict[str, Dict[str, Union[float, str]]]:
        """Get configurations specific to a landing zone category."""
        return self.category_configs.get(category, {})

    # def get_alarm_configs(self, resource_type: str) -> List[AlarmConfigs]:
    #     """Get alarm configurations for a specific resource type."""
    #     return self.alarm_configs.get(resource_type, [])
