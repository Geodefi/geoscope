# -*- coding: utf-8 -*-
import os
from web3.contract.contract import ContractEvent

from src.common import AttributeDict, Loggable
from src.globals import (
    set_config,
    set_sdk,
    set_constants,
    set_logger,
    get_config,
    get_sdk,
    get_logger,
)
from src.exceptions import ConfigurationFieldError, MissingConfigurationError, GasApiError

from src.globals.config import apply_flags, init_config
from src.globals.constants import init_constants
from src.globals.sdk import init_sdk

from src.utils.gas import parse_gas, fetch_gas
from src.utils.notify import send_email
from src.database.deposits import create_deposits_table, reinitialize_deposits_table
from src.database.pools import create_pools_table, reinitialize_pools_table
from src.database.slots import create_slots_table, reinitialize_slots_table
from src.database.validators import create_validators_table, reinitialize_validators_table
from src.database.withdrawals import create_withdrawals_table, reinitialize_withdrawals_table


def preflight_checks(test_email: bool = False):
    """Checks if everything is ready for geoscope to work.
    - Checks if config missing any values. 'gas' and 'email' sections are optional,
        however they should be valid if provided.
    - Checks if ethdo is available and account exists
    - Checks if gas api working, when provided
    - Checks if given private key can control the provided Operator ID
    - Checks if there is enough money in the operator wallet and prints

    Raises:
        MissingConfigurationError: One of the required fields on configuration file is missing.
    """
    config = get_config()

    # Sections
    if not "chains" in config:
        raise MissingConfigurationError("'chains' section on config.json is missing or empty.")
    if not "network" in config:
        raise MissingConfigurationError("'network' section on config.json is missing or empty.")
    if not "strategy" in config:
        raise MissingConfigurationError("'strategy' section on config.json is missing or empty.")
    if not "logger" in config:
        raise MissingConfigurationError("'logger' section on config.json is missing or empty.")
    if not "database" in config:
        raise MissingConfigurationError("'database' section on config.json is missing or empty.")
    if not "watchers" in config:
        raise MissingConfigurationError("'ethdo' section on config.json is missing or empty.")

    # Fields
    # TODO: (later) chain related checks should be implemented...
    # chain: AttributeDict = config.chains[config.chain_name] #
    network: AttributeDict = config.network
    if not "refresh_rate" in network:
        raise MissingConfigurationError("'network' section is missing the 'refresh_rate' field.")
    elif network.refresh_rate <= 0 or network.refresh_rate > 360:
        raise ConfigurationFieldError("Provided value is unexpected: (0-360] seconds")

    if not "max_attempt" in network:
        raise MissingConfigurationError("'network' section is missing the 'max_attempt' field.")
    elif network.max_attempt <= 0 or network.max_attempt > 100:
        raise ConfigurationFieldError("Provided value is unexpected: (0-100] attempts")

    if not "attempt_rate" in network:
        raise MissingConfigurationError("'network' section is missing the 'attempt_rate' field.")
    elif network.max_attempt <= 0 or network.attempt_rate > 10:
        raise ConfigurationFieldError("Provided value is unexpected: (0-10] seconds")
    logger: AttributeDict = config.logger
    if not "no_stream" in logger:
        raise MissingConfigurationError("'logger' section is missing the 'no_stream' field.")

    if not "no_file" in logger:
        raise MissingConfigurationError("'logger' section is missing the 'no_file' field.")

    if not "no_file" in logger:
        if not "level" in logger:  # can add more checks
            raise MissingConfigurationError("'logger' section is missing the 'level' field.")

        if not "when" in logger:  # can add more checks
            raise MissingConfigurationError("'logger' section is missing the 'when' field.")

        if not "interval" in logger:  # can add more checks
            raise MissingConfigurationError("'logger' section is missing the 'interval' field.")

        if not "backup" in logger:  # can add more checks
            raise MissingConfigurationError("'logger' section is missing the 'backup' field.")

    database: AttributeDict = config.database
    if not "dir" in database:
        raise MissingConfigurationError("'database' section is missing the 'dir' field.")

    if "gas" in config:
        gas: AttributeDict = config.gas
        if not "max_priority" in gas:
            raise MissingConfigurationError("'gas' section is missing the 'max_priority' field.")
        if not "max_fee" in gas:
            raise MissingConfigurationError("'gas' section is missing the 'max_fee' field.")
        if not "api" in gas:
            raise MissingConfigurationError("'gas' section is missing the 'api' field.")
        if not "parser" in gas:
            raise MissingConfigurationError(
                "No parser could be identified for the provided gas api"
            )

        priority_fee, base_fee = parse_gas(fetch_gas())
        if priority_fee is None or base_fee is None or priority_fee <= 0 or base_fee <= 0:
            raise GasApiError("Gas api did not respond or faulty")

    if test_email:
        if "email" in config:
            email: AttributeDict = config.email

            if not "smtp_server" in email:
                raise MissingConfigurationError(
                    "'email' section is missing the required 'smtp_server' field."
                )
            if not "smtp_port" in email:
                raise MissingConfigurationError(
                    "'email' section is missing the required 'smtp_port' field."
                )
            if not "dont_notify_devs" in email:
                email.dont_notify_devs = False

                get_logger().info(f"Notification service is configured! Sending a test email...")
                send_email(
                    "Email notification service is active",
                    "Looks like geoscope is functional and it is sailing smoothly at the moment."
                    "We will send you emails when something important happens or there is an error."
                    "Don't forget to check your script regularly tho. This service can fail too!",
                    dont_notify_devs=True,
                )
    # TODO: ping watchers


def setup(**kwargs):
    """Initializes the required components from the geoscope script:
    - Applies the provided flags to be utilized in the config step
    - Creates a config dict from provided json
    - Configures the geodefi python sdk
    - Configures the constant parameters for ease of use
    """
    flags: AttributeDict = AttributeDict({k: v for k, v in kwargs.items() if v is not None})

    config = apply_flags(init_config(flags.main_dir), flags)
    set_config(config)

    set_constants(init_constants())

    logger: Loggable = Loggable()
    set_logger(logger)

    set_sdk(
        init_sdk(
            exec_api=config.chains[config.chain_name].execution_api,
            cons_api=config.chains[config.chain_name].consensus_api,
            priv_key=os.getenv("GEOSCOPE_PRIVATE_KEY"),
        )
    )

    preflight_checks(test_email=kwargs["test_email"])


def init_dbs(reset: bool = False):
    """Initializes the databases as suited.\
    This function is called at the beginning of the program to make sure the
    databases are up to date.

    Args:
        reset (bool, optional): Wipes out all data if provided. Defaults to False.
    """
    if reset:
        get_logger().warning("Dropping the database...")
        reinitialize_deposits_table()
        reinitialize_pools_table()
        reinitialize_slots_table()
        reinitialize_validators_table()
        reinitialize_withdrawals_table()
    else:
        create_deposits_table()
        create_pools_table()
        create_slots_table()
        create_validators_table()
        create_withdrawals_table()


def run_daemons():
    """Initializes and runs the daemons for the triggers.

    This function is called at the beginning of the program to make sure the
    daemons are running.
    """
    # events: ContractEvent = get_sdk().portal.contract.events

    # TODO
    # Triggers
    # Create appropriate type of Daemons for the triggers
    # Run the daemons
