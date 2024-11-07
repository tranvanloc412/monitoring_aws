import boto3
import logging
from typing import List, Optional, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..core import *
from .config import *

from .constants import *

logger = logging.getLogger(__name__)


class AlarmDefinitionBuilder:
    """Handles alarm definition creation logic"""

    def __init__(self, lz, metric_config, threshold_config, customs):
        self.lz = lz
        self.metric_config = metric_config
        self.threshold_config = threshold_config
        self.custom_config = customs
        self.session = None
        self._existing_alarms = None

    def set_session(self, session: AWSSession) -> None:
        """Set AWS session for alarm operations"""
        self.session = session
        self._existing_alarms = None  # Reset cache when session changes

    def create_alarm_definition(self, resource) -> List[AlarmConfig]:
        """Create alarm definitions for a specific resource."""
        metrics = self.metric_config.get_metric_settings(resource.resource_type)
        thresholds = self.threshold_config.get_thresholds(
            self.lz.category, resource.resource_type
        )
        # I want to check the metrics in a specific namespace in cloudwatch to see if they exist
        # if not, I want to skip the alarm creation for that metric
        # if they do exist, I want to get the metric dimensions

        if not metrics or not thresholds:
            logger.warning(
                f"No metrics/thresholds for {resource.resource_type} in {self.lz.name}"
            )
            return []

        alarm_configs = []
        for metric in metrics.values():
            threshold = thresholds.get(metric.name)
            if not self._is_valid_alarm(metric, threshold, resource):
                continue

            # Check if the metric exists in CloudWatch
            if not self._metric_exists_in_cloudwatch(metric, resource):
                logger.info(
                    f"Metric {metric.name} does not exist for {resource.resource_name}, skipping alarm creation."
                )
                continue

            alarm_configs.append(self._build_alarm_config(resource, metric, threshold))

        return alarm_configs

    def _metric_exists_in_namespace(self, metric, resource) -> bool:
        """Check if a metric exists in CloudWatch."""
        if not self.session:
            return False

        cloudwatch = self.session.session.client("cloudwatch")
        try:
            response = cloudwatch.list_metrics(
                Namespace=metric.namespace,
                MetricName=metric.name,
                Dimensions=self._get_dimensions_for_resource(resource),
            )
            return len(response.get("Metrics", [])) > 0
        except Exception as e:
            logger.error(f"Error checking metric {metric.name} existence: {e}")
            return False

    def _build_alarm_config(self, resource, metric, threshold) -> AlarmConfig:
        name = f"{self.lz.name}-{resource.resource_name}-{metric.name}"
        return AlarmConfig(
            name=name,
            description=f"Alarm for {metric.name} on {resource.resource_name}",
            metric_settings=metric,
            threshold_value=threshold,
            dimensions=self._get_dimensions_for_resource(resource),
            sns_topic_arns=self._get_sns_topics(
                self.lz, resource.resource_type, metric.name
            ),
        )

    def _get_sns_topics(
        self, lz: LandingZone, resource_type: str, metric_name: str
    ) -> List[str]:
        """Get SNS topic ARNs for the given resource type and metric."""
        sns_prefix = f"arn:aws:sns:{DEFAULT_REGION}:{lz.account_id}:"

        # First try to get custom topic configuration
        topic = self.custom_config.get_sns_topic(
            resource_type, metric_name, lz.category
        )

        # If no custom topic, use default based on category
        if not topic:
            topic = (
                SNSTopic.MEDIUM.value
                if lz.category == Category.A.value
                else SNSTopic.LOW.value
            )

        logger.debug(
            f"SNS topic for {resource_type} {metric_name} {lz.category}: {topic}"
        )
        return [f"{sns_prefix}{topic}"]

    def _is_valid_alarm(
        self, metric: MetricSettings, threshold: float, resource: Resource
    ) -> bool:
        """Check if alarm should be created based on configuration and existing alarms."""
        if not threshold:
            return False

        alarm_name = f"{self.lz.name}-{resource.resource_name}-{metric.name}"
        is_disabled = self.custom_config.is_alarm_disabled(
            self.lz.name, resource.resource_type, metric.name
        )
        exists = self.session and self._is_alarm_exists(alarm_name)

        return not (is_disabled or exists)

    def _is_alarm_exists(self, alarm_name: str) -> bool:
        if not self.session:
            return False
        existing_alarms = self._get_existing_alarms(self.session)
        return alarm_name in existing_alarms

    def _get_existing_alarms(self, session: AWSSession) -> List[str]:
        """Get existing CMS-managed alarms."""
        if self._existing_alarms is not None:
            return self._existing_alarms

        try:
            scanner = ResourceScanner(session)
            resources = scanner.get_resources_by_tag(
                tags={MANAGE_BY_TAG_KEY: CMS_MANAGED_TAG_VALUE},
                resource_config={
                    "CloudWatch": {"type": "cloudwatch:alarm", "delimiter": ":"}
                },
            )
            self._existing_alarms = [
                resource.resource_name
                for resource in resources
                if hasattr(resource, "resource_name")
            ]
        except Exception as e:
            logger.error(f"Error fetching existing alarms: {str(e)}")
            self._existing_alarms = []

        return self._existing_alarms

    def _get_dimensions_for_resource(self, resource) -> List[Dict[str, str]]:
        """Get CloudWatch dimensions for the given resource."""
        return [{"Name": "ResourceId", "Value": resource.resource_id}]


