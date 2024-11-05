### Common constants ###
# File paths
CONFIG_DIR = "configs"
LZ_CONFIG = f"{CONFIG_DIR}/landing_zones.yml"
THRESHOLDS_CONFIG = f"{CONFIG_DIR}/thresholds.yml"
METRICS_CONFIG = f"{CONFIG_DIR}/metrics_settings.yml"

# Logging
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


### AWS constants ###
DEFAULT_REGION = "ap-southeast-1"
CMS_SPOKE_ROLE = "HIPCMSProvisionSpokeRole"
# CMS_HUB_ROLE = ""
DEFAULT_SESSION = "CMSMonotoring"

# CMS managed tag constants
MANAGED_TAG_KEY = "managed_by"
CMS_MANAGED_TAG_VALUE = "CMS"


### CloudWatch constants ###
# Monitoring categories
CATEGORIES = {"A": "CAT_A", "B": "CAT_B", "C": "CAT_C", "D": "CAT_D"}
