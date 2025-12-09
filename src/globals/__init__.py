# pylint: disable=global-statement

import logging
from typing import Any

from geodefi import Geode

from src.common.loggable import Loggable
from src.globals.constants.config import DEFAULT_LOGGER_FORMAT_DATE, DEFAULT_LOGGER_FORMAT_MESSAGE
from src.utils.dict import get_nested_value

# global CONFIG referance, requires initialization
__CONFIG: dict

# global Logger referance, requires initialization, returns a default logger otherwise.
__LOGGER: Loggable

# global SDK referance, requires initialization
__SDK: Geode


# GETTERS
def get_config(field: tuple | None = None) -> Any:
    """
    Retrieve the global config, or a nested value within it.

    Args:
        field (tuple, optional): Tuple path to a nested value in the configuration.
            For example to reach the value "c" in config:
                {
                'a':{
                    'b':{
                        'c':5
                        }
                    }
                }
            path of ('a','b','c') tuple should be provided.

            Otherwise, given None, the whole config dictionary is returned.

    Returns:
        Any: The entire configuration, or the value at the specified nested field path.

    Raises:
        KeyError: If the specified path does not exist in the configuration.
    """
    if field:
        return get_nested_value(dct=__CONFIG, keys=field, abort=True)
    else:
        return __CONFIG


def get_logger() -> logging.Logger:
    """
    Retrieve the global Logger instance.

    Provides a default logger if the global Logger have not been initialized yet.

    Returns:
        logging.Logger: The global Logger instance for logging messages.
    """
    try:
        return __LOGGER.logger

    except (NameError, AttributeError):
        ch = logging.StreamHandler()
        ch.setFormatter(
            logging.Formatter(
                fmt=DEFAULT_LOGGER_FORMAT_MESSAGE,
                datefmt=DEFAULT_LOGGER_FORMAT_DATE,
            )
        )
        logging.basicConfig(handlers=[ch], force=True, level=logging.INFO)
        def_log = logging.getLogger()
        return def_log


def get_sdk() -> Geode:
    """
    Retrieve the global Geodefi SDK instance.

    Returns:
        Geode: The initialized Geodefi SDK instance.
    """
    return __SDK


# Setters
def set_config(value: dict) -> None:
    """
    Initialize or update the global configuration variables.

    Args:
        value (dict): Dictionary to set as the global configuration.

    Raises:
        TypeError: If the provided value is not a dictionary.
    """
    global __CONFIG
    if not isinstance(value, dict):
        raise TypeError("Config value must be a dictionary.")
    __CONFIG = value


def set_logger(value: Loggable) -> None:
    """
    Set the global Logger instance.

    Args:
        value (Loggable): An instance of Loggable to be used globally.

    Raises:
        TypeError: If the provided value is not an instance of Loggable.
    """
    global __LOGGER
    if not isinstance(value, Loggable):
        raise TypeError("Logger value must be an instance of Loggable.")
    __LOGGER = value


def set_sdk(value: Geode) -> None:
    """
    Set the global Geodefi SDK instance.

    Args:
        value (Geode): An instance of Geodefi SDK to be used globally.

    Raises:
        TypeError: If the provided value is not an instance of Geode.
    """
    global __SDK
    if not isinstance(value, Geode):
        raise TypeError("SDK value must be an instance of Geode.")
    __SDK = value
