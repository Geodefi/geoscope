# -*- coding: utf-8 -*-

from os import path
import json

from src.common import AttributeDict
from src.exceptions.globals.config import ConfigurationFileError, MissingConfigurationError


def apply_flags(
    config: AttributeDict,
    flags: AttributeDict,
    env: AttributeDict,
):
    """Applies the flags to the configuration.
    If a particular flag is not set, the configuration is not changed.

    Args:
        config (AttributeDict): the configuration as an AttributeDict.

    Returns:
        AttributeDict: the configuration with the flags applied.
    """
    # TODO: these should be implemented according to the config.json
    pass


def init_config(main_dir: str) -> AttributeDict:
    """Initializes the configuration from the config.json file from main directory.

    Returns:
        AttributeDict: the configuration as an AttributeDict.

    Raises:
        TypeError: if the config file is not a dict after loading from json.
    """

    try:
        config_path = path.join(main_dir, "config.json")

        # Catch configuration variables
        config_dict: dict = json.load(open(config_path, encoding="utf-8"))

        config: AttributeDict = AttributeDict.convert_recursive(config_dict)

    except Exception as e:
        raise ConfigurationFileError(
            "Error while loading the configuration file 'config.json'"
        ) from e

    return config
