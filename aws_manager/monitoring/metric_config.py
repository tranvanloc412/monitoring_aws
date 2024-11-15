from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class MetricConfig:
    """Settings for a CloudWatch metric"""

    name: str
    namespace: str
    dimensions: List[Dict[str, str]] = field(default_factory=list)
    # distinct dimension for cwagent metrics
    distinct_dimension: Optional[Dict[str, str]] = None


@dataclass
class CWAgentMetrics:
    """Manages CloudWatch metrics in CWAgent namespace for EC2 resources"""

    def __init__(self) -> None:
        # First key: InstanceId, Second key: metric_name
        self.metrics: Dict[str, Dict[str, List[MetricConfig]]] = {}

    def add_metric(
        self,
        metric: MetricConfig,
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

    def get_instance_metrics(self, instance_id: str) -> Dict[str, List[MetricConfig]]:
        return self.metrics.get(instance_id, {})

    def get_metrics(
        self, instance_id: str, metric_name: str
    ) -> Optional[List[MetricConfig]]:
        return self.metrics.get(instance_id, {}).get(metric_name, None)

    def __bool__(self) -> bool:
        return bool(self.metrics)
