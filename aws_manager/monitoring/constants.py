"""AWS-specific constants for CloudWatch alarm management."""

from typing import Final, Dict

# AWS CloudWatch Constants
DEFAULT_REGION: Final[str] = "ap-southeast-1"
DEFAULT_MAX_WORKERS: Final[int] = 3
MANAGE_BY_TAG_KEY: Final[str] = "managed_by"
CMS_MANAGED_TAG_VALUE: Final[str] = "CMS"

DIMENSION_KEYS: Final[Dict[str, str]] = {
    "EC2": "InstanceId",
    "RDS": "DBInstanceIdentifier",
}
