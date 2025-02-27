import logging
from pathlib import Path
from typing import Dict, List, Any

from .alarm_config import AlarmDefinition, Metric
from utils import load_yaml

logger = logging.getLogger(__name__)


class ConfigLoader:
    def __init__(
        self,
        alarm_config_path: Path,
        category_config_path: Path,
        custom_config_path: Path,
    ):
        self.alarm_configs = self.load_alarm_configs(alarm_config_path)
        self.category_configs = self.load_category_configs(category_config_path)
        self.custom_configs = self.load_custom_configs(custom_config_path)

    @staticmethod
    def load_alarm_configs(path: Path) -> Dict[str, List[AlarmDefinition]]:
        """Load alarm configurations from YAML file."""
        try:
            data = load_yaml(path)
            alarm_configs = {
                resource_type: [
                    AlarmDefinition(
                        metric=Metric(
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
            logger.error(f"Error loading alarm configs from {path}: {e}")
            raise

    @staticmethod
    def load_category_configs(path: Path) -> Dict[str, Dict[str, Any]]:
        """Load category configurations from YAML file."""
        try:
            return load_yaml(path)
        except Exception as e:
            logger.error(f"Error loading category configs from {path}: {e}")
            raise

    @staticmethod
    def load_custom_configs(path: Path) -> Dict[str, Any]:
        """Load custom configurations from YAML file."""
        try:
            return load_yaml(path)
        except Exception as e:
            logger.error(f"Error loading custom configs from {path}: {e}")
            raise
