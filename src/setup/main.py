"""
Initialization and setup module for the Geoscope.

This module handles preflight checks, application setup, database initialization,
and daemon processes required for the proper functioning of Geoscope.
"""

import os

from eth_typing import ChecksumAddress

from src.actions.watchers import get_chain_id, get_contract_address, get_signers, get_version
from src.common import Loggable
from src.exceptions import (
    ConfigurationFieldError,
    GasApiError,
    MultiSigError,
    WatcherAddressError,
    WatcherError,
    WatcherNetworkError,
    WatcherVersionError,
)
from src.globals import get_config, get_sdk, set_logger, set_sdk
from src.globals.constants.config import (
    CHAIN_CONSENSUS_API_FIELD,
    CHAIN_EXECUTION_API_FIELD,
    CHAIN_NAME_FIELD,
    GAS_API_FIELD,
    LOGGER_BACKUP_KEEP_FIELD,
    LOGGER_BACKUP_WHEN_FIELD,
    LOGGER_DIR_FIELD,
    LOGGER_FORMAT_DATE_FIELD,
    LOGGER_FORMAT_MESSAGE_FIELD,
    LOGGER_LEVEL_FIELD,
    WATCHERS_FIELD,
)
from src.globals.constants.watcher import EXPECTED_VERSION, HTTP_PATTERN
from src.globals.schemas.database import DATABASE_SCHEMA
from src.helpers.portal import fetch_oracle_address
from src.utils.gas import fetch_gas, parse_gas
from src.utils.notify import send_email

from .database import create_db_tables
from .sdk import init_sdk


def __verify_watcher() -> None:
    watchers = get_config(field=WATCHERS_FIELD)
    for url in watchers:
        # Veirfy url string validity
        if not HTTP_PATTERN.match(url):
            raise ConfigurationFieldError(f"Invalid watcher URL: {url}")

        try:
            # Verify Version
            watcher_version: str = get_version(url)
            if watcher_version != EXPECTED_VERSION:
                raise WatcherVersionError(
                    f"Watcher api did not respond with a supported version: {url}"
                )

            # Verify chain-id
            watcher_chain_id: int = get_chain_id(url)
            expected_chain_id: int = get_sdk().w3.eth.chain_id
            if watcher_chain_id != expected_chain_id:
                raise WatcherNetworkError(
                    f"Watcher api did not respond with a expected chain-id: {url}"
                )

            # Verify Oracle Address
            oracle_address = fetch_oracle_address(block_identifier="latest")
            watcher_address = get_contract_address(url)
            if watcher_address != oracle_address:
                raise WatcherAddressError(
                    f"Watcher api did not respond with a expected oracle address: {url}"
                )

            # Verify Signer
            signer_address = get_sdk().w3.eth.default_account
            safe_owners: list[ChecksumAddress] = get_signers(url)
            if signer_address in safe_owners:
                raise MultiSigError("You are not authorized as a multisig member for Watcher")

        except Exception as e:
            raise WatcherError("Watcher api did not respond properly.") from e


def __verify_email() -> None:
    send_email(
        "Email notification service is active",
        "Looks like geoscope is functional and it is sailing smoothly at the moment."
        "We will send you emails when something important happens or there is an error."
        "Don't forget to check your script regularly tho. This service can fail too!",
        dont_notify_devs=True,
    )


def __verify_gas_api() -> None:
    if get_config(field=GAS_API_FIELD):
        priority_fee, base_fee = parse_gas(fetch_gas())
        if priority_fee is None or base_fee is None or priority_fee <= 0 or base_fee <= 0:
            raise GasApiError("Gas api did not respond as expected")


def setup(
    main_dir: str,
    setup_logger: bool = False,
    setup_sdk: bool = False,
    setup_db: bool = False,
    verify: bool = False,
) -> None:
    """
    Initialize and configure the Geoscope application components.
    """

    if setup_logger:
        set_logger(
            Loggable(
                main_dir=main_dir,
                prefix=get_config(field=CHAIN_NAME_FIELD),
                log_dir=get_config(field=LOGGER_DIR_FIELD),
                level=get_config(field=LOGGER_LEVEL_FIELD),
                fmt=get_config(field=LOGGER_FORMAT_MESSAGE_FIELD),
                datefmt=get_config(field=LOGGER_FORMAT_DATE_FIELD),
                backup_when=get_config(field=LOGGER_BACKUP_WHEN_FIELD),
                backup_keep=get_config(field=LOGGER_BACKUP_KEEP_FIELD),
            )
        )

    if setup_sdk:
        set_sdk(
            init_sdk(
                exec_api=get_config(field=CHAIN_EXECUTION_API_FIELD),
                cons_api=get_config(field=CHAIN_CONSENSUS_API_FIELD),
                priv_key=os.getenv("GEOSCOPE_PRIVATE_KEY"),
            )
        )

    if setup_db:
        create_db_tables(*DATABASE_SCHEMA.keys())

    # if verify: TODO:(later) open this part after fresh deployment of all system.
    #     __verify_watcher()
    #     __verify_gas_api()
    #     __verify_email()
