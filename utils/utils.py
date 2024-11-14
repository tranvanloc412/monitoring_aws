import yaml
from typing import Dict, Union
from pathlib import Path


def load_yaml(file_path: Union[str, Path]) -> Dict:
    with open(file_path, "r") as file:
        data = yaml.safe_load(file)
    return data
