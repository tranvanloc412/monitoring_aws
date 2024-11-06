import logging
import yaml
from typing import Dict, Optional, Union
from pathlib import Path
from utils.utils import load_yaml

logger = logging.getLogger(__name__)


class ThresholdConfig:
    _threshold_configs: Dict[str, Dict[str, int]] = {}

    def __init__(self, file_path: Union[str, Path]):
        if not self._threshold_configs:
            self._load_threshold_configs(file_path)

    @classmethod
    def _load_threshold_configs(cls, file_path: Union[str, Path]) -> None:
        if cls._threshold_configs:
            logger.debug("Threshold Configs already loaded.")
            return

        try:
            data = load_yaml(file_path)
            cls._threshold_configs = {
                f"{resource['resource_type']}_{category}": {
                    metric_name: threshold
                    for metric_name, threshold in resource["thresholds"].items()
                }
                for category, resources in data.items()
                for resource in resources
            }
            logger.info(
                f"Loaded {len(cls._threshold_configs)} threshold configurations."
            )
            logger.info(f"Threshold Configurations loaded: {cls._threshold_configs}")
        except (FileNotFoundError, yaml.YAMLError) as e:
            logger.error(f"Error loading thresholds: {e}")

    @classmethod
    def get_cat_thresholds(
        cls, category: str, resource_type: str
    ) -> Optional[Dict[str, int]]:
        key = f"{resource_type}_{category}"
        threshold = cls._threshold_configs.get(key, {})

        if not threshold:
            logger.info(
                f"No thresholds found for resource '{resource_type}' in category '{category}'."
            )

        return threshold
