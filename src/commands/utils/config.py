import json
import os
from os import path
from typing import Any

import click
from dotenv import load_dotenv

from src.exceptions import ConfigVersionError, MissingConfigurationError
from src.exceptions.globals.config import ConfigurationFileError
from src.globals import set_config
from src.globals.constants.config import (
    CHAIN_NAME_FIELD,
    EXPECTED_VERSION,
    MAIN_DIR_FIELD,
    VERSION_KEY,
)
from src.utils.dict import set_nested_value


def __verify_config_version(config_file: dict) -> None:
    """_summary_

    Args:
        config_file (dict): _description_

    Raises:
        MissingConfigurationError: _description_
        ConfigVersionError: _description_
    """
    if VERSION_KEY not in config_file:
        raise MissingConfigurationError("'version' section on config.json is missing or empty.")

    config_version: int = config_file[VERSION_KEY]

    if config_version != EXPECTED_VERSION:
        raise ConfigVersionError(
            f"config.json version is {config_version}, expected {EXPECTED_VERSION} instead."
        )


def __init_config(main_dir: str, chain_name: str) -> dict:
    """
    Initialize the configuration by loading settings from a config.json file in the main directory.

    Searches for a `config.json` file within the specified `main_dir`.
    Then, reads and parses the JSON configuration.

    Args:
        main_dir (str): The main directory path where the `config.json` file is located.

    Returns:
        dict: A dictionary containing all configuration variables.

    Raises:
        ConfigurationFileError: If the main directory does not exist, the config file is missing,
                                or there is an error while loading the config file.
    """
    main_dir_path = os.path.join(os.getcwd(), main_dir)

    if not path.exists(main_dir_path):
        raise ConfigurationFileError(
            f"Could not locate the provided path for the main directory: {main_dir_path}"
        )

    config_path = os.path.join(main_dir_path, "config.json")
    config: dict

    if os.path.exists(config_path):

        config_dict: dict

        try:
            with open(config_path, encoding="utf-8") as config_file:
                config_dict = json.load(config_file)
        except json.JSONDecodeError as e:
            raise ConfigurationFileError(f"Invalid JSON format in {config_path}") from e
        except OSError as e:
            raise ConfigurationFileError(f"Error reading {config_path}") from e

        __verify_config_version(config_dict)

        try:
            config = config_dict[chain_name]
            config = set_nested_value(dct=config, keys=MAIN_DIR_FIELD, value=main_dir)
            config = set_nested_value(dct=config, keys=CHAIN_NAME_FIELD, value=chain_name)

        except KeyError as e:
            raise ConfigurationFileError(
                f"config.json doesn't have a section for given chain: {chain_name}"
            ) from e

    else:
        raise ConfigurationFileError(f"Could not find a config.json file in {main_dir_path}")

    return config


def setup_config(
    ctx: click.Context,
    _option: click.Parameter,
    value: Any,
) -> Any:
    """
    Configures the application based on the provided directory and environment settings.

    This function is used as a callback for a --main-dir option, which is eager.
    Setting up the main  directory for the application, validating its existence,
    creating it if necessary, and loading environment variables from a `.env` file.
    It then initializes the application's configuration and ensures it is accessible globally.

    Args:
        ctx (click.Context): The Click context object, representing the current command-line
                             execution context.
        _option (click.Parameter): The Click parameter object associated with the option
                                   invoking this callback.
        value (Any): The value provided for the `--main-dir` option. Expected to be a string
                     representing the path to the main directory.

    Raises:
        click.BadParameter: If the `--main-dir` value is not provided or is invalid.

    Returns:
        Any: The validated and prepared main directory path, ready for use in the application.
    """
    if ctx.resilient_parsing:
        return value

    if not value:
        raise click.BadParameter("Something unexpected happened: --main-dir is required")

    if not os.path.exists(value):
        click.prompt(
            "Provided Main Directory for geoscope does not exist. Create one?",
            default=True,
            type=click.BOOL,
        )
        os.makedirs(value, exist_ok=True)

    # Load environment variables first, we don't override environment variables from now on.
    load_dotenv(os.path.join(value, ".env"), override=False)

    chain_name = str(os.getenv("GEOSCOPE_CHAIN", ""))
    config = __init_config(main_dir=value, chain_name=chain_name)

    set_config(config)
    return value
