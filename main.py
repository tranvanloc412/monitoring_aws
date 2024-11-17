from pathlib import Path
from typing import Optional
import logging

from aws_manager import (
    LandingZoneManager,
    SessionManager,
    ResourceScanner,
    AlarmManager,
)
from constants import (
    LZ_CONFIG,
    ALARM_SETTINGS,
    CATEGORY_CONFIGS,
    CUSTOM_SETTINGS,
    LOG_FORMAT,
    CMS_SPOKE_ROLE,
    DEFAULT_REGION,
    DEFAULT_SESSION,
)
from cli_parser import CliParser
from logger import LoggerSetup
from utils import validate_config_paths

# Config Paths
BASE_DIR = Path(__file__).parent
CONFIG_PATHS = {
    "lz": BASE_DIR / LZ_CONFIG,
    "alarm_settings": BASE_DIR / ALARM_SETTINGS,
    "category_configs": BASE_DIR / CATEGORY_CONFIGS,
    "custom_settings": BASE_DIR / CUSTOM_SETTINGS,
}


def load_lz_config(logger: logging.Logger) -> LandingZoneManager:
    """Setup logging and load configurations."""

    if not validate_config_paths(CONFIG_PATHS, logger):
        raise FileNotFoundError("Landing zone configuration file not found")

    return LandingZoneManager(CONFIG_PATHS["lz"])


def process_landing_zone(lz, args, logger: logging.Logger) -> None:
    """Process a single landing zone based on the provided arguments."""
    logger.info(f"Processing landing zone: {lz}")
    try:
        session = SessionManager.get_or_create_session(
            lz=lz,
            role=CMS_SPOKE_ROLE,
            region=DEFAULT_REGION,
            role_session_name=DEFAULT_SESSION,
        )

        if not session:
            logger.warning(f"Failed to create session for landing zone: {lz}")
            return

        resource_scanner = ResourceScanner(session, DEFAULT_REGION)
        resources = resource_scanner.get_managed_resources(lz.env)
        logger.info(f"Found {len(resources)} resources to monitor")

        alarm_manager = AlarmManager(
            landing_zone=lz,
            aws_session=session,
            monitored_resources=resources,
            alarm_config_path=CONFIG_PATHS["alarm_settings"],
            category_config_path=CONFIG_PATHS["category_configs"],
            custom_config_path=CONFIG_PATHS["custom_settings"],
        )

        # Map actions to their corresponding methods
        action_methods = {
            "create": create_alarms,
            "scan": scan_resources,
            "delete": delete_alarms,
        }

        # Handle dry run or execute the actual action
        if args.dry_run:
            dry_run(alarm_manager, logger, lz, args.action)
        else:
            action_method = action_methods.get(args.action)
            if action_method:
                action_method(alarm_manager, logger, lz)
            else:
                logger.error(f"Unknown action: {args.action}")

    except Exception as e:
        logger.error(f"Error processing landing zone {lz}: {e}")


def create_alarms(alarm_manager, logger, lz):
    """Create and deploy alarms for the landing zone."""
    alarm_definitions = alarm_manager.create_all_alarm_definitions()
    logger.info(f"Created {len(alarm_definitions)} alarm definitions")
    alarm_manager.deploy_alarms(alarm_definitions)
    logger.info(f"Successfully deployed alarms for landing zone: {lz}")


def scan_resources(alarm_manager, logger, lz):
    """Scan resources for the landing zone."""
    logger.info(f"Scanning resources for landing zone: {lz}")
    alarm_manager.scan_alarms()
    logger.info(f"Successfully scanned resources for landing zone: {lz}")


def delete_alarms(alarm_manager, logger, lz):
    """Delete alarms for the landing zone."""
    logger.info(f"Deleting alarms for landing zone: {lz}")
    alarm_manager.delete_alarms()
    logger.info(f"Successfully deleted alarms for landing zone: {lz}")


def dry_run(alarm_manager, logger, lz, action):
    """Simulate the execution of the specified action."""
    logger.info(f"[DRY RUN] Simulating '{action}' for landing zone: {lz}")

    if action == "create":
        alarm_definitions = alarm_manager.create_all_alarm_definitions()
        logger.info(
            f"[DRY RUN] Would create {len(alarm_definitions)} alarm definitions"
        )
        # Log sample of what would be created
        for alarm in alarm_definitions[:3]:  # Show first 3 as example
            logger.info(f"[DRY RUN] Would create alarm: {alarm}")

    elif action == "delete":
        logger.info(f"[DRY RUN] Would delete all alarms for landing zone: {lz}")

    elif action == "scan":
        logger.info(f"[DRY RUN] Would scan resources for landing zone: {lz}")

    logger.info(f"[DRY RUN] Completed simulation for landing zone: {lz}")


def main() -> None:
    """
    Main execution function for CMS Monitoring.
    Handles the setup and deployment of alarms across all landing zones.
    """
    args = CliParser.parse_arguments()
    logger = LoggerSetup(LOG_FORMAT).get_logger()
    try:
        logger.info(
            f"Starting CMS Monitoring for landing zone: {args.lz} with action: {args.action}"
        )

        CliParser.validate_production_lz(args, logger)

        landing_zone_manager = load_lz_config(logger)

        if args.lz.lower() == "all":
            landing_zones = landing_zone_manager.get_all_landing_zones()
        else:
            landing_zones = [landing_zone_manager.get_landing_zone(args.lz)]

        for lz in landing_zones:
            process_landing_zone(lz, args, logger)

        logger.info("CMS Monitoring completed successfully")

    except Exception as e:
        logger.error(f"Fatal error in main execution: {e}")
        raise


if __name__ == "__main__":
    main()
