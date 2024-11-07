import logging
from pathlib import Path

from aws_manager import *
from utils.constants import *

# Config Paths
BASE_DIR = Path(__file__).parent
CONFIG_PATHS = {
    "lz": BASE_DIR / LZ_CONFIG,
    "metrics": BASE_DIR / METRICS_CONFIG,
    "thresholds": BASE_DIR / THRESHOLDS_CONFIG,
    "customs": BASE_DIR / CUSTOM_CONFIG,
}

def setup() -> tuple[logging.Logger, MonitoringConfig, LandingZoneManager]:
    """Setup logging and load configurations"""
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    logger = logging.getLogger(__name__)

    try:
        monitoring_config = MonitoringConfig.load(CONFIG_PATHS["metrics"], CONFIG_PATHS["thresholds"], CONFIG_PATHS["customs"])
        landing_zone_manager = LandingZoneManager(CONFIG_PATHS["lz"])
        return logger, monitoring_config, landing_zone_manager
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        raise

def process_landing_zone(lz: LandingZone, session: AWSSession, monitoring_config: MonitoringConfig) -> None:
    """Process a single landing zone"""
    resource_scanner = ResourceScanner(session, DEFAULT_REGION)
    resources = resource_scanner.get_managed_resources(lz.env)
    
    AlarmManager(lz, session, monitoring_config).deploy_alarms(resources)

def main():
    logger, monitoring_config, landing_zone_manager = setup()
    logger.info("Starting CMS Monitoring")

    try:
        for lz in landing_zone_manager.get_all_landing_zones():
            session = SessionManager.get_or_create_session(
                lz=lz,
                role=CMS_SPOKE_ROLE,
                region=DEFAULT_REGION,
                role_session_name=DEFAULT_SESSION
            )
            if session:
                try:
                    process_landing_zone(lz, session, monitoring_config)
                except Exception as e:
                    logger.error(f"Error processing {lz.name}: {e}")

    except Exception as e:
        logger.error(f"Critical error: {e}")
        raise
    finally:
        logger.info("CMS Monitoring Completed")


if __name__ == "__main__":
    main()
