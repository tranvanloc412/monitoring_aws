"""AWS-specific constants used across the aws_manager package."""

from typing import Final, Dict, List

# AWS Region and Roles
DEFAULT_REGION: Final[str] = "ap-southeast-1"

# CMS Managed Tags
MANAGE_BY_TAG_KEY: Final[str] = "managed_by"
CMS_MANAGED_TAG_VALUE: Final[str] = "CMS"

### CloudWatch constants ###
# Monitoring categories
CATEGORIES: Final[Dict[str, str]] = {
    "A": "CAT_A",
    "B": "CAT_B",
    "C": "CAT_C",
    "D": "CAT_D",
}

# SNS topics
CMS_SNS_TOPIC_LOW: Final[str] = (
    "arn:aws:sns:ap-southeast-1:891377130283:HIPNotifyTopicLow"
)
CMS_SNS_TOPIC_HIGH: Final[str] = (
    "arn:aws:sns:ap-southeast-1:891377130283:HIPNotifyTopicHigh"
)
CMS_SNS_TOPIC_MEDIUM: Final[str] = (
    "arn:aws:sns:ap-southeast-1:891377130283:HIPNotifyTopicMedium"
)
