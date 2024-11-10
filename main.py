import logging
from pathlib import Path

from aws_manager import *
from utils.constants import *

# Config Paths
BASE_DIR = Path(__file__).parent
CONFIG_PATHS = {
    "lz": BASE_DIR / LZ_CONFIG,
    "alarm_settings": BASE_DIR / ALARM_SETTINGS,
    "category_configs": BASE_DIR / CATEGORY_CONFIGS,
    "custom_settings": BASE_DIR / CUSTOM_SETTINGS,
}


def setup() -> tuple[logging.Logger, LandingZoneManager]:
    """Setup logging and load configurations"""
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    logger = logging.getLogger(__name__)

    try:
        landing_zone_manager = LandingZoneManager(CONFIG_PATHS["lz"])
        return logger, landing_zone_manager
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        raise


def test():
    logger, landing_zone_manager = setup()
    logger.info("Starting CMS Monitoring")

    lz = landing_zone_manager.get_landing_zone("cmsnonprod")
    session = SessionManager.get_or_create_session(
        lz=lz,
        role=CMS_SPOKE_ROLE,
        region=DEFAULT_REGION,
        role_session_name=DEFAULT_SESSION,
    )
    # print(f"lz: {lz}")
    resource_scanner = ResourceScanner(session, DEFAULT_REGION)
    resources = resource_scanner.get_managed_resources(lz.env)
    # print(f"resources: {resources}")

    # test_resource = Resource(type="EC2", name="CMSLIDA9001", id="i-0edbded74c49e63a1")

    # alarm = AlarmConfigs(
    #     metric=Metric(name="CPUUtilization", namespace="AWS/EC2", dimensions=[]),
    #     statistic="Average",
    #     comparison_operator="GreaterThanThreshold",
    #     unit="Percent",
    #     period=300,
    #     evaluation_periods=2,
    #     description="",
    #     threshold_value=0,
    #     name="",
    #     sns_topic_arns=[],
    # )
    # print(f"alarm: {alarm}")
    alarm_manager = AlarmManager(
        landing_zone=lz,
        aws_session=session,
        monitored_resources=resources,
        alarm_config_path=CONFIG_PATHS["alarm_settings"],
        category_config_path=CONFIG_PATHS["category_configs"],
        custom_config_path=CONFIG_PATHS["custom_settings"],
    )
    # print(f"alarm_manager: {alarm_manager} \n")
    # print(f"new alarms: {alarm_manager.create_alarm_definitions(test_resource)} \n")

    # print(f"new alarms: {alarm_manager.create_all_alarm_definitions()} \n")

    print(alarm_manager.create_all_alarm_definitions())
    # alarm_manager.deploy_alarms(alarm_manager.create_all_alarm_definitions())

    # print(f"existing alarms: {alarm_manager.scan_existing_alarms(resources)} \n")


# def process_landing_zone(
#     lz: LandingZone, session: AWSSession, monitoring_config: MonitoringConfig
# ) -> None:
#     """Process a single landing zone"""
#     resource_scanner = ResourceScanner(session, DEFAULT_REGION)
#     resources = resource_scanner.get_managed_resources(lz.env)

#     AlarmManager(lz, session, monitoring_config).deploy_alarms(resources)


# def main():
#     logger, landing_zone_manager = setup()
#     logger.info("Starting CMS Monitoring")

#     for lz in landing_zone_manager.get_all_landing_zones():
#         session = SessionManager.get_or_create_session(
#             lz=lz,
#             role=CMS_SPOKE_ROLE,
#             region=DEFAULT_REGION,
#             role_session_name=DEFAULT_SESSION,
#         )
#         print(f"Processing {lz.name}")
#         resources = ResourceScanner(session, DEFAULT_REGION).get_managed_resources(
#             lz.env
#         )
#         print(f"Resources: {resources}")

#     # except Exception as e:
#     #     logger.error(f"Critical error: {e}")
#     #     raise
#     # finally:
#     #     logger.info("CMS Monitoring Completed")

#     alarm_configs = AlarmManager(
#         lz=None,
#         alarm_config_path=CONFIG_PATHS["alarms_configs"],
#         threshold_config_path=CONFIG_PATHS["alarms_thresholds"],
#         customs_config_path=CONFIG_PATHS["alarms_customs"],
#     )
# print(f"alarm_configs: {alarm_configs._alarm_configs}")
# print("\n")
# print(f"threshold_configs: {alarm_configs._threshold_configs}")
# print("\n")
# print(f"customs_configs: {alarm_configs._customs_configs}")


if __name__ == "__main__":
    # main()
    test()
