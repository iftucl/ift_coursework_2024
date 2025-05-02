"""
Loads the sustainability indicator configuration from a YAML file.
"""

from pathlib import Path

import yaml


def load_indicator_config(path: Path) -> list:
    """
    Loads the indicator configuration from a YAML file.

    Args:
        path (Path): Path to the YAML configuration file.

    Returns:
        list: Parsed list of indicator group configurations.
    """
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
