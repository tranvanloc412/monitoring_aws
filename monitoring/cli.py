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

    # Run the Ansible playbook
    run_ansible_playbook(
        playbook_path=str(PLAYBOOK_PATH),
        inventory_path=str(INVENTORY_PATH),
        session=assume_role_session,
    )


if __name__ == "__main__":
    main()


# if get_current_assumed_role() == "AUR-Resource-AWS-cmshubnonprod-2FA-cms-jump-provision":
#     rs = assume_role(cms_lz["environment"]["nonprod"],  CMS_JMP_ROLE)
#     print(rs)
