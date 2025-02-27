import yaml
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Union
from utils import load_yaml

logger = logging.getLogger(__name__)


@dataclass
class LandingZone:
    name: str
    env: str
    id: str
    app_id: str
    category: str


class LandingZoneManager:
    _lz_configs: List[LandingZone] = []

    def __init__(self, lz_file: Union[str, Path]):
        if not self._lz_configs:
            self._load_lz_configs(lz_file)

    @classmethod
    def _load_lz_configs(cls, lz_file: Union[str, Path]) -> None:
        try:
            data = load_yaml(lz_file)
            cls._lz_configs = [
                LandingZone(
                    name=f"{lz['landing_zone']}{env}",
                    env=env,
                    id=account_id,
                    app_id=lz.get("app_id", "CMS"),
                    category=lz.get("category", "CAT_D"),
                )
                for lz in data
                for env, account_id in lz.get("environments", {}).items()
                if account_id
            ]
            logger.info(f"Loaded {len(cls._lz_configs)} landing zones")
        except (FileNotFoundError, yaml.YAMLError) as e:
            logger.error(f"Error loading config: {e}")
            cls._lz_configs = []

    @classmethod
    def get_all_landing_zones(cls) -> List[LandingZone]:
        return cls._lz_configs

    @classmethod
    def get_landing_zone(cls, lz_name: str) -> Optional[LandingZone]:
        return next((lz for lz in cls._lz_configs if lz.name == lz_name), None)
