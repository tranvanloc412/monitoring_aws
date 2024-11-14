import logging
from pathlib import Path
from copy import deepcopy
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..core import LandingZone, AWSSession, Resource, ResourceScanner
from .alarm_config import AlarmConfig, Alarms, ResourceMetrics, MetricConfig
from .constants import *
from .alarm_config_manager import AlarmConfigManager

logger = logging.getLogger(__name__)


class AlarmManager:
    """
    Manages CloudWatch alarms for AWS resources.
    Handles alarm configuration, creation, and deployment.
    """

    def __init__(
        self,
        landing_zone: LandingZone,
        aws_session: AWSSession,
        monitored_resources: List[Resource],
        alarm_config_path: Path,
        category_config_path: Path,
        custom_config_path: Path,
    ) -> None:
        """Initialize AlarmManager with required configurations."""
        self.landing_zone = landing_zone
        self.aws_session = aws_session
        self.monitored_resources = monitored_resources

        # Initialize state
        self._existing_alarms: set[str] = set()
        self._existing_custom_metrics = ResourceMetrics()

        # Load configurations
        self._load_configurations(
            alarm_config_path, category_config_path, custom_config_path
        )
        self._load_states()

    #### Public Methods ####
    # ---- Alarm Deployment ----
    def deploy_alarms(self, alarms: Alarms) -> None:
        """Deploy alarms in parallel batches."""
        with ThreadPoolExecutor(max_workers=DEFAULT_MAX_WORKERS) as executor:
            futures = {
                executor.submit(
                    self._deploy_single_alarm, self.aws_session, alarm
                ): alarm.name
                for alarm in alarms.alarms
            }

            for future in as_completed(futures):
                alarm_name = futures[future]
                try:
                    future.result()
                    logger.info(f"Deployed alarm: {alarm_name}")
                except Exception as e:
                    logger.error(f"Failed to deploy {alarm_name}: {e}")
                    raise

    def scan_alarms(self) -> None:
        """Scan and cache existing alarms in the AWS account."""
        logger.info(
            f"Successfully scanned resources for landing zone: {self.landing_zone.name}"
        )
        logger.info(f"Existing alarms: {self._existing_alarms}")

    def delete_alarms(self) -> None:
        """Delete all alarms in the AWS account."""
        logger.info(f"Deleting alarms for landing zone: {self.landing_zone.name}")
        for alarm in self._existing_alarms:
            self.aws_session.session.client("cloudwatch").delete_alarms(
                AlarmNames=[alarm]
            )
            logger.info(f"Deleted alarm: {alarm}")

    # ---- Alarm Definition Creation ----
    def create_all_alarm_definitions(self) -> Alarms:
        """Create alarm definitions for all resources."""
        try:
            all_alarm_definitions = Alarms()
            for resource in self.monitored_resources:
                alarms = self._create_alarm_definitions(resource)

                all_alarm_definitions.add_alarm(alarms)

            return all_alarm_definitions
        except Exception as e:
            logger.error(f"Failed to create all alarm definitions: {e}")
            return Alarms()

    #### Private Configuration Methods ####
    def _load_configurations(
        self,
        alarm_config_path: Path,
        category_config_path: Path,
        custom_config_path: Path,
    ) -> None:
        """Initialize all configuration settings."""
        config_manager = AlarmConfigManager()
        config_manager.load_configs(
            alarm_config_path, category_config_path, custom_config_path
        )
        self._alarm_configs = config_manager.get_alarm_configs()
        self._all_category_configs = config_manager.get_category_configs()
        self._custom_configs = config_manager.get_custom_configs()

        self._category_configs = self._all_category_configs.get(
            self.landing_zone.category, {}
        )
        self._threshold_configs = self._category_configs.get("thresholds", {})
        self._sns_topics = self._category_configs.get("sns_topic_arns", [])

    def _load_states(self):
        self._existing_alarms = set()
        self._existing_custom_metrics = ResourceMetrics()
        self._scan_existing_alarms()
        self._fetch_existing_custom_metrics()

    def _get_alarm_config_by_resource_type(
        self, resource_type: str
    ) -> List[AlarmConfig]:
        return self._alarm_configs.get(resource_type, [])

    def _get_dimensions(self, resource: Resource) -> List[Dict[str, str]]:
        """Get dimensions for a specific resource based on resource type."""
        dimension_key = DIMENSION_KEYS.get(resource.type)
        if not dimension_key:
            logger.warning(f"No dimension key found for resource type {resource.type}")
            return []

        dimensions = [{"Name": dimension_key, "Value": resource.id}]
        return dimensions

    def _get_threshold_value(
        self, resource_type: str, metric_name: str
    ) -> Optional[float]:
        """Get threshold value for a specific resource type and metric."""
        return self._threshold_configs.get(resource_type).get(metric_name, {})

    def _get_sns_topics(self, resource_type: str, metric_name: str) -> List[str]:
        """Get SNS topic ARNs for the given resource type and metric."""
        sns_prefix = f"arn:aws:sns:{DEFAULT_REGION}:{self.landing_zone.account_id}:"
        sns_topic_arns = self._sns_topics

        # Get custom topic configuration
        custom_sns_mappings = (
            self._custom_configs.get("sns_mappings", {})
            .get(resource_type, {})
            .get(metric_name, {})
        )

        if (
            custom_sns_mappings
            and self.landing_zone.category in custom_sns_mappings.get("categories", [])
        ):
            sns_topic_arns = custom_sns_mappings.get("sns_topics", self._sns_topics)

        return [sns_prefix + topic for topic in sns_topic_arns]

    def _create_alarm_definitions(self, resource: Resource) -> Alarms:
        """Create alarm definitions for all metrics of a specific resource."""
        alarm_definitions = Alarms()
        alarm_configs = self._get_alarm_config_by_resource_type(resource.type)

        if not alarm_configs:
            logger.debug(f"No alarm configs found for resource type: {resource.type}")
            return alarm_definitions

        for alarm_config in alarm_configs:
            try:
                alarm_def = self._create_single_alarm_definition(alarm_config, resource)
                if not alarm_def:
                    continue

                if self._is_custom_metric(alarm_def.metric.name):
                    alarm_definitions.add_alarm(
                        self._update_alarm_definitions(alarm_def, resource)
                    )
                else:
                    alarm_definitions.add_alarm(alarm_def)
            except Exception as e:
                logger.error(
                    f"Failed to create alarm definition for {resource.name}: {e}"
                )
                continue

        logger.info(
            f"Created {len(alarm_definitions)} alarm definitions for {resource.type} - {resource.name}"
        )
        return alarm_definitions

    def _create_single_alarm_definition(
        self,
        alarm: AlarmConfig,
        resource: Resource,
    ) -> Optional[AlarmConfig]:
        """Create alarm definition for a specific resource and metric."""
        alarm_name = f"{self.landing_zone.name}-{resource.type}-{resource.name}-{alarm.metric_name()}"

        if self._is_alarm_exists(alarm_name):
            logger.info(f"Alarm {alarm_name} already exists, skipping creation")
            return None

        threshold = self._get_threshold_value(resource.type, alarm.metric.name)
        if threshold is None:
            logger.warning(
                f"Missing threshold config for {resource.type}.{alarm.metric.name}"
            )
            return None

        new_alarm = deepcopy(alarm)
        new_alarm.name = alarm_name
        new_alarm.description = f"Alarm for {alarm.metric.name} on {resource.name}"
        new_alarm.metric.dimensions = self._get_dimensions(resource)
        new_alarm.threshold_value = threshold
        new_alarm.sns_topic_arns = self._get_sns_topics(
            resource.type, alarm.metric.name
        )

        return new_alarm

    def _update_alarm_definitions(
        self, alarm_def: AlarmConfig, resource: Resource
    ) -> Alarms:
        """Create multiple alarm definitions for custom metrics."""
        custom_alarm_definitions = Alarms()
        custom_metrics = self._existing_custom_metrics.get_metrics(resource.id)

        for index, metric in enumerate(custom_metrics):
            if metric.name != alarm_def.metric.name:
                continue

            new_alarm_def = deepcopy(alarm_def)
            new_alarm_def.name = f"{alarm_def.name}-{index}"
            if self._is_alarm_exists(new_alarm_def.name):
                logger.info(
                    f"Alarm {new_alarm_def.name} already exists, skipping creation"
                )
                continue
            new_alarm_def.metric.dimensions = metric.dimensions
            custom_alarm_definitions.add_alarm(new_alarm_def)

        return custom_alarm_definitions

    def _deploy_single_alarm(self, session: AWSSession, alarm: AlarmConfig) -> None:
        """Deploy a single CloudWatch alarm."""
        if not alarm:
            logger.error("Cannot deploy alarm with no name")
            return

        cloudwatch = session.session.client("cloudwatch")
        try:
            cloudwatch.put_metric_alarm(
                AlarmName=alarm.name,
                MetricName=alarm.metric.name,
                Namespace=alarm.metric.namespace,
                Dimensions=alarm.metric.dimensions,
                Statistic=alarm.statistic,
                Period=alarm.period,
                EvaluationPeriods=alarm.evaluation_periods,
                Threshold=alarm.threshold_value,
                ComparisonOperator=alarm.comparison_operator,
                ActionsEnabled=True,
                AlarmActions=alarm.sns_topic_arns or [],
                AlarmDescription=alarm.description or "",
                Unit=alarm.unit,
                Tags=self._build_alarm_tags(alarm.name),
            )
        except Exception as e:
            logger.error(f"Error deploying alarm {alarm.name}: {e}")
            raise

    #### Utility Methods ####
    def _is_custom_metric(self, metric_name: str) -> bool:
        return any(
            custom_metric["name"] == metric_name
            for custom_metric in self._custom_configs.get("metrics", [])
        )

    def _is_alarm_exists(self, alarm_name: str) -> bool:
        """Check if an alarm already exists."""
        if not self._existing_alarms:
            self._scan_existing_alarms()
        return alarm_name in self._existing_alarms

    def _scan_existing_alarms(self):
        """Scan and cache existing alarms in the AWS account."""
        resource_scanner = ResourceScanner(self.aws_session, DEFAULT_REGION)
        if not self._existing_alarms:
            scanned_alarms = resource_scanner.get_resources_by_tag(
                tags={MANAGE_BY_TAG_KEY: CMS_MANAGED_TAG_VALUE},
                resource_config={
                    "CloudWatch": {"type": "cloudwatch:alarm", "delimiter": ":"}
                },
            )
            self._existing_alarms = {alarm.name for alarm in scanned_alarms}

    def _build_alarm_tags(self, alarm_name: str) -> List[Dict[str, str]]:
        """Create standardized tags for CloudWatch alarms."""
        return [
            {"Key": "Name", "Value": alarm_name},
            {"Key": "AppID", "Value": self.landing_zone.app_id},
            {"Key": "Environment", "Value": self.landing_zone.env},
            {"Key": "ResourceType", "Value": "CloudWatchAlarm"},
            {"Key": MANAGE_BY_TAG_KEY, "Value": CMS_MANAGED_TAG_VALUE},
        ]

    def _fetch_existing_custom_metrics(self) -> None:
        """Fetch and cache existing custom metrics from CloudWatch."""
        for metric in self._custom_configs.get("metrics", []):
            try:
                metrics = self._fetch_metric_in_namespace(
                    metric["namespace"], metric["name"]
                )
                for custom_metric in metrics:
                    metric_config = MetricConfig(
                        name=custom_metric.get("MetricName", ""),
                        namespace=custom_metric.get("Namespace", ""),
                        dimensions=custom_metric.get("Dimensions", []),
                    )
                    self._existing_custom_metrics.add_metric(metric_config)
            except Exception as e:
                logger.error(f"Failed to fetch custom metric {metric['name']}: {e}")

    def _fetch_metric_in_namespace(
        self, namespace: str, metric_name: str
    ) -> List[Dict]:
        """Fetch all metrics with specified name in a CloudWatch namespace."""
        client = self.aws_session.session.client("cloudwatch")
        try:
            response = client.list_metrics(Namespace=namespace, MetricName=metric_name)
            return response.get("Metrics", [])
        except Exception as e:
            logger.error(
                f"Error fetching metric {metric_name} in namespace {namespace}: {e}"
            )
            return []
