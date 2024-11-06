import yaml
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional, Union
from utils.utils import load_yaml

logger = logging.getLogger(__name__)


@dataclass
class LandingZone:
    name: str
    account_id: str
    app_id: str = "CMS"
    category: str = "CAT_D"


class LandingZoneManager:
    _lz_configs: Optional[List[LandingZone]] = None

    def __init__(self, lz_file: Union[str, Path]):
        if LandingZoneManager._lz_configs is None:
            self._load_lz_configs(lz_file)

    @classmethod
    def _load_lz_configs(cls, lz_file: Union[str, Path]) -> None:
        """
        Load all landing zone configurations from a YAML file and store them in _lz_configs.
        """
        if cls._lz_configs is not None:
            logger.debug("Landing zone configurations already loaded.")
            return

        try:
            cls._lz_configs = []
            data = load_yaml(lz_file)

            for lz_data in data:
                landing_zones = [
                    cls._init_landing_zone(lz_data, env)
                    for env, account_id in lz_data.get("environments", {}).items()
                    if account_id  # Only initialize valid account IDs
                ]
                cls._lz_configs.extend(lz for lz in landing_zones if lz is not None)
            logger.info(f"Loaded {len(cls._lz_configs)} landing zones from {lz_file}")
        except FileNotFoundError:
            logger.error(f"Error: File {lz_file} not found.")
            cls._lz_configs = []
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML: {e}")
            cls._lz_configs = []

    @classmethod
    def get_all_landing_zones(cls) -> List[LandingZone]:
        """Returns the current lz_configs dictionary"""

        if cls._lz_configs is None:
            logger.error("Landing zone configurations are not loaded.")
            return []

        return cls._lz_configs

    @classmethod
    def get_landing_zone(cls, lz_name: str) -> Optional[LandingZone]:
        """Retrieves a LandingZone instance by name."""

        if cls._lz_configs is None:
            logger.error("Landing zone configurations not loaded.")
            return None
        return next((lz for lz in cls._lz_configs if lz.name == lz_name), None)

    @staticmethod
    def _init_landing_zone(lz_data: Dict, env: str) -> Optional[LandingZone]:
        try:
            return LandingZone(
                name=f"{lz_data['landing_zone']}{env}",
                account_id=lz_data["environments"]["nonprod"],
                app_id=lz_data["app_id"],
                category=lz_data["category"],
            )
        except KeyError as e:
            logger.warning(f"Missing data for landing zone in {env}: {e}")
            return None
