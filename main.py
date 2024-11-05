import logging
from pathlib import Path
from typing import Dict, List, Optional
from aws_manager import *
from utils.utils import load_yaml
from constants import *
from dataclasses import asdict

### Constants for paths
# Config Paths
BASE_DIR = Path(__file__).parent
LZ_CONFIG_PATH = BASE_DIR.joinpath(LZ_CONFIG)
METRICS_CONFIG_PATH = BASE_DIR.joinpath(METRICS_CONFIG)
THRESHOLDS_CONFIG_PATH = BASE_DIR.joinpath(THRESHOLDS_CONFIG)

# Set up the root logger
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

# Log Starting message
logger.info("--- Starting CMS Monitoring ---")

def load_configurations():
    """Load and validate all configurations at startup"""
    try:
        landing_zones = LandingZoneManager(LZ_CONFIG_PATH)
        metric_config = MetricConfig(METRICS_CONFIG_PATH)
        threshold_config = ThresholdConfig(THRESHOLDS_CONFIG_PATH)
        return landing_zones, metric_config, threshold_config
    except Exception as e:
        logger.error(f"Failed to load configurations: {e}")
        raise


def assume_role_for_landing_zone(lz: LandingZone) -> Optional[AWSSession]:
    """
    Assume the role for a specified landing zone with retries
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            session = assume_role(lz, CMS_SPOKE_ROLE, DEFAULT_REGION, DEFAULT_SESSION)
            if session:
                logger.info(f"Assumed role successfully for {lz.name}")
                return session
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt == max_retries - 1:
                logger.error(f"Failed to assume role for {lz.name} after {max_retries} attempts")
    return None


def main() -> None:
    try:
        # Load configurations
        landing_zones, metric_config, threshold_config = load_configurations()
        
        # Process each landing zone
        for lz in landing_zones.get_all_landing_zones():
            logger.info(f"Processing landing zone: {lz.name}")
            
            # Assume role with retries
            session = assume_role_for_landing_zone(lz)
            if not session:
                continue
                
            # Scan resources
            resource_scanner = ResourceScanner(session, region_name=DEFAULT_REGION)
            try:
                resources = resource_scanner.get_managed_resources()
            except Exception as e:
                logger.error(f"Failed to scan resources for {lz.name}: {e}")
                continue
                
            # Create and deploy alarms
            alarm_manager = AlarmManager(
                lz=lz,
                resources=resources,
                metric_config=metric_config,
                threshold_config=threshold_config,
            )
            
            alarm_definitions = alarm_manager.create_all_alarm_definitions()
            logger.info(f"Created alarm definitions: {alarm_definitions}")``
            
            # Deploy alarms (implement this method)
            # deploy_alarms(session, alarm_definitions)
            
    except Exception as e:
        logger.error(f"Critical error in main execution: {e}")
        raise


if __name__ == "__main__":
    main()
    
    
