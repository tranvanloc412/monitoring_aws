import logging
from pathlib import Path
from typing import Optional

# Internal Module Imports
from session import SessionManager
from logger import LoggerSetup
from landing_zone import LandingZoneManager
from resource_discovery import ResourceScanner
from alarm_engine import AlarmManager
from utils import validate_config_paths
from cli_parser import CliParser, CliArgs

# Constants & Config
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

# Define configuration paths relative to BASE_DIR
BASE_DIR = Path(__file__).parent
CONFIG_PATHS = {
    "lz": BASE_DIR / LZ_CONFIG,
    "alarm_settings": BASE_DIR / ALARM_SETTINGS,
    "category_configs": BASE_DIR / CATEGORY_CONFIGS,
    "custom_settings": BASE_DIR / CUSTOM_SETTINGS,
}


def load_lz_config(logger: logging.Logger) -> LandingZoneManager:
    """Validate configuration paths and load landing zone configuration."""
    if not validate_config_paths(CONFIG_PATHS, logger):
        raise FileNotFoundError("One or more configuration files not found.")
    return LandingZoneManager(CONFIG_PATHS["lz"])


def process_landing_zone(
    lz_name: str,
    logger: logging.Logger,
    action: str,
    dry_run: bool = False,
    change_request: Optional[str] = None,
) -> None:
    """
    Create an AWS session, load landing zone config, scan resources,
    and deploy (or scan or delete) alarms based on the provided action.
    """
    logger.info(f"Starting process for landing zone: {lz_name}")
    try:
        # Load landing zone configuration
        landing_zone_manager = load_lz_config(logger)
        lz = landing_zone_manager.get_landing_zone(lz_name)
        if not lz:
            raise ValueError(f"Landing zone '{lz}' not found in configuration.")
        logger.info(f"Loaded landing zone: {lz}")

        # Create AWS session using SessionManager
        session = SessionManager.get_session(
            account_id=lz.id,
            account_name=lz.name,
            role=CMS_SPOKE_ROLE,
            region=DEFAULT_REGION,
            role_session_name=DEFAULT_SESSION,
        )
        if not session:
            logger.error(f"Failed to create session for landing zone: {lz_name}")
            return

        # Scan resources for the landing zone
        scanner = ResourceScanner(session)
        logger.info(f"Scanning resources for landing zone '{lz.name}'...")
        resources = scanner.scan_all_supported_resources(lz.name)
        logger.info(f"Discovered {len(resources)} resources.")

        # Initialize AlarmManager
        alarm_manager = AlarmManager(
            landing_zone=lz,
            session=session,
            alarm_config_path=CONFIG_PATHS["alarm_settings"],
            category_config_path=CONFIG_PATHS["category_configs"],
            custom_config_path=CONFIG_PATHS["custom_settings"],
            monitored_resources=resources,
        )

        if action == "create":
            if dry_run:
                logger.info("Dry run mode enabled. No alarms will be deployed.")
            else:
                for resource in resources:
                    logger.debug(f"Deploying alarms for resource: {resource}")
                    alarm_manager.deploy_alarms(resource)
                logger.info(f"Completed alarm deployment for landing zone '{lz.name}'.")
        elif action == "scan":
            # Scan for alarms and log the result.
            alarms = alarm_manager.scan_alarms()
            count = len(alarms)
            logger.info(f"Scanned alarms: {count}")
            if count > 0:
                for alarm in sorted(alarms):
                    logger.info(f"  {alarm}")
            else:
                logger.info("No alarms found.")
        elif action == "delete":
            try:
                # delete all CMS-managed alarms.
                alarm_manager.delete_alarms()
                logger.info(f"Deleted alarms for landing zone '{lz.name}'.")
            except Exception as e:
                logger.error(f"Error deleting alarms for landing zone '{lz.name}': {e}")
        else:
            logger.error(f"Unknown action: {action}")
    except Exception as e:
        logger.exception(f"Error processing landing zone {lz_name}: {e}")
        raise


def main() -> None:
    # Parse CLI arguments using CliParser
    args: CliArgs = CliParser.parse_arguments()

    # Initialize logger (configured once)
    logger = LoggerSetup(LOG_FORMAT).get_logger("main")
    logger.info("Starting main execution")

    # Validate production landing zone requirements (e.g., change request)
    CliParser.validate_production_lz(args, logger)

    # Process the landing zone using parsed CLI arguments.
    process_landing_zone(
        lz_name=args.lz,
        logger=logger,
        action=args.action,
        dry_run=args.dry_run,
        change_request=args.change_request,
    )


if __name__ == "__main__":
    main()
