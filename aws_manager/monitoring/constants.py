"""AWS-specific constants for CloudWatch alarm management."""
from enum import Enum
from typing import Final, Dict, List

# AWS CloudWatch Constants
DEFAULT_REGION: Final[str] = "ap-southeast-1"
DEFAULT_MAX_WORKERS: Final[int] = 10
MANAGE_BY_TAG_KEY: Final[str] = "ManagedBy"
CMS_MANAGED_TAG_VALUE: Final[str] = "CMS"

class Category(str, Enum):
    A = "CAT_A"
    B = "CAT_B"
    C = "CAT_C"
    D = "CAT_D"

class SNSTopic(str, Enum):
    LOW = "HIPNotifySpokeCMSTopicLow"
    MEDIUM = "HIPNotifySpokeCMSTopicMedium"
    HIGH = "HIPNotifySpokeCMSTopicHigh"

# Resource-specific dimension mappings
DIMENSION_MAPPINGS: Final[Dict[str, List[Dict[str, str]]]] = {
    "EC2": [{"Name": "InstanceId", "Value": "{resource_id}"}],
    "RDS": [{"Name": "DBInstanceIdentifier", "Value": "{resource_id}"}],
    "ELB": [{"Name": "LoadBalancerName", "Value": "{resource_name}"}],
}
