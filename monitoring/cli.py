import logging

from pathlib import Path
from typing import Dict, Optional
from aws_manager import *
from .ansible_runners.run_playbook import run_ansible_playbook
from .constants import CMS_JMP_ROLE, CONFIG_FILE_PATH

# Constants for paths
BASE_DIR = Path(__file__).parents[1]
CONFIG_FILE_PATH = BASE_DIR.joinpath(CONFIG_FILE_PATH)
ANSIBLE_FILE_PATH = BASE_DIR.joinpath("ansible")
PLAYBOOK_PATH = ANSIBLE_FILE_PATH.joinpath("site.yml")
INVENTORY_PATH = ANSIBLE_FILE_PATH.joinpath("inventory/hosts.ini")

# Set up the root logger
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Log Starting message
logger.info("--- Starting Monitoring CLI ---")


def load_landing_zone_configs() -> Dict[str, dict]:
    """
    Load landing zone configurations from the specified config file path.

    :return: Dictionary containing landing zone configurations.
    """
    LandingZoneManager.load_lz_configs(str(CONFIG_FILE_PATH))
    return LandingZoneManager.get_lz_configs()


def get_cms_landing_zone() -> Optional[LandingZone]:
    """
    Retrieve the CMS landing zone configuration from loaded configurations.

    :return: CMS LandingZone instance or None if not found.
    """
    cms_lz = LandingZoneManager.get_landing_zone("cms", "nonprod")
    if cms_lz:
        logger.info(f"Retrieved CMS landing zone: {cms_lz}")
    else:
        logger.error("CMS landing zone not found in configuration.")
    return cms_lz


def assume_role_for_landing_zone(lz: LandingZone) -> Optional[AWSSessionDetails]:
    """
    Assume the role for a specified landing zone and return the session details.

    :param lz: LandingZone instance for which to assume the role.
    :return: AWSSessionDetails if role assumption is successful, otherwise None.
    """
    session = assume_role(lz, CMS_JMP_ROLE)
    if session:
        logger.info(f"Assumed role successfully for {lz.name}")
    else:
        logger.error("Failed to assume role for the landing zone.")
    return session


def main() -> None:
    """
    Main function to load configurations, retrieve the CMS landing zone,
    assume role, and execute the Ansible playbook.
    """
    # Load landing zone configurations
    landing_zones = load_landing_zone_configs()
    logger.info(f"Loaded landing zones: {landing_zones.keys()}")

    # Retrieve CMS landing zone
    cms_lz = get_cms_landing_zone()
    if cms_lz is None:
        logger.error("Exiting due to missing CMS landing zone configuration.")
        return

    # Assume role for CMS landing zone
    assume_role_session = assume_role_for_landing_zone(cms_lz)
    if assume_role_session is None:
        logger.error("Exiting due to failure in assuming role.")
        return

    # Initialize the scanner
    scanner = ResourceScanner(region_name="ap-southeast-1")
    # Get resources managed by 'CM'
    managed_resources = scanner.get_managed_resources()

    # Print each resource's details
    for resource in managed_resources:
        logger.info(resource.to_dict())

    # Set up an example alarm configuration
    alarm_config = AlarmConfig(
        instance_name="CMSLIDA9001",
        instance_id="i-0edbded74c49e63a1",
        alarm_action="arn:aws:sns:ap-southeast-1:891377130283:HIPNotifyTopicLow",
        cpu_threshold=85,
        memory_threshold=75,
        disk_threshold=80,
        period=300,
        evaluation_periods=2,
    )
    
    resource_type = "EC2"
    metric_name = "CPUUtilization"

    # Fetch the global settings and category threshold
    metric_settings = metric_config.get_metric_settings(resource_type, metric_name)
    threshold = category_config.get_threshold(resource_type, metric_name)

    # Combine the values into a dictionary for use in alarm creation
    if metric_settings and threshold is not None:
        alarm_config = {
            "name": f"{resource_type}-{metric_name}-Alarm",
            "metric_name": metric_name,
            "threshold": threshold,
            "period": metric_settings["period"],
            "evaluation_periods": metric_settings["evaluation_periods"],
            "comparison_operator": "GreaterThanThreshold",
            "statistic": "Average",
            "unit": "Percent",
            "alarm_action": "arn:aws:sns:your-topic-arn"
        }
        print("Alarm Configuration:", alarm_config)
    else:
        print("Could not find configuration for the specified resource type and metric.")

    # Run the Ansible playbook
    # run_ansible_playbook(
    #     playbook_path=str(PLAYBOOK_PATH),
    #     inventory_path=str(INVENTORY_PATH),
    #     extra_vars=alarm_config.to_dict(),
    #     session=assume_role_session,
    # )


if __name__ == "__main__":
    main()