class AlarmDeployer:
    """Handles alarm deployment to AWS"""

    def __init__(self, session, lz):
        self.session = session
        self.lz = lz

    def deploy_alarms(self, alarms: List[AlarmConfig]) -> None:
        """Deploy alarms in parallel batches."""
        if not self.session:
            raise ValueError("AWS session required for deployment")

        cloudwatch = self.session.session.client("cloudwatch")
        self._deploy_alarm_batch(cloudwatch, alarms)

    def _deploy_alarm_batch(self, cloudwatch, alarms: List[AlarmConfig]) -> None:
        """Deploy a batch of alarms using thread pool."""
        with ThreadPoolExecutor(max_workers=DEFAULT_MAX_WORKERS) as executor:
            futures = {
                executor.submit(
                    self._deploy_single_alarm, cloudwatch, alarm
                ): alarm.name
                for alarm in alarms
            }

            for future in as_completed(futures):
                alarm_name = futures[future]
                try:
                    future.result()
                    logger.info(f"Deployed alarm: {alarm_name}")
                except Exception as e:
                    logger.error(f"Failed to deploy {alarm_name}: {e}")

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

    def _build_alarm_tags(self, alarm_name: str) -> List[Dict[str, str]]:
        """Create standardized tags for CloudWatch alarms."""
        return [
            {"Key": "Name", "Value": alarm_name},
            {"Key": "AppID", "Value": self.lz.app_id},
            {"Key": "Environment", "Value": self.lz.env},
            {"Key": "ResourceType", "Value": "CloudWatchAlarm"},
            {"Key": MANAGE_BY_TAG_KEY, "Value": CMS_MANAGED_TAG_VALUE},
        ]


class AlarmManager:
    """Unified alarm management"""

    def __init__(self, lz: LandingZone, session: AWSSession, config: MonitoringConfig):
        self.lz = lz
        self.session = session
        self.config = config
        self.builder = AlarmDefinitionBuilder(
            lz=lz, metric_config=config, threshold_config=config, customs=config
        )
        self.builder.set_session(session)
        self.deployer = AlarmDeployer(session, lz)

    def deploy_alarms(self, resources: List[Resource]) -> None:
        """Deploy alarms for the given resources with proper error handling"""
        try:
            alarm_configs = self._create_alarm_configs(resources)
            if alarm_configs:
                self._deploy_alarms(alarm_configs)
            else:
                logger.warning(f"No alarm configurations generated for {self.lz.name}")
        except Exception as e:
            logger.error(f"Failed to deploy alarms for {self.lz.name}: {e}")
            raise

    def _create_alarm_configs(self, resources: List[Resource]) -> List[AlarmConfig]:
        """Create alarm configurations for all resources."""
        all_configs = []
        for resource in resources:
            try:
                configs = self.builder.create_alarm_definition(resource)
                all_configs.extend(configs)
            except Exception as e:
                logger.error(
                    f"Failed to create alarm config for {resource.resource_id}: {e}"
                )
        return all_configs

    def _deploy_alarms(self, alarms: List[AlarmConfig]):
        """Deploy all alarm configurations."""
        try:
            self.deployer.deploy_alarms(alarms)
        except Exception as e:
            logger.error(f"Failed to deploy alarms: {e}")
            raise
