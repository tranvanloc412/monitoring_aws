from dataclasses import dataclass, field
from typing import Any, Dict, List

import logging

logger = logging.getLogger(__name__)


@dataclass
class MetricConfig:
    """Settings for a CloudWatch metric"""

    name: str
    namespace: str
    dimensions: List[Dict[str, str]] = field(default_factory=list)


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
