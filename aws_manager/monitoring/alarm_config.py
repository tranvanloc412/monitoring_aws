from dataclasses import dataclass, field
from typing import Dict, Set, List, Optional, Union


@dataclass
class MetricConfig:
    """Settings for a CloudWatch metric

    Attributes:
        name: The name of the metric
        namespace: The namespace of the metric (e.g., 'AWS/EC2')
        dimensions: List of key-value pairs that identify the metric
    """

    name: str
    namespace: str
    dimensions: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class ResourceMetrics:
    """Manages CloudWatch metrics for different AWS resources"""

    def __init__(self) -> None:
        self.metrics: Dict[str, List[MetricConfig]] = {}

    def add_metric(self, metric: MetricConfig) -> bool:
        """Add a metric configuration for a resource.

        Returns:
            bool: True if metric was added successfully, False otherwise
        """
        instance_dimensions = [
            d for d in metric.dimensions if d["Name"] == "InstanceId"
        ]
        if not instance_dimensions:
            return False

        resource_id = instance_dimensions[0]["Value"]
        if resource_id not in self.metrics:
            self.metrics[resource_id] = []
        if metric not in self.metrics[resource_id]:
            self.metrics[resource_id].append(metric)
        return True

    def is_metric_exists(self, metric: MetricConfig, resource_id: str) -> bool:
        """Check if a metric exists for a specific resource."""
        return metric in self.metrics.get(resource_id, [])

    def get_metrics(self, resource_id: str) -> List[MetricConfig]:
        return self.metrics.get(resource_id, [])

    def __bool__(self) -> bool:
        return bool(self.metrics)


@dataclass
class AlarmConfig:
    """Configuration for a CloudWatch alarm

    Attributes:
        metric: The metric to monitor
        statistic: The statistic to apply (e.g., 'Average', 'Sum')
        comparison_operator: The comparison operator (e.g., 'GreaterThanThreshold')
        unit: The unit of measurement
        period: The period in seconds over which to evaluate
        evaluation_periods: Number of periods to evaluate
        description: Optional alarm description
        threshold_value: The threshold value to compare against
        name: Unique name for the alarm
        sns_topic_arns: List of SNS topics to notify
    """

    metric: MetricConfig
    statistic: str
    comparison_operator: str
    unit: str
    period: int
    evaluation_periods: int
    description: str = ""
    threshold_value: float = 0
    name: str = ""
    sns_topic_arns: List[str] = field(default_factory=list)

    def metric_name(self) -> str:
        """Generate a cleaned metric name without spaces and special characters."""
        return self.metric.name.translate(str.maketrans("", "", " %"))

    def __bool__(self) -> bool:
        return bool(self.name)


@dataclass
class Alarms:
    """Configuration for a list of CloudWatch alarms"""

    def __init__(self) -> None:
        self.alarms: List[AlarmConfig] = []

    def add_alarm(self, alarms: Union[AlarmConfig, "Alarms"]) -> None:
        """Add one or more alarms to the collection."""
        if isinstance(alarms, Alarms):
            # Avoid duplicate alarms
            for alarm in alarms.alarms:
                if not self.find(alarm.name):
                    self.alarms.append(alarm)
        elif not self.find(alarms.name):
            self.alarms.append(alarms)

    def remove_alarm(self, name: str) -> bool:
        """Remove an alarm by its name."""
        alarm = self.find(name)
        if alarm:
            self.alarms.remove(alarm)
            return True
        return False

    def get_alarms_by_metric(self, metric_name: str) -> List[AlarmConfig]:
        return [alarm for alarm in self.alarms if alarm.metric.name == metric_name]

    def find(self, name: str) -> Optional[AlarmConfig]:
        """Find an alarm by its name."""
        for alarm in self.alarms:
            if alarm.name == name:
                return alarm
        return None

    def __bool__(self) -> bool:
        return bool(self.alarms)

    def __len__(self) -> int:
        return len(self.alarms)
