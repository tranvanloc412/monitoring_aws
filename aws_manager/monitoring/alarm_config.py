from dataclasses import dataclass, field
from typing import List, Optional, Union

from .metric_config import MetricConfig


@dataclass
class AlarmConfig:
    """Configuration for a CloudWatch alarm"""

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
    """Configuration for a set of CloudWatch alarms"""

    def __init__(self) -> None:
        self.alarms: List[AlarmConfig] = []

    def add_alarm(self, alarms: Union[AlarmConfig, "Alarms"]) -> None:
        """Add one or more alarms to the collection.
        Allows adding duplicates."""

        if isinstance(alarms, Alarms):
            self.alarms.extend(alarms.alarms)
        else:
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
