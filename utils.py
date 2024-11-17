from logging import Logger
from pathlib import Path
from typing import Dict, Union

import yaml


def load_yaml(file_path: Union[str, Path]) -> Dict:
    with open(file_path, "r") as file:
        data = yaml.safe_load(file)
    return data


def validate_config_paths(config_paths: Dict[str, Path], logger: Logger) -> bool:
    """Validate that all configuration paths exist."""
    for config_name, path in config_paths.items():
        if not path.exists():
            logger.error(f"Configuration file not found: {config_name} at {path}")
            raise FileNotFoundError(
                f"Configuration file not found: {config_name} at {path}"
            )
    return True
