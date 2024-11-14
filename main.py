import argparse
import logging
from pathlib import Path

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

# Config Paths
BASE_DIR = Path(__file__).parent
CONFIG_PATHS = {
    "lz": BASE_DIR / LZ_CONFIG,
    "alarm_settings": BASE_DIR / ALARM_SETTINGS,
    "category_configs": BASE_DIR / CATEGORY_CONFIGS,
    "custom_settings": BASE_DIR / CUSTOM_SETTINGS,
}


def setup_logging() -> logging.Logger:
    """Setup logging configuration."""
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    return logging.getLogger(__name__)


def validate_config_paths(logger: logging.Logger) -> None:
    """Validate that all configuration paths exist."""
    for config_name, path in CONFIG_PATHS.items():
        if not path.exists():
            logger.error(f"Configuration file not found: {config_name} at {path}")
            raise FileNotFoundError(
                f"Configuration file not found: {config_name} at {path}"
            )


def setup() -> tuple[logging.Logger, LandingZoneManager]:
    """Setup logging and load configurations."""
    logger = setup_logging()
    try:
        validate_config_paths(logger)
        landing_zone_manager = LandingZoneManager(CONFIG_PATHS["lz"])
        return logger, landing_zone_manager
    except Exception as e:
        logger.error(f"Error during setup: {e}")
        raise


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

        # Execute the corresponding method for the action
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


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="CMS Monitoring Alarm Management")
    parser.add_argument(
        "--lz",
        "-l",
        type=str,
        default="all",
        help="Specific landing zone to process (e.g., lz250prod, cmsprod) or 'all'",
    )
    parser.add_argument(
        "--action",
        "-a",
        type=str,
        choices=["create", "scan", "delete"],
        required=True,
        help="Action to perform: 'create', 'scan', or 'delete'",
    )
    parser.add_argument(
        "--change-request",
        "-cr",
        type=str,
        help="Change request number for logging (required for production landing zones)",
    )
    return parser.parse_args()


def is_production_lz(lz_name: str) -> bool:
    """Check if the landing zone is a production environment."""
    lz_name_lower = lz_name.lower()
    return (
        "prod" in lz_name_lower
        and "nonprod" not in lz_name_lower
        and "preprod" not in lz_name_lower
    )


def validate_production_lz(args, logger):
    """Validate if a change request number is required for production landing zones."""
    if is_production_lz(args.lz) and args.action == "create":
        if not args.change_request:
            error_message = (
                "Change request number is required for production landing zones."
            )
            logger.error(error_message)
            raise ValueError(error_message)


def main() -> None:
    """
    Main execution function for CMS Monitoring.
    Handles the setup and deployment of alarms across all landing zones.
    """
    args = parse_arguments()
    logger = logging.getLogger(__name__)
    try:
        logger, landing_zone_manager = setup()
        logger.info(
            f"Starting CMS Monitoring for landing zone: {args.lz} with action: {args.action}"
        )

        validate_production_lz(args, logger)

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
