# Standard library imports
import logging
from pathlib import Path
from typing import Dict, List, Set, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# Local imports
from ..core import LandingZone, AWSSession, Resource, ResourceScanner
from .alarm_config import AlarmConfig, MetricConfig  # Renamed from AlarmConfigs, Metric
from .constants import (
    DEFAULT_REGION,
    DEFAULT_MAX_WORKERS,
    MANAGE_BY_TAG_KEY,
    CMS_MANAGED_TAG_VALUE,
    DIMENSION_KEYS,
)
from .alarm_config_manager import AlarmConfigManager

logger = logging.getLogger(__name__)


class AlarmManager:
    def __init__(
        self,
        landing_zone: LandingZone,
        aws_session: AWSSession,
        monitored_resources: List[Resource],
        alarm_config_path: Path,
        category_config_path: Path,
        custom_config_path: Path,
    ):
        # Core attributes
        self.landing_zone = landing_zone
        self.aws_session = aws_session
        self.monitored_resources = monitored_resources
        self._resource_ids = {resource.id for resource in monitored_resources}

        # Initialize configurations
        self.config_manager = AlarmConfigManager(
            alarm_config_path, category_config_path, custom_config_path
        )
        self._load_configurations()

        # Initialize state
        self._existing_alarms = set()
        self._existing_custom_metrics = {}
        self._scan_existing_alarms()
        self._fetch_custom_metrics()

    def _load_configurations(self):
        """Load all necessary configurations."""
        self._alarm_configs = self.config_manager.alarm_configs
        self._category_configs = self.config_manager.get_category_config(
            self.landing_zone.category
        )
        self._custom_configs = self.config_manager.custom_configs
        self._threshold_configs = self._category_configs.get("thresholds", {})

    def _fetch_custom_metrics(self):
        """Fetch and store existing custom metrics for resources."""
        client = self.aws_session.session.client("cloudwatch")

        try:
            for custom_metric in self._custom_configs.get("metrics", []):
                metrics = client.list_metrics(
                    Namespace=custom_metric["namespace"],
                    MetricName=custom_metric["name"],
                ).get("Metrics", [])

                for metric in metrics:
                    dimensions = self._dimensions_to_dict(metric["Dimensions"])
                    if "InstanceId" not in dimensions:
                        continue

                    instance_id = dimensions["InstanceId"]
                    if instance_id in self._resource_ids:
                        # Append dimensions instead of overwriting
                        if instance_id not in self._existing_custom_metrics:
                            self._existing_custom_metrics[instance_id] = []
                        self._existing_custom_metrics[instance_id].append(dimensions)

        except Exception as e:
            logger.error(f"Failed to fetch custom metrics: {e}")

    def _dimensions_to_dict(self, dimensions: List[Dict[str, str]]) -> Dict[str, str]:
        return {dim["Name"]: dim["Value"] for dim in dimensions}

    def _get_dimensions(
        self, metric: MetricConfig, resource: Resource
    ) -> List[Dict[str, str]]:
        """Get dimensions for a specific resource."""
        # Handle custom metrics case
        custom_metrics = [m["name"] for m in self._custom_configs.get("metrics", [])]
        if metric.name in custom_metrics:
            dimensions = self._existing_custom_metrics.get(resource.id, [])
            logger.info(f"Custom metric dimensions for {resource.id}: {dimensions}")
            return dimensions

        # Handle standard dimensions
        try:
            dimensions = [{DIMENSION_KEYS.get(resource.type, ""): resource.id}]
            logger.debug(f"Standard metric dimensions for {resource.id}: {dimensions}")
            return dimensions
        except Exception as e:
            logger.error(f"Failed to get dimensions for {resource.id}: {e}")
            return []

    # ---- Configuration Getter Methods ----
    def _get_sns_topics(self, resource_type: str, metric_name: str) -> List[str]:
        """Get SNS topic ARNs for the given resource type and metric."""
        sns_prefix = f"arn:aws:sns:{DEFAULT_REGION}:{self.landing_zone.account_id}:"
        sns_topic_arns = self._category_configs.get("sns_topic_arns", [])

        # Get custom topic configuration
        custom_sns_mappings = (
            self.config_manager.custom_configs.get("sns_mappings", {})
            .get(resource_type, {})
            .get(metric_name, {})
        )

        if self.landing_zone.category in custom_sns_mappings.get("categories", []):
            sns_topic_arns = custom_sns_mappings.get("sns_topics", [])

        return [sns_prefix + topic for topic in sns_topic_arns]

    def _get_alarm_config_by_resource_type(
        self, resource_type: str
    ) -> List[AlarmConfig]:
        return self._alarm_configs.get(resource_type, [])

    def _get_threshold_value(
        self, resource_type: str, metric_name: str
    ) -> Optional[float]:
        """Get threshold value for a specific resource type and metric."""
        resource_thresholds = self._threshold_configs.get(resource_type, {})
        if isinstance(resource_thresholds, dict):
            return resource_thresholds.get(metric_name, None)
        return (
            resource_thresholds
            if isinstance(resource_thresholds, (int, float))
            else None
        )

    # ---- Alarm Creation Methods ----

    def create_alarm_definition(
        self, alarm: AlarmConfig, resource: Resource
    ) -> Optional[AlarmConfig]:
        """Create or update alarm definition for a specific resource and metric."""
        try:
            # Sanitize metric name for alarm name construction
            sanitized_metric_name = alarm.metric.name.replace(" ", "").replace("%", "")
            alarm_name = f"{self.landing_zone.name}-{resource.type}-{resource.name}-{sanitized_metric_name}"
            logger.debug(f"Constructing alarm definition for: {alarm_name}")

            # Early returns for invalid cases
            if self._is_alarm_exists(alarm_name):
                logger.info(f"Alarm {alarm_name} already exists, skipping creation")
                return None

            threshold = self._get_threshold_value(resource.type, alarm.metric.name)
            if threshold is None:
                logger.warning(
                    f"No threshold configured for {resource.type}.{alarm.metric.name}, "
                    f"skipping alarm creation"
                )
                return None

            # Create new alarm configuration
            alarm.name = alarm_name
            alarm.description = f"Alarm for {alarm.metric.name} on {resource.name}"
            alarm.metric.dimensions = self._get_dimensions(alarm.metric, resource)
            alarm.threshold_value = threshold
            alarm.sns_topic_arns = self._get_sns_topics(
                resource.type, alarm.metric.name
            )

            logger.debug(f"Successfully created alarm definition for {alarm_name}")
            return alarm

        except Exception as e:
            logger.error(
                f"Failed to create alarm definition for {resource.id}: {str(e)}",
                exc_info=True,
            )
            return None

    def create_alarm_definitions(self, resource: Resource) -> List[AlarmConfig]:
        """Create alarm definitions for all metrics of a specific resource."""
        try:
            logger.debug(f"Creating alarm definitions for resource: {resource.id}")

            # Get alarm configs for resource type
            alarms = self._get_alarm_config_by_resource_type(resource.type)

            if not alarms:
                logger.info(
                    f"No alarm configurations found for resource type: {resource.type}"
                )
                return []

            # Create alarm definitions
            result_alarms = [
                alarm_def
                for alarm in alarms
                if (alarm_def := self.create_alarm_definition(alarm, resource))
            ]

            logger.info(
                f"Created {len(result_alarms)} alarm definitions for resource {resource.id}"
            )
            return result_alarms

        except Exception as e:
            logger.error(
                f"Failed to create alarm definitions for resource {resource.id}: {e}"
            )
            return []

    def create_all_alarm_definitions(self) -> List[AlarmConfig]:
        """Create alarm definitions for all resources."""
        try:
            all_alarms = []
            for resource in self.monitored_resources:
                alarms = self.create_alarm_definitions(resource)
                all_alarms.extend(alarms)
            return all_alarms
        except Exception as e:
            logger.error(f"Failed to create all alarm definitions: {e}")
            return []

    # ---- Alarms Deployment Methods ----

    def _deploy_single_alarm(self, session: AWSSession, alarm: AlarmConfig) -> None:
        """Deploy a single CloudWatch alarm."""
        if not alarm.name:  # Add validation
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
                AlarmActions=alarm.sns_topic_arns or [],  # Ensure we don't pass None
                AlarmDescription=alarm.description
                or "",  # Provide default empty string
                Unit=alarm.unit,
                Tags=self._build_alarm_tags(alarm.name),
            )
        except Exception as e:
            logger.error(f"Error deploying alarm {alarm.name}: {e}")
            raise

    def deploy_alarms(self, alarms: List[AlarmConfig]) -> None:
        """Deploy alarms in parallel batches."""
        with ThreadPoolExecutor(max_workers=DEFAULT_MAX_WORKERS) as executor:
            futures = {
                executor.submit(
                    self._deploy_single_alarm, self.aws_session, alarm
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

    # ---- Utility Methods ----

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
