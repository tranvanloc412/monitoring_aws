"""AWS-specific constants for CloudWatch alarm management."""

from typing import Final, Dict

# AWS CloudWatch Constants
DEFAULT_REGION: Final[str] = "ap-southeast-1"
DEFAULT_MAX_WORKERS: Final[int] = 5
MANAGE_BY_TAG_KEY: Final[str] = "managed_by"
CMS_MANAGED_TAG_VALUE: Final[str] = "CMS"

# Dimension keys for native metrics
DIMENSION_KEYS: Final[Dict[str, str]] = {
    "EC2": "InstanceId",
    "RDS": "DBInstanceIdentifier",
}

# CWAgent metrics : distinct dimensions keys
CWAGENT_METRICS: Final[Dict[str, str]] = {
    "mem_used_percent": "",
    "Memory % Committed Bytes In Use": "objectname",
    "disk_used_percent": "path",
    "LogicalDisk % Free Space": "instance",
}
