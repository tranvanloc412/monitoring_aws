import boto3
import logging
import yaml
from pathlib import Path
from typing import Dict, List, Any, Set, Optional, Union
from concurrent.futures import ThreadPoolExecutor, as_completed
import copy

from ..core import *
from .config import AlarmConfigs, Metric
from utils.utils import load_yaml
from .constants import *
from utils.constants import *

logger = logging.getLogger(__name__)


class AlarmManager:
    # Class-level configuration caches
    _alarm_configs: Dict[str, List[AlarmConfigs]] = {}
    _all_category_configs: Dict[str, Dict[str, Dict[str, Union[float, str]]]] = {}
    _custom_configs: Dict[str, Any] = {}

    def __init__(
        self,
        lz: Optional[LandingZone],
        resources: List[Resource],
        alarm_config_path: Path,
        category_config_path: Path,
        custom_config_path: Path,
        session: AWSSession,
    ):
        self.lz = lz
        self.resources = resources
        self.session = session
        self._category_configs: Dict[str, Dict[str, Union[float, str]]] = {}
        self._existing_alarms: Set[str] = set()
        self.alarms: List[AlarmConfigs] = []
        self._resource_ids: Set[str] = {resource.id for resource in self.resources}
        self._custom_metrics: List[Metric] = []

        # Load configurations if not already cached
        self._initialize_configs(
            alarm_config_path, category_config_path, custom_config_path
        )

    # ---- Configuration Loading Methods ----

    def _initialize_configs(
        self,
        alarm_config_path: Path,
        category_config_path: Path,
        custom_config_path: Path,
    ) -> None:
        """Initialize all required configurations."""
        if not self._alarm_configs:
            self._load_alarm_configs(alarm_config_path)
            logger.debug(f"Loaded alarm configs: {self._alarm_configs}")
        if not self._all_category_configs:
            self._load_all_category_configs(category_config_path)
            logger.debug(f"_all_category_configs: {self._all_category_configs}")
        if not self._custom_configs:
            self._load_custom_configs(custom_config_path)

        self._category_configs = self._get_category_configs()
        self._threshold_configs = self._get_threshold_configs()
        self._existing_alarms = self.scan_existing_alarms()
        self.get_custom_metrics()

    @classmethod
    def _load_alarm_configs(cls, alarm_config_paths: Path) -> None:
        """Load and parse alarm configurations from YAML."""
        try:
            data = load_yaml(alarm_config_paths)
            for resource_type, configs in data.items():
                cls._alarm_configs[resource_type] = [
                    AlarmConfigs(
                        metric=Metric(
                            name=config["metric"]["name"],
                            namespace=config["metric"]["namespace"],
                            dimensions=config["metric"]["dimensions"],
                        ),
                        statistic=config["statistic"],
                        comparison_operator=config["comparison_operator"],
                        unit=config["unit"],
                        period=config["period"],
                        evaluation_periods=config["evaluation_periods"],
                        name=config["name"],
                    )
                    for config in configs
                ]
        except (yaml.YAMLError, FileNotFoundError) as e:
            logger.error(f"Error loading alarm configs: {e}")
            raise ConfigurationError(f"Failed to load alarm configs: {e}")

    @classmethod
    def _load_all_category_configs(cls, threshold_configs_path: Path) -> None:
        """Load category-specific configurations."""
        try:
            cls._all_category_configs = load_yaml(threshold_configs_path)
        except Exception as e:
            logger.error(f"Error loading thresholds: {e}")

    @classmethod
    def _load_custom_configs(cls, custom_config_path: Path) -> None:
        """Load custom alarm configurations."""
        try:
            cls._custom_configs = load_yaml(custom_config_path)
        except Exception as e:
            logger.error(f"Error loading custom configs: {e}")

    # ---- Configuration Getter Methods ----

    def _get_category_configs(self) -> Dict[str, Dict[str, Union[float, str]]]:
        """Get configurations specific to the current landing zone category."""
        return self._all_category_configs.get(self.lz.category, {})

    def _get_threshold_configs(self) -> Dict[str, Dict[str, float]]:
        """Get threshold value for a specific resource type and metric."""
        return self._category_configs.get("thresholds", {})

    def _get_sns_topics(self, resource_type: str, metric_name: str) -> List[str]:
        """Get SNS topic ARNs for the given resource type and metric."""
        sns_topic_arns = self._category_configs.get("sns_topic_arns", [])

        # Get custom topic configuration
        custom_sns_mappings = (
            self._custom_configs.get("sns_mappings", {})
            .get(resource_type, {})
            .get(metric_name, {})
        )

        if self.lz.category in custom_sns_mappings.get("categories", []):
            sns_topic_arns = custom_sns_mappings.get("sns_topics", [])

        # Format each topic ARN and create a new list
        formatted_topics = [
            topic.format(region=DEFAULT_REGION, account_id=self.lz.account_id)
            for topic in sns_topic_arns
        ]

        return formatted_topics

    def get_custom_metrics(self) -> List[Metric]:
        """Get custom metrics from configuration."""
        for custom_metric in self._custom_configs.get("metrics", []):
            metrics = self._get_metrics_in_namespace(custom_metric)
            self._custom_metrics.extend(metrics)
        return self._custom_metrics

    def _update_dimensions(
        self, metric: Metric, resource: Resource
    ) -> List[Dict[str, str]]:
        """Get dimensions for a specific resource."""
        format_vars = {
            "instance_id": resource.id,
            "name": resource.name,
            "type": resource.type,
        }

        # Handle custom metrics case first
        if metric.name in self._custom_configs.get("dimensions", {}).get("metrics", []):
            return [
                dim
                for metric in self._custom_metrics
                if metric.dimensions.get("InstanceId") == resource.id
                for dim in (
                    [metric.dimensions]
                    if isinstance(metric.dimensions, dict)
                    else metric.dimensions
                )
            ]

        # Handle standard dimension updates
        try:
            updated_dimensions = copy.deepcopy(metric.dimensions)
            if not isinstance(updated_dimensions, list):
                updated_dimensions = [updated_dimensions]

            for dimension in updated_dimensions:
                if not isinstance(dimension, dict):
                    logger.warning(f"Invalid dimension format: {dimension}")
                    continue

                if "Value" not in dimension:
                    continue

                try:
                    dimension["Value"] = dimension["Value"].format(**format_vars)
                except KeyError as e:
                    logger.warning(
                        f"Missing format variable {e} for dimension {dimension}. "
                        f"Available variables: {list(format_vars.keys())}"
                    )
                except ValueError as e:
                    logger.warning(
                        f"Invalid format string in dimension {dimension}: {e}"
                    )

            return updated_dimensions

        except Exception as e:
            logger.error(f"Failed to update dimensions: {e}")
            return []

    # ---- Alarm Creation Methods ----

    def create_alarm_definition(
        self, alarm: AlarmConfigs, resource: Resource
    ) -> Optional[AlarmConfigs]:
        """Create or update alarm definition for a specific resource and metric."""
        try:
            # Sanitize metric name for alarm name construction
            sanitized_metric_name = alarm.metric.name.replace(" ", "").replace("%", "")
            alarm_name = f"{self.lz.name}-{resource.type}-{resource.name}-{sanitized_metric_name}"
            logger.debug(f"Constructing alarm definition for: {alarm_name}")

            # Early returns for invalid cases
            if self._is_alarm_exists(alarm_name):
                logger.info(f"Alarm {alarm_name} already exists, skipping creation")
                return None

            threshold = self._threshold_configs.get(resource.type, {}).get(
                alarm.metric.name
            )
            if threshold is None:
                logger.warning(
                    f"No threshold configured for {resource.type}.{alarm.metric.name}, "
                    f"skipping alarm creation"
                )
                return None

            # Create new alarm configuration
            new_alarm = copy.deepcopy(alarm)  # Prevent modifying the original config
            new_alarm.name = alarm_name
            new_alarm.description = f"Alarm for {alarm.metric.name} on {resource.name}"
            new_alarm.metric.dimensions = self._update_dimensions(
                alarm.metric, resource
            )
            new_alarm.threshold_value = threshold
            new_alarm.sns_topic_arns = self._get_sns_topics(
                resource.type, alarm.metric.name
            )

            logger.debug(f"Successfully created alarm definition for {alarm_name}")
            return new_alarm

        except Exception as e:
            logger.error(
                f"Failed to create alarm definition for {resource.id}: {str(e)}",
                exc_info=True,
            )
            return None

    def create_alarm_definitions(self, resource: Resource) -> List[AlarmConfigs]:
        """Create alarm definitions for all metrics of a specific resource."""
        try:
            logger.debug(f"Creating alarm definitions for resource: {resource.id}")

            # Get alarm configs for resource type
            alarms = self._alarm_configs.get(resource.type, [])
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
                f"Failed to create alarm definitions for resource {resource.id}: {str(e)}",
                exc_info=True,
            )
            return []

    def create_all_alarm_definitions(self) -> List[AlarmConfigs]:
        """Create alarm definitions for all resources."""
        try:
            logger.info(
                f"Creating alarm definitions for {len(self.resources)} resources"
            )

            # Process resources in parallel for better performance
            with ThreadPoolExecutor(max_workers=DEFAULT_MAX_WORKERS) as executor:
                future_to_resource = {
                    executor.submit(self.create_alarm_definitions, resource): resource
                    for resource in self.resources
                }

                all_alarms = []
                for future in as_completed(future_to_resource):
                    resource = future_to_resource[future]
                    try:
                        alarm_defs = future.result()
                        if alarm_defs:
                            all_alarms.extend(alarm_defs)
                    except Exception as e:
                        logger.error(
                            f"Failed to process resource {resource.id}: {str(e)}",
                            exc_info=True,
                        )

            logger.info(
                f"Successfully created {len(all_alarms)} alarm definitions in total"
            )
            return all_alarms

        except Exception as e:
            logger.error(
                f"Failed to create all alarm definitions: {str(e)}", exc_info=True
            )
            return []

    # ---- Alarms Deployment Methods ----

    def _deploy_single_alarm(self, session: AWSSession, alarm: AlarmConfigs) -> None:
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
            logger.error(f"Error deploying alarm {alarm.name}: {str(e)}")
            raise

    def deploy_alarms(self, alarms: List[AlarmConfigs]) -> None:
        """Deploy alarms in parallel batches."""
        with ThreadPoolExecutor(max_workers=DEFAULT_MAX_WORKERS) as executor:
            futures = {
                executor.submit(
                    self._deploy_single_alarm, self.session, alarm
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
            self.scan_existing_alarms()
        return alarm_name in self._existing_alarms

    def scan_existing_alarms(self) -> Set[str]:
        """Scan and cache existing alarms in the AWS account."""
        resource_scanner = ResourceScanner(self.session, DEFAULT_REGION)
        if not self._existing_alarms:
            scanned_alarms = resource_scanner.get_resources_by_tag(
                tags={MANAGE_BY_TAG_KEY: CMS_MANAGED_TAG_VALUE},
                resource_config={
                    "CloudWatch": {"type": "cloudwatch:alarm", "delimiter": ":"}
                },
            )
            self._existing_alarms = {alarm.name for alarm in scanned_alarms}
        return self._existing_alarms

    def _build_alarm_tags(self, alarm_name: str) -> List[Dict[str, str]]:
        """Create standardized tags for CloudWatch alarms."""
        return [
            {"Key": "Name", "Value": alarm_name},
            {"Key": "AppID", "Value": self.lz.app_id},
            {"Key": "Environment", "Value": self.lz.env},
            {"Key": "ResourceType", "Value": "CloudWatchAlarm"},
            {"Key": MANAGE_BY_TAG_KEY, "Value": CMS_MANAGED_TAG_VALUE},
        ]

    def _get_metrics_in_namespace(self, custom_metric: Metric) -> List[Metric]:
        client = self.session.session.client("cloudwatch")

        metrics = client.list_metrics(
            Namespace=custom_metric.namespace,
            MetricName=custom_metric.name,
        ).get("Metrics", [])

        return [
            Metric(
                namespace=custom_metric.namespace,
                name=metric["MetricName"],
                dimensions=metric["Dimensions"],
            )
            for metric in metrics
        ]
