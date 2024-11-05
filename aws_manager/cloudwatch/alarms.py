import logging
from dataclasses import dataclass
from typing import List, Optional, Dict
from ..landing_zone import LandingZone
from ..resources import Resource
from .metrics import (
    MetricSettings,
    MetricConfig,
    ThresholdConfig,
)

logger = logging.getLogger(__name__)

CMS_SNS_TOPIC_LOW = ["arn:aws:sns:ap-southeast-1:891377130283:HIPNotifyTopicLow"]


@dataclass
class AlarmConfig:
    metric_settings: MetricSettings
    threshold_value: int
    sns_topic_arns: List[str]  # Used for both alarm and OK actions


class AlarmManager:
    def __init__(
        self,
        lz: LandingZone,
        resources: List[Resource],
        metric_config: MetricConfig,
        threshold_config: ThresholdConfig,
        sns_topic_arns: Optional[List[str]] = None,
    ):
        self.lz = lz
        self.resources = resources
        self.metric_config = metric_config
        self.threshold_config = threshold_config
        self.sns_topic_arns = sns_topic_arns or CMS_SNS_TOPIC_LOW

    def create_all_alarm_definitions(self) -> List[AlarmConfig]:
        """Generates a list of AlarmConfig instances for all resources in the landing zone."""
        all_alarm_configs = []

        for resource in self.resources:
            resource_alarms = self.create_alarm_definitions(resource)
            all_alarm_configs.extend(resource_alarms)
            self._log_alarm_creation(resource, len(resource_alarms))

        logger.info(
            f"Total alarms generated for landing zone '{self.lz.name}' in category '{self.lz.category}': {len(all_alarm_configs)}"
        )
        return all_alarm_configs

    def create_alarm_definitions(self, resource: Resource) -> List[AlarmConfig]:
        """Generates a list of AlarmConfig instances for all applicable metrics of a given resource."""
        alarm_configs = []
        resource_metrics = self._get_metrics_for_resource(resource.resource_type)

        if not resource_metrics:
            logger.warning(
                f"No metrics found for resource type '{resource.resource_type}' in landing zone '{self.lz.name}'"
            )
            return alarm_configs

        category_thresholds = self._get_thresholds_for_resource(resource.resource_type)

        for metric in resource_metrics:
            threshold_value = category_thresholds.get(metric.name)
            if threshold_value is not None:
                alarm_configs.append(self._build_alarm_config(metric, threshold_value))
            else:
                logger.warning(
                    f"Threshold not found for metric '{metric.name}' in "
                    f"resource type '{resource.resource_type}' for category '{self.lz.category}'."
                )

        logger.info(
            f"Generated {len(alarm_configs)} alarm definitions for {resource.resource_type} in landing zone '{self.lz.name}'."
        )
        return alarm_configs

    def _get_metrics_for_resource(self, resource_type: str) -> List[MetricSettings]:
        """Fetch all metrics applicable to a given resource type."""
        metrics = (
            self.metric_config.get_all_metric_configs().get(resource_type, {}).values()
        )
        logger.debug(
            f"Retrieved {len(metrics)} metrics for resource type '{resource_type}' in landing zone '{self.lz.name}'."
        )
        return list(metrics)

    def _get_thresholds_for_resource(self, resource_type: str) -> Dict[str, int]:
        """Fetch thresholds for the specified resource type and landing zone category."""
        thresholds = (
            self.threshold_config.get_cat_thresholds(self.lz.category, resource_type)
            or {}
        )

        if not thresholds:
            logger.warning(
                f"No thresholds configured for resource type '{resource_type}' "
                f"in category '{self.lz.category}' for landing zone '{self.lz.name}'. Returning empty thresholds."
            )
        else:
            logger.debug(
                f"Retrieved thresholds for resource type '{resource_type}': {thresholds}"
            )
        return thresholds

    def _build_alarm_config(
        self, metric: MetricSettings, threshold_value: int
    ) -> AlarmConfig:
        """Builds and returns an AlarmConfig instance for a given metric and threshold."""
        alarm_config = AlarmConfig(
            metric_settings=metric,
            threshold_value=threshold_value,
            sns_topic_arns=self.sns_topic_arns,
        )
        logger.debug(
            f"Created AlarmConfig for metric '{metric.name}' with threshold '{threshold_value}': {alarm_config}"
        )
        return alarm_config

    def _log_alarm_creation(self, resource: Resource, alarm_count: int) -> None:
        """Logs the number of alarms created for a specific resource."""
        logger.info(
            f"Generated {alarm_count} alarm definitions for resource '{resource.resource_type}' in landing zone '{self.lz.name}'."
        )
