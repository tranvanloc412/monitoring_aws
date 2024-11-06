import logging
from dataclasses import dataclass
from typing import List, Optional, Dict
from ..iam import AWSSession
from ..landing_zone import LandingZone
from ..resources import Resource, ResourceScanner
from ..core import *
from .metrics import MetricSettings, MetricConfig
from .thresholds import ThresholdConfig
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# Add constants at the top
DEFAULT_MAX_WORKERS = 10
DEFAULT_SNS_TOPIC = CMS_SNS_TOPIC_LOW


@dataclass
class AlarmConfig:
    """Configuration for a CloudWatch alarm."""

    name: str
    description: str
    metric_settings: MetricSettings
    threshold_value: int
    dimensions: Optional[List[Dict[str, str]]] = None
    sns_topic_arns: Optional[List[str]] = None


class AlarmManager:
    """Manages CloudWatch alarms for AWS resources."""

    def __init__(
        self,
        lz: LandingZone,
        resources: List[Resource],
        metric_config: MetricConfig,
        threshold_config: ThresholdConfig,
        sns_topic_arns: Optional[List[str]] = None,
        session: Optional[AWSSession] = None,
    ) -> None:
        self.lz = lz
        self.resources = resources
        self.metric_config = metric_config
        self.threshold_config = threshold_config
        self.sns_topic_arns = sns_topic_arns or [DEFAULT_SNS_TOPIC]
        self.session = session
        self._existing_alarms_cache: Optional[List[str]] = None

    def create_all_alarm_definitions(self) -> List[AlarmConfig]:
        new_alarms = []
        for resource in self.resources:
            resource_alarms = self.create_alarm_definitions(resource)
            new_alarms.extend(resource_alarms)

        logger.info(
            f"Total alarms generated for landing zone '{self.lz.name}' in category '{self.lz.category}': {len(new_alarms)}"
        )
        return new_alarms

    def create_alarm_definitions(self, resource: Resource) -> List[AlarmConfig]:
        """Create alarm definitions for a specific resource."""
        alarm_configs = []
        resource_metrics = self._get_metrics_for_resource(resource.resource_type)

        if not resource_metrics:
            logger.warning(
                f"No metrics found for {resource.resource_type} in {self.lz.name}"
            )
            return alarm_configs

        thresholds = self._get_thresholds_for_resource(resource.resource_type)

        for metric in resource_metrics:
            if threshold_value := thresholds.get(metric.name):
                alarm_name = f"{self.lz.name}-{resource.resource_name}-{metric.name}"

                # Skip if alarm already exists
                if self.session and self._is_alarm_exists(alarm_name):
                    logger.info(f"Existing alarms: {alarm_name}")
                    continue

                alarm_config = self._build_alarm_config(
                    name=alarm_name,
                    description=f"Alarm for {metric.name} on {self.lz.name} - {resource.resource_name}",
                    metric=metric,
                    threshold_value=threshold_value,
                    dimensions=self._get_dimensions_for_resource(resource),
                    sns_topic_arns=self._get_sns_topics_for_category(),
                )
                alarm_configs.append(alarm_config)

        return alarm_configs

    def deploy_alarms(
        self, max_workers: Optional[int] = DEFAULT_MAX_WORKERS, batch_size: int = 50
    ) -> None:
        """Deploy alarms to CloudWatch using parallel execution."""
        if not self.session:
            raise ValueError("AWS session is required for alarm deployment")

        cloudwatch = self.session.session.client("cloudwatch")
        alarms = self.create_all_alarm_definitions()

        if not alarms:
            logger.info("No alarms to deploy")
            return

        logger.info(f"Starting deployment of {len(alarms)} alarms")

        for i in range(0, len(alarms), batch_size):
            batch = alarms[i : i + batch_size]
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(self._deploy_single_alarm, cloudwatch, alarm): alarm
                    for alarm in batch
                }

                for future in as_completed(futures):
                    alarm = futures[future]
                    try:
                        future.result()
                        logger.info(f"Successfully deployed alarm: {alarm.name}")
                    except Exception as exc:
                        logger.error(f"Failed to deploy alarm {alarm.name}: {exc}")



    # Configuration Retrieval Methods
    def _get_metrics_for_resource(self, resource_type: str) -> List[MetricSettings]:
        """Retrieve metric configurations for a resource type."""
        metrics = (
            self.metric_config.get_all_metric_configs().get(resource_type, {}).values()
        )
        logger.debug(
            f"Retrieved {len(metrics)} metrics for resource type '{resource_type}' in landing zone '{self.lz.name}'."
        )
        return list(metrics)

    def _get_thresholds_for_resource(self, resource_type: str) -> Dict[str, int]:
        """Retrieve threshold configurations for a resource type."""
        thresholds = (
            self.threshold_config.get_cat_thresholds(self.lz.category, resource_type)
            or {}
        )
        if not thresholds:
            logger.warning(
                f"No thresholds configured for resource type '{resource_type}' in category '{self.lz.category}' for landing zone '{self.lz.name}'."
            )
        else:
            logger.debug(
                f"Retrieved thresholds for resource type '{resource_type}': {thresholds}"
            )
        return thresholds

    def _get_dimensions_for_resource(self, resource: Resource) -> List[Dict[str, str]]:
        """Get CloudWatch dimensions for a specific resource type."""
        dimension_mappings = {
            "EC2": [{"Name": "InstanceId", "Value": resource.resource_id}],
            "RDS": [{"Name": "DBInstanceIdentifier", "Value": resource.resource_id}],
            "ELB": [{"Name": "LoadBalancerName", "Value": resource.resource_name}],
        }

        try:
            dimensions = dimension_mappings.get(resource.resource_type, [])
            if not dimensions:
                logger.warning(
                    f"No dimension mapping for {resource.resource_type}. "
                    "Alarm may not work as expected."
                )
            return dimensions
        except Exception as e:
            logger.error(
                f"Error creating dimensions for {resource.resource_type}: {str(e)}"
            )
            return []

    def _get_sns_topics_for_category(
        self, override_topics: Optional[List[str]] = None
    ) -> List[str]:
        """Get SNS topics based on category, with optional override."""
        if override_topics:
            return override_topics

        category_topic_mapping = {
            "CAT_A": [CMS_SNS_TOPIC_MEDIUM],
            "CAT_B": [CMS_SNS_TOPIC_MEDIUM],
            "CAT_C": [CMS_SNS_TOPIC_LOW],
            "CAT_D": [CMS_SNS_TOPIC_LOW],
        }

        return category_topic_mapping.get(self.lz.category, [CMS_SNS_TOPIC_LOW])

    # Alarm Building Methods
    def _build_alarm_config(
        self,
        name: str,
        description: str,
        metric: MetricSettings,
        threshold_value: int,
        dimensions: List[Dict[str, str]],
        sns_topic_arns: List[str],
    ) -> AlarmConfig:
        alarm_config = AlarmConfig(
            name=name,
            description=description,
            metric_settings=metric,
            threshold_value=threshold_value,
            dimensions=dimensions,
            sns_topic_arns=sns_topic_arns,
        )
        logger.debug(
            f"Created AlarmConfig for metric '{metric.name}' with threshold '{threshold_value}'"
            f" and dimensions '{dimensions}': {alarm_config}"
        )
        return alarm_config

    def _build_alarm_tags(self, alarm_name: str) -> List[Dict[str, str]]:
        """Create standardized tags for CloudWatch alarms."""
        return [
            {"Key": MANAGE_BY_TAG_KEY, "Value": CMS_MANAGED_TAG_VALUE},
            {"Key": "Name", "Value": alarm_name},
            {"Key": "ResourceType", "Value": "CloudWatchAlarm"},
            {"Key": "AppID", "Value": "CMS"},
        ]

    # Deployment Methods
    def _deploy_single_alarm(self, cloudwatch, alarm: AlarmConfig) -> None:
        """Deploy a single CloudWatch alarm."""
        try:
            cloudwatch.put_metric_alarm(
                AlarmName=alarm.name,
                MetricName=alarm.metric_settings.name,
                Namespace=alarm.metric_settings.namespace,
                Statistic=alarm.metric_settings.statistic,
                Period=alarm.metric_settings.period,
                EvaluationPeriods=alarm.metric_settings.evaluation_periods,
                Threshold=alarm.threshold_value,
                ComparisonOperator=alarm.metric_settings.comparison_operator,
                ActionsEnabled=True,
                AlarmActions=alarm.sns_topic_arns or [],
                AlarmDescription=alarm.description,
                Dimensions=alarm.dimensions or [],
                Unit=alarm.metric_settings.unit,
                Tags=self._build_alarm_tags(alarm.name),
            )
        except Exception as e:
            logger.error(f"Error deploying alarm {alarm.name}: {str(e)}")
            raise

    # Alarm Existence Check Methods
    def _get_existing_alarms(self, session: AWSSession) -> List[str]:
        if self._existing_alarms_cache is None:
            resource_scanner = ResourceScanner(session)
            resources = resource_scanner._get_resources_by_tag(
                MANAGE_BY_TAG_KEY,
                CMS_MANAGED_TAG_VALUE,
                supported_resource_types={"CloudWatch": "cloudwatch:alarm"},
            )
            self._existing_alarms_cache = [r.resource_name for r in resources]
        return self._existing_alarms_cache

    def _is_alarm_exists(self, alarm_name: str) -> bool:
        if not self.session:
            return False
        existing_alarms = self._get_existing_alarms(self.session)
        return alarm_name in existing_alarms


