# requirements:
# load all yaml config and store in a dict: lz_configs
# have a function to init 1 lz which is to create a lz from Namedtuple Landing Zone
# find the lz base on the lz_configs and return the lz instance of Landing Zone namedtuple
# have another function it init all landing zones by lazy loading

import yaml
import logging

from collections import namedtuple
from typing import Dict, Optional

logger = logging.getLogger(__name__)

LandingZone = namedtuple("LandingZone", ["name", "account_id", "region", "managed_by"])


class LandingZoneManager:
    _lz_configs: Optional[Dict[str, dict]] = None  # Caching

    @classmethod
    def load_lz_configs(cls, file_path: str) -> None:
        """
        Load all landing zone configurations from a YAML file and store them in _lz_configs.

        :param file_path: Path to the YAML file with landing zone configurations.
        """
        if cls._lz_configs is None:  # Load only if not already loaded
            try:
                with open(file_path, "r") as file:
                    data = yaml.safe_load(file)
                    cls._lz_configs = {
                        lz["landing_zone"]: lz for lz in data if "landing_zone" in lz
                    }
                logger.info(
                    f"Loaded {len(cls._lz_configs)} landing zones from {file_path}"
                )
            except FileNotFoundError:
                logger.error(f"Error: File {file_path} not found.")
                cls._lz_configs = {}
            except yaml.YAMLError as e:
                logger.error(f"Error parsing YAML: {e}")
                cls._lz_configs = {}

    @classmethod
    def get_lz_configs(cls) -> Dict[str, dict]:
        """
        Returns the current lz_configs dictionary, ensuring it's loaded first.

        :return: Dictionary with landing zone configurations.
        """
        if cls._lz_configs is None:
            logger.error(
                "Landing zone configurations are not loaded. Please call `load_lz_configs` first."
            )
            return {}
        return cls._lz_configs

    @classmethod
    def get_landing_zone(cls, name: str, env: str) -> Optional[LandingZone]:
        """
        Retrieves a LandingZone instance by name, initializing it if data is available.

        :param name: The name of the landing zone.
        :param env: Environment type (e.g., 'nonprod', 'prod').
        :return: LandingZone namedtuple if found, None otherwise.
        """
        lz_data = cls._lz_configs.get(name) if cls._lz_configs else None
        if lz_data is None:
            logger.info(f"Landing Zone '{name}' not found.")
            return None
        return cls.init_landing_zone(lz_data, env)

    @staticmethod
    def init_landing_zone(lz_data: dict, env: str) -> Optional[LandingZone]:
        """
        Initialize a LandingZone namedtuple from a dictionary entry.

        :param lz_data: Dictionary containing landing zone data.
        :param env: Environment type (e.g., 'nonprod', 'prod').
        :return: LandingZone namedtuple if data is valid, None otherwise.
        """
        return LandingZone(
            name=lz_data.get("landing_zone", "cms"),
            account_id=lz_data["environments"].get(env, "nonprod"),
            region=lz_data.get("region", "ap-southeast-2"),
            managed_by=lz_data.get("managed_by", "CMS"),
        )
