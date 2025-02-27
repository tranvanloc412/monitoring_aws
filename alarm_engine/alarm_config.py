from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional


@dataclass
class Metric:
    """Settings for a CloudWatch metric"""

    name: str
    namespace: str
    dimensions: List[Dict[str, str]] = field(default_factory=list)
    # distinct dimension for cwagent metrics
    distinct_dimension: Optional[Dict[str, str]] = None


@dataclass
class CWAgent:
    """Manages CloudWatch metrics in CWAgent namespace for EC2 resources"""

    def __init__(self) -> None:
        # First key: InstanceId, Second key: metric_name
        self.metrics: Dict[str, Dict[str, List[Metric]]] = {}

    def __repr__(self) -> str:
        return f"CWAgent(metrics={self.metrics})"

    def add_metric(
        self,
        metric: Metric,
        instance_ids: set[str],
        distinct_dimension_key: str,
    ) -> bool:
        """Add a metric configuration for a resource"""
        try:
            dimensions = {d["Name"]: d["Value"] for d in metric.dimensions}
        except (KeyError, TypeError):
            return False

        if not dimensions or "InstanceId" not in dimensions:
            return False

        if distinct_dimension_key:
            if distinct_dimension_key not in dimensions:
                return False
            distinct_dimension_value = dimensions[distinct_dimension_key]
            metric.distinct_dimension = {
                distinct_dimension_key: distinct_dimension_value
            }

        instance_id = dimensions["InstanceId"]
        if instance_id not in instance_ids:
            return False

        metric_list = self.metrics.setdefault(instance_id, {}).setdefault(
            metric.name, []
        )
        metric_list.append(metric)
        return True

    def get_instance_metrics(self, instance_id: str) -> Dict[str, List[Metric]]:
        return self.metrics.get(instance_id, {})

    def get_metrics(self, instance_id: str, metric_name: str) -> Optional[List[Metric]]:
        return self.metrics.get(instance_id, {}).get(metric_name, None)

    def __bool__(self) -> bool:
        return bool(self.metrics)


@dataclass
class AlarmDefinition:
    """Configuration for a CloudWatch alarm.

    Attributes:
        metric (MetricConfig): The metric configuration for the alarm
        statistic (str): The statistic to apply to the metric (e.g., 'Average', 'Sum')
        comparison_operator (str): The comparison operator for the threshold (e.g., 'GreaterThanThreshold')
        unit (str): The unit of measurement for the metric
        period (int): The period in seconds over which the metric is evaluated
        evaluation_periods (int): The number of periods to evaluate before triggering the alarm
        description (str): Optional description of the alarm
        threshold_value (float): The threshold value to compare against
        name (str): The name of the alarm
        sns_topic_arns (List[str]): List of SNS topic ARNs to notify when alarm triggers
    """

    metric: Metric
    statistic: str
    comparison_operator: str
    unit: str
    period: int
    evaluation_periods: int
    description: str = ""
    threshold_value: float = 0.0
    name: str = ""
    sns_topic_arns: List[str] = field(default_factory=list)

    def metric_name(self) -> str:
        """Generate a cleaned metric name without spaces and special characters"""
        return self.metric.name.translate(str.maketrans("", "", " %"))

    def __bool__(self) -> bool:
        """True if the alarm has a name, False otherwise"""
        return bool(self.name)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AlarmDefinition":
        """Create an AlarmDefinition instance from a dictionary."""
        metric_config = Metric(
            name=data.get("metric_name", ""),
            namespace=data.get("namespace", ""),
            dimensions=data.get("dimensions", []),
        )

        return cls(
            name=data.get("name", ""),
            metric=metric_config,
            threshold_value=float(data.get("threshold", 0.0)),
            comparison_operator=data.get("comparison_operator", ""),
            statistic=data.get("statistic", "Average"),
            unit=data.get("unit", "Count"),
            period=int(data.get("period", 300)),
            evaluation_periods=int(data.get("evaluation_periods", 1)),
        )
