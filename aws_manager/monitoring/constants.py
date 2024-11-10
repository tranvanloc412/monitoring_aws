"""AWS-specific constants for CloudWatch alarm management."""

from enum import Enum
from typing import Final

# AWS CloudWatch Constants
DEFAULT_REGION: Final[str] = "ap-southeast-1"
DEFAULT_MAX_WORKERS: Final[int] = 10
MANAGE_BY_TAG_KEY: Final[str] = "managed_by"
CMS_MANAGED_TAG_VALUE: Final[str] = "CMS"


class Category(str, Enum):
    A = "CAT_A"
    B = "CAT_B"
    C = "CAT_C"
    D = "CAT_D"
