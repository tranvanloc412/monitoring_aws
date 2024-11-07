from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging
from utils.utils import load_yaml
from utils.constants import METRICS_CONFIG, THRESHOLDS_CONFIG, CUSTOM_CONFIG

logger = logging.getLogger(__name__)

@dataclass
class MetricSettings:
    """Settings for a CloudWatch metric"""
    resource_type: str
    name: str
    namespace: str
    statistic: str
    comparison_operator: str
    unit: str
    period: int
    evaluation_periods: int

@dataclass
class AlarmConfig:
    """Configuration for a CloudWatch alarm"""
    name: str
    description: str
    metric_settings: MetricSettings
    threshold_value: float
    dimensions: List[Dict[str, str]] = field(default_factory=list)
    sns_topic_arns: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.name or not self.description:
            raise ValueError("Name and description are required")
        if self.threshold_value < 0:
            raise ValueError("Threshold value must be non-negative")

@dataclass
class MonitoringConfig:
    """Unified configuration for alarm monitoring"""
    _metric_configs: Dict[str, Dict[str, MetricSettings]] = field(default_factory=dict)
    _threshold_configs: Dict[str, Dict[str, float]] = field(default_factory=dict)
    _custom_configs: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, 
             metrics_path: Path = METRICS_CONFIG,
             thresholds_path: Path = THRESHOLDS_CONFIG,
             customs_path: Path = CUSTOM_CONFIG) -> 'MonitoringConfig':
        """Load configuration from default or specified paths"""
        config = cls()
        config._load_configs(metrics_path, thresholds_path, customs_path)
        return config

    def _load_configs(self, metrics_path: Path, thresholds_path: Path, customs_path: Path) -> None:
        """Load all configurations at once"""
        try:
            self._load_metric_configs(metrics_path)
            self._load_threshold_configs(thresholds_path)
            self._load_custom_configs(customs_path)
        except Exception as e:
            logger.error(f"Failed to load configurations: {e}")
            raise

    def _load_metric_configs(self, file_path: Path) -> None:
        try:
            data = load_yaml(file_path)
            self._metric_configs = {
                resource_type: {
                    metric_name: MetricSettings(
                        resource_type=resource_type,
                        name=metric_name,
                        **settings
                    )
                    for metric_name, settings in metrics.items()
                }
                for resource_type, metrics in data.items()
            }
        except Exception as e:
            logger.error(f"Error loading metrics: {e}")

    def _load_threshold_configs(self, file_path: Path) -> None:
        try:
            data = load_yaml(file_path)
            self._threshold_configs = {
                f"{resource['resource_type']}_{category}": resource["thresholds"]
                for category, resources in data.items()
                for resource in resources
            }
        except Exception as e:
            logger.error(f"Error loading thresholds: {e}")

    def _load_custom_configs(self, file_path: Path) -> None:
        try:
            self._custom_configs = load_yaml(file_path)
        except Exception as e:
            logger.error(f"Error loading custom configs: {e}")

    def get_metric_settings(self, resource_type: str) -> Dict[str, MetricSettings]:
        return self._metric_configs.get(resource_type, {})

    def get_thresholds(self, category: str, resource_type: str) -> Dict[str, float]:
        key = f"{resource_type}_{category}"
        return self._threshold_configs.get(key, {})

    def is_alarm_disabled(self, landing_zone: str, resource_type: str, metric: str) -> bool:
        disabled = self._custom_configs.get('disabled_alarms', {}).get(landing_zone, {}).get(resource_type, [])
        return metric in disabled

    def get_sns_topic(self, resource_type: str, metric: str, category: str) -> Optional[str]:
        mapping = self._custom_configs.get('sns_mappings', {}).get(resource_type, {}).get(metric, {})
        if mapping and category in mapping.get('categories', []):
            return mapping.get('sns_topic')
        return None
