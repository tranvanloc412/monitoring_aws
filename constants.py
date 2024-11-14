from pathlib import Path
from typing import Final

# File paths
CONFIG_DIR = "configs"
LZ_CONFIG = Path(CONFIG_DIR) / "landing_zone_configs.yml"
ALARM_SETTINGS = Path(CONFIG_DIR) / "alarm_settings.yml"
CATEGORY_CONFIGS = Path(CONFIG_DIR) / "category_configs.yml"
CUSTOM_SETTINGS = Path(CONFIG_DIR) / "custom_settings.yml"

# Logging
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# AWS
DEFAULT_REGION = "ap-southeast-1"
CMS_SPOKE_ROLE: Final[str] = "HIPCMSProvisionSpokeRole"
# CMS_HUB_ROLE: Final[str] = ""

# Monitoring
DEFAULT_SESSION: Final[str] = "CMSMonotoring"
