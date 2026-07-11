from typing import Any, Dict

import yaml


def load_yaml_config(filepath: str) -> Dict[str, Any]:
    """
    Load raw configuration data from a YAML file

    :param filepath: Path to YAML config file
    :return: Raw config data, a mapping with a ``statements`` list
    """
    with open(filepath, 'r') as f:
        return yaml.safe_load(f)
