# ====================================================
# Standard Library Imports
# ====================================================
import boto3
import logging
from pathlib import Path
from copy import deepcopy
from typing import Any, Dict, List, Optional, Union, Set
from concurrent.futures import ThreadPoolExecutor, as_completed

# ====================================================
# Internal Module Imports
# ====================================================
from landing_zone import LandingZone
from resource_discovery.resource_plugins.resource import Resource
from resource_discovery.resource_scanner import ResourceScanner
from .alarm_config import AlarmDefinition, Metric, CWAgent
from .config_loader import ConfigLoader
from .constants import *
from utils import validate_config_paths

# ====================================================
# Logger Setup
# ====================================================
logger = logging.getLogger(__name__)


# ====================================================
# AlarmManager Class Definition
# ====================================================
class AlarmManager:
    """
    Manages CloudWatch alarms for AWS resources.
    Loads configuration files, caches existing alarms and metrics,
    and deploys new alarms for monitored resources.
    """

    # ----------------------------
    # Initialization Methods
    # ----------------------------
    def __init__(
        self,
        landing_zone: LandingZone,
        session: boto3.Session,
        alarm_config_path: Path,
        category_config_path: Path,
        custom_config_path: Path,
        monitored_resources: List[Resource],
    ) -> None:
        self.landing_zone = landing_zone
        self.session = session
        self.monitored_resources = monitored_resources

        # Load configuration files using ConfigLoader
        config_loader = ConfigLoader(
            alarm_config_path=alarm_config_path,
            category_config_path=category_config_path,
            custom_config_path=custom_config_path,
        )
        self._alarm_configs = config_loader.alarm_configs
        self._thresholds = config_loader.category_configs.get(
            self.landing_zone.category, {}
        ).get("thresholds", {})
        self._sns_topics = config_loader.category_configs.get(
            self.landing_zone.category, {}
        ).get("sns_topic_arns", [])

        # Initialize caches:
        # 1. Cache monitored EC2 instance IDs (used for CWAgent metric filtering)
        self._monitored_ec2: Set[str] = {
            resource.id
            for resource in self.monitored_resources
            if resource.type == "EC2"
        }
        # 2. Cache existing alarm names to avoid re-creating alarms
        self._existing_alarms: Set[str] = self._initialize_alarm_cache()
        # 3. Initialize and populate CWAgent metrics cache via a CWAgent instance
        self._cwagent_metrics = CWAgent()
        self._fetch_cwagent_metrics()
        # 4. Cache mapping for RDS allocated storage (instance ID -> allocated storage in GiB)
        self._rds_storage_map = self._get_rds_storage_map()

    # ----------------------------
    # Cache Initialization Functions
    # ----------------------------
    def _initialize_alarm_cache(self) -> Set[str]:
        """
        Scan for existing CloudWatch alarms once and cache their names.
        """
        logger.info("Scanning for existing CloudWatch alarms...")
        scanner = ResourceScanner(self.session)
        scanned_alarms = scanner.scan_resources(
            service_name="cw", lz_name=self.landing_zone.name
        )
        cached = {alarm.name for alarm in scanned_alarms}
        logger.info(f"Cached {len(cached)} existing alarms.")
        return cached

    def _get_rds_storage_map(self) -> Dict[str, int]:
        """
        Retrieve a mapping of RDS instance IDs to their allocated storage in GiB.
        """
        storage_map = {}
        try:
            rds_client = self.session.client("rds")
            response = rds_client.describe_db_instances()
            for instance in response.get("DBInstances", []):
                storage_map[instance["DBInstanceIdentifier"]] = instance[
                    "AllocatedStorage"
                ]
            return storage_map
        except Exception as e:
            logger.error(f"Failed to fetch RDS storage information: {e}")
            return {}

    def _fetch_cwagent_metrics(self) -> None:
        """
        Fetch and cache CWAgent metrics for EC2 instances.
        Uses the CWAGENT_METRICS dictionary to map metric names to distinct dimension keys.
        """
        client = self.session.client("cloudwatch")
        for metric_name, distinct_dimension_key in CWAGENT_METRICS.items():
            try:
                response = client.list_metrics(
                    Namespace="CWAgent", MetricName=metric_name
                )
                metrics = response.get("Metrics", [])
                for cwagent_metric in metrics:
                    metric_config = Metric(
                        name=cwagent_metric.get("MetricName", ""),
                        namespace=cwagent_metric.get("Namespace", ""),
                        dimensions=cwagent_metric.get("Dimensions", []),
                    )
                    self._cwagent_metrics.add_metric(
                        metric_config, self._monitored_ec2, distinct_dimension_key
                    )
            except Exception as e:
                logger.error(f"Failed to fetch CWAgent metric {metric_name}: {e}")

    # ----------------------------
    # Alarm Scan and Delete Methods
    # ----------------------------
    def scan_alarms(self) -> Set[str]:
        """
        Return the cached set of existing alarm names.
        """
        return self._existing_alarms

    def delete_alarms(self, alarm_names: Optional[List[str]] = None) -> None:
        """
        Delete CloudWatch alarms.

        If alarm_names is not provided, delete all alarms in the cached set.

        Args:
            alarm_names (Optional[List[str]]): List of alarm names to delete.
        """
        cloudwatch = self.session.client("cloudwatch")
        if alarm_names is None:
            alarm_names = list(self.scan_alarms())
            logger.info(f"Retrieved {len(alarm_names)} alarms from cache for deletion.")
        if alarm_names:
            try:
                cloudwatch.delete_alarms(AlarmNames=alarm_names)
                logger.info(f"Successfully deleted alarms: {alarm_names}")
                self._existing_alarms -= set(alarm_names)
            except Exception as e:
                logger.error(f"Error deleting alarms {alarm_names}: {e}")
                raise
        else:
            logger.info("No alarms to delete.")

    # ----------------------------
    # Alarm Deployment Methods
    # ----------------------------
    def deploy_alarms(self, resource: Resource) -> None:
        """
        Deploy alarms for a given resource.
        Alarm definitions are generated based on the resource type and then deployed in parallel.
        """
        alarm_configs = self._alarm_configs.get(resource.type, [])
        cloudwatch = self.session.client("cloudwatch")
        standard_alarm_defs: List[AlarmDefinition] = []
        for alarm in alarm_configs:
            result = self._update_single_alarm_definition(alarm, resource)
            if result:
                if isinstance(result, list):
                    standard_alarm_defs.extend(result)
                else:
                    standard_alarm_defs.append(result)
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(self._deploy_single_alarm, alarm_def, cloudwatch)
                for alarm_def in standard_alarm_defs
            ]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Error in parallel alarm deployment: {e}")
                    raise

    def _update_single_alarm_definition(
        self, alarm: AlarmDefinition, resource: Resource
    ) -> Optional[Union[AlarmDefinition, List[AlarmDefinition]]]:
        """
        Create an alarm definition for a resource.
        Handles special cases for RDS storage and EC2 CWAgent storage metrics.

        Returns:
            A single AlarmDefinition or a list of them, or None if the alarm exists
            or required configuration is missing.
        """
        base_alarm_name = f"{self.landing_zone.name}-{resource.type}-{resource.name}-{alarm.metric_name()}"
        if self._is_alarm_exists(base_alarm_name):
            logger.info(f"Alarm {base_alarm_name} already exists, skipping creation")
            return None

        if resource.type == "RDS" and alarm.metric.name == "FreeStorageSpace":
            return self._process_rds_storage_alarm(alarm, resource)
        elif resource.type == "EC2" and alarm.metric.namespace == "CWAgent":
            return self._process_ec2_cwagent_alarm(alarm, resource)

        threshold = self._get_threshold_value(resource.type, alarm.metric.name)
        if threshold is None:
            logger.warning(
                f"Missing threshold config for {resource.type}.{alarm.metric.name}"
            )
            return None

        return self._create_alarm_definition(alarm, resource, threshold)

    def _create_alarm_definition(
        self,
        alarm: AlarmDefinition,
        resource: Resource,
        threshold: float,
        distinct_value: str = "",
    ) -> AlarmDefinition:
        """
        Helper method to create a standard AlarmDefinition.
        """
        base_alarm_name = f"{self.landing_zone.name}-{resource.type}-{resource.name}-{alarm.metric_name()}"
        alarm_name = (
            f"{base_alarm_name}-{distinct_value}" if distinct_value else base_alarm_name
        )
        return AlarmDefinition(
            metric=Metric(
                name=alarm.metric.name,
                namespace=alarm.metric.namespace,
                dimensions=self._get_dimensions(resource),
            ),
            statistic=alarm.statistic,
            comparison_operator=alarm.comparison_operator,
            unit=alarm.unit,
            period=alarm.period,
            evaluation_periods=alarm.evaluation_periods,
            description=f"Alarm for {alarm.metric.name} on {resource.name}",
            threshold_value=threshold,
            name=alarm_name,
            sns_topic_arns=self._get_sns_topics(),
        )

    def _process_rds_storage_alarm(
        self, alarm: AlarmDefinition, resource: Resource
    ) -> Optional[AlarmDefinition]:
        """
        Process RDS storage alarms:
        Convert a percentage threshold to a byte threshold using allocated storage.
        """
        allocated_storage = self._rds_storage_map.get(resource.id, 0)
        threshold_percentage = self._get_threshold_value(
            resource.type, alarm.metric.name
        )
        if threshold_percentage is None or allocated_storage == 0:
            logger.warning(f"Cannot process RDS storage alarm for {resource.id}")
            return None
        computed_threshold = (allocated_storage * 1024 * 1024 * 1024) * (
            threshold_percentage / 100
        )
        return self._create_alarm_definition(alarm, resource, computed_threshold)

    def _process_ec2_cwagent_alarm(
        self, alarm: AlarmDefinition, resource: Resource
    ) -> Optional[List[AlarmDefinition]]:
        """
        Process EC2 CWAgent storage alarms:
        For each CWAgent metric associated with the resource, generate a unique alarm definition.

        Returns:
            A list of AlarmDefinition objects, or None if none could be created.
        """
        metrics = self._cwagent_metrics.get_instance_metrics(resource.id)
        if not metrics:
            logger.warning(f"No CWAgent storage metrics found for {resource.id}")
            return None

        alarm_definitions = []
        for key, metric_config in metrics.items():
            threshold = self._get_threshold_value(resource.type, alarm.metric.name)
            if threshold is None:
                logger.warning(
                    f"Missing threshold for {resource.type}.{alarm.metric.name}"
                )
                continue

            distinct_value = ""
            if metric_config.distinct_dimension:
                distinct_value = next(
                    iter(metric_config.distinct_dimension.values()), "unknown"
                )

            alarm_name = f"{self.landing_zone.name}-{resource.type}-{resource.name}-{alarm.metric_name()}-{distinct_value}"
            if self._is_alarm_exists(alarm_name):
                logger.info(f"Alarm {alarm_name} already exists, skipping creation")
                continue

            new_alarm = self._create_alarm_definition(
                alarm, resource, threshold, distinct_value
            )
            alarm_definitions.append(new_alarm)

        return alarm_definitions if alarm_definitions else None

    # ----------------------------
    # Helper Methods
    # ----------------------------
    def _is_alarm_exists(self, alarm_name: str) -> bool:
        """
        Check if an alarm with the given name already exists (cached).

        Args:
            alarm_name (str): The name of the alarm.

        Returns:
            bool: True if the alarm exists, False otherwise.
        """
        return alarm_name in self._existing_alarms

    def _get_threshold_value(
        self, resource_type: str, metric_name: str
    ) -> Optional[float]:
        """
        Retrieve the threshold configuration for a given resource type and metric.

        Args:
            resource_type (str): The type of resource (e.g., "EC2", "RDS").
            metric_name (str): The name of the metric.

        Returns:
            Optional[float]: The threshold value if found, otherwise None.
        """
        resource_thresholds = self._thresholds.get(resource_type, {})
        threshold = resource_thresholds.get(metric_name)
        if threshold is None:
            logger.warning(f"No threshold found for {resource_type}.{metric_name}")
            return None
        return threshold

    def _get_dimensions(self, resource: Resource) -> List[Dict[str, str]]:
        """
        Construct a list of dimensions for the resource based on the DIMENSION_KEYS mapping.

        For each key in DIMENSION_KEYS for the resource type:
          - For EC2 and RDS, use resource.id.
          - For ALB, use resource.id for 'LoadBalancer' and use the first related resource
            for 'TargetGroup' (or 'unknown' if not available).

        Args:
            resource (Resource): The resource for which to build dimensions.

        Returns:
            List[Dict[str, str]]: A list of dimension dictionaries.
        """
        dims = []
        keys = DIMENSION_KEYS.get(resource.type, [])
        for key in keys:
            if resource.type in ["EC2", "RDS"]:
                value = resource.id
            elif resource.type == "ALB":
                if key == "LoadBalancer":
                    value = resource.id
                elif key == "TargetGroup":
                    value = (
                        resource.related_resources[0]
                        if resource.related_resources
                        else "unknown"
                    )
                else:
                    value = "unknown"
            else:
                value = "unknown"
            dims.append({"Name": key, "Value": value})
        return dims

    def _get_sns_topics(self) -> List[str]:
        """
        Construct full SNS topic ARNs based on the default region and landing zone account.

        Returns:
            List[str]: A list of fully qualified SNS topic ARNs.
        """
        sns_prefix = f"arn:aws:sns:{DEFAULT_REGION}:{self.landing_zone.id}:"
        return [sns_prefix + topic for topic in self._sns_topics]

    def _deploy_single_alarm(
        self, alarm_definition: AlarmDefinition, cloudwatch: Any
    ) -> None:
        """
        Deploy a single alarm to CloudWatch using the put_metric_alarm API.
        Logs success or failure.

        Args:
            alarm_definition (AlarmDefinition): The alarm configuration to deploy.
            cloudwatch (Any): A CloudWatch client.
        """
        try:
            cloudwatch.put_metric_alarm(
                AlarmName=alarm_definition.name,
                MetricName=alarm_definition.metric.name,
                Namespace=alarm_definition.metric.namespace,
                Dimensions=alarm_definition.metric.dimensions,
                Statistic=alarm_definition.statistic,
                Period=alarm_definition.period,
                EvaluationPeriods=alarm_definition.evaluation_periods,
                Threshold=alarm_definition.threshold_value,
                ComparisonOperator=alarm_definition.comparison_operator,
                ActionsEnabled=True,
                AlarmActions=alarm_definition.sns_topic_arns,
                AlarmDescription=alarm_definition.description,
                Unit=alarm_definition.unit,
                Tags=[{"Key": "managed_by", "Value": "CMS"}],
            )
            logger.info(f"Successfully deployed alarm: {alarm_definition.name}")
        except Exception as e:
            logger.error(f"Failed to deploy alarm {alarm_definition.name}: {e}")
            raise


# ====================================================
# End of AlarmManager Class
# ====================================================
