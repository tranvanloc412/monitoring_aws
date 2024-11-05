import logging
import yaml
from dataclasses import dataclass
from typing import Dict, List, Optional, Union
from pathlib import Path
from utils.utils import load_yaml

logger = logging.getLogger(__name__)


@dataclass
class MetricSettings:
    resource_type: str
    name: str
    namespace: str
    statistic: str
    comparison: str
    unit: str
    period: int
    evaluation_periods: int


class MetricConfig:
    _metric_configs: Dict[str, Dict[str, MetricSettings]] = {}

    def __init__(self, file_path: Union[str, Path]):
        if not MetricConfig._metric_configs:
            self._load_metric_configs(file_path)

    @classmethod
    def _load_metric_configs(cls, file_path: Union[str, Path]) -> None:
        if cls._metric_configs:
            logger.debug("Metric Configs already loaded.")
            return

        try:
            data = load_yaml(file_path)
            cls._metric_configs = {
                resource_type: {
                    metric_name: MetricSettings(
                        resource_type=resource_type,
                        name=metric_name,
                        namespace=settings["namespace"],
                        statistic=settings["statistic"],
                        comparison=settings["comparison"],
                        unit=settings["unit"],
                        period=settings["period"],
                        evaluation_periods=settings["evaluation_periods"],
                    )
                    for metric_name, settings in metrics.items()
                }
                for resource_type, metrics in data.items()
            }
            logger.info(f"{len(cls._metric_configs)} metric configurations loaded.")
            logger.info(f"Metrics loaded: {cls._metric_configs}")
        except (FileNotFoundError, yaml.YAMLError) as e:
            logger.error(f"Error loading metrics: {e}")

    @classmethod
    def get_all_metric_configs(cls) -> Dict[str, Dict[str, MetricSettings]]:
        return cls._metric_configs

    @classmethod
    def get_metric_settings(
        cls, resource_type: str, metric_name: str
    ) -> Optional[MetricSettings]:
        """Get the MetricSettings for a specific resource_type and metric_name."""
        resource_metrics = cls._metric_configs.get(resource_type)
        if resource_metrics:
            metric_settings = resource_metrics.get(metric_name)
            if metric_settings:
                return metric_settings
        logger.info(
            f"Metric '{metric_name}' not found for resource type '{resource_type}'."
        )
        return None


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
