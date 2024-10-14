# -*- coding: utf-8 -*-

import os
from os import getenv
import json

from src.common import AttributeDict
from src.exceptions.globals.config import ConfigurationFileError, MissingConfigurationError


def apply_flags(
    config: AttributeDict,
    flags: AttributeDict,
) -> AttributeDict:
    """Applies the flags to the configuration.
    If a particular flag is not set, the configuration is not changed.

    Args:
        config (AttributeDict): the configuration as an AttributeDict.

    Returns:
        AttributeDict: the configuration with the flags applied.
    """
    # TODO: (later) these should be implemented according to the config.json
    # DONE! but need to check when fixing the commands neverthless. So stays a to-do.

    config.dir = flags.main_dir
    config.chain_name = flags.chain
    if "chain_start" in flags:
        config.chains[config.chain_name].start = flags.chain_start
    if "chain_identifier" in flags:
        config.chains[config.chain_name].identifier = flags.chain_identifier
    if "chain_period" in flags:
        config.chains[config.chain_name].period = int(flags.chain_period)
    if "chain_interval" in flags:
        config.chains[config.chain_name].interval = int(flags.chain_interval)
    if "chain_range" in flags:
        config.chains[config.chain_name].range = int(flags.chain_range)
    if "execution_api" in flags:
        config.chains[config.chain_name].execution_api = int(flags.execution_api)
    if "consensus_api" in flags:
        config.chains[config.chain_name].consensus_api = int(flags.consensus_api)

    if "network_refresh_rate" in flags:
        config.network.refresh_rate = flags.network_refresh_rate
    if "network_max_attempt" in flags:
        config.network.max_attempt = flags.network_max_attempt
    if "network_attempt_rate" in flags:
        config.network.attempt_rate = flags.network_attempt_rate

    if "no_log_stream" in flags:
        config.logger.no_stream = flags.no_log_stream
    if "no_log_file" in flags:
        config.logger.no_file = flags.no_log_file
    if "logger_dir" in flags:
        config.logger.dir = flags.logger_dir
    if "logger_level" in flags:
        config.logger.level = flags.logger_level
    if "logger_when" in flags:
        config.logger.when = flags.logger_when
    if "logger_interval" in flags:
        config.logger.interval = flags.logger_interval
    if "logger_backup" in flags:
        config.logger.backup = flags.logger_backup

    if "database_dir" in flags:
        config.database.dir = flags.database_dir
    # Apply environment variables if desired

    if "<API_KEY_EXECUTION>" in config.chains[flags.chain].execution_api:
        # put the execution api key in configuration from environment variables
        if getenv("API_KEY_EXECUTION"):
            config.chains[config.chain_name].execution_api = config.chains[
                config.chain_name
            ].execution_api.replace("<API_KEY_EXECUTION>", getenv("API_KEY_EXECUTION"))
        else:
            raise MissingConfigurationError("API_KEY_EXECUTION environment var should be provided.")

    if "<API_KEY_CONSENSUS>" in config.chains[config.chain_name].consensus_api:
        # put the consensus api key in configuration from environment variables
        if getenv("API_KEY_CONSENSUS"):
            config.chains[config.chain_name].consensus_api = config.chains[
                config.chain_name
            ].consensus_api.replace("<API_KEY_CONSENSUS>", getenv("API_KEY_CONSENSUS"))
        else:
            raise MissingConfigurationError("API_KEY_CONSENSUS environment var should be provided.")

    # put the gas api key in configuration from environment variables
    if "gas" in config:
        if "<API_KEY_GAS>" in config.gas.api:
            if getenv("API_KEY_GAS"):
                config.gas.api = config.gas.api.replace("<API_KEY_GAS>", getenv("API_KEY_GAS"))
            else:
                raise MissingConfigurationError("API_KEY_GAS environment var should be provided.")

    return config


def init_config(main_dir: str) -> AttributeDict:
    """Initializes the configuration from the config.json file from main directory.

    Returns:
        AttributeDict: the configuration as an AttributeDict.

    Raises:
        TypeError: if the config file is not a dict after loading from json.
    """
    main_dir_path = os.path.join(os.getcwd(), main_dir)

    if not os.path.exists(main_dir_path):
        raise ConfigurationFileError(
            f"Could not locate the provided path for the main directory: {main_dir_path}"
        )

    config_path = os.path.join(main_dir_path, "config.json")

    if os.path.exists(config_path):
        # Catch configuration variables
        try:
            with open(config_path, encoding="utf-8") as user_file:
                config_dict = json.load(user_file)
        except Exception as e:
            raise ConfigurationFileError(
                "Error while loading the configuration file 'config.json'"
            ) from e

    else:
        raise ConfigurationFileError(f"Could not find a config.json file in {main_dir_path}")

    config: AttributeDict = AttributeDict.convert_recursive(config_dict)

    return config
