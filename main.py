import logging
from pathlib import Path
from dataclasses import dataclass

from aws_manager import *
from utils.constants import *

# Config Paths
BASE_DIR = Path(__file__).parent
CONFIG_PATHS = {
    "lz": BASE_DIR / LZ_CONFIG,
    "metrics": BASE_DIR / METRICS_CONFIG,
    "thresholds": BASE_DIR / THRESHOLDS_CONFIG,
}


@dataclass
class Config:
    """Holds all configuration instances"""

    landing_zones: LandingZoneManager
    metrics: MetricConfig
    thresholds: ThresholdConfig


def setup() -> tuple[logging.Logger, Config]:
    """Setup logging and load configurations"""
    # Setup logging
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    logger = logging.getLogger(__name__)

    # Load configurations
    try:
        config = Config(
            landing_zones=LandingZoneManager(CONFIG_PATHS["lz"]),
            metrics=MetricConfig(CONFIG_PATHS["metrics"]),
            thresholds=ThresholdConfig(CONFIG_PATHS["thresholds"]),
        )
        return logger, config
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        raise


def process_landing_zone(lz: "LandingZone", config: Config, session) -> None:
    """Process a single landing zone"""
    resource_scanner = ResourceScanner(session, region_name=DEFAULT_REGION)
    resources = resource_scanner.get_managed_resources()

    alarm_manager = AlarmManager(
        lz=lz,
        resources=resources,
        metric_config=config.metrics,
        threshold_config=config.thresholds,
        session=session,
    )

    alarm_manager.deploy_alarms(max_workers=3)


def main():
    """Main application entry point"""
    logger, config = setup()
    logger.info("Starting CMS Monitoring")

    try:
        for lz in config.landing_zones.get_all_landing_zones():
            session = SessionManager.get_or_create_session(
                lz=lz,
                role=CMS_SPOKE_ROLE,
                region=DEFAULT_REGION,
                role_session_name=DEFAULT_SESSION,
            )
            if session:
                try:
                    process_landing_zone(lz, config, session)
                except Exception as e:
                    logger.error(f"Error processing {lz.name}: {e}")
                finally:
                    SessionManager.cleanup_session(session)

    except Exception as e:
        logger.error(f"Critical error: {e}")
        raise
    finally:
        logger.info("CMS Monitoring Completed")


if __name__ == "__main__":
    main()
