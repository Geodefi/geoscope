"""
Transaction Submission via Watchers for Geoscope.

This module contains functions to interact with the Watcher api services,
including submitting transactions and retrieving version information
from watcher services. It handles transaction preparation, submission, and
response handling.
"""

from typing import Any

import requests  # type: ignore
from eth_typing import ChecksumAddress
from eth_typing.abi import TypeStr
from requests.exceptions import RequestException

from src.exceptions import WatcherApiError
from src.globals import get_config, get_logger, get_sdk
from src.globals.constants.config import WATCHERS_FIELD
from src.globals.constants.watcher import (
    CHAIN_ID_ENDPOINT,
    CONTRACT_ADDRESS_ENDPOINT,
    SIGNERS_ENDPOINT,
    SUBMIT_ENDPOINT,
    VERSION_ENDPOINT,
)
from src.helpers.gnosis import get_nonce, prepare_tx


def post_submit_batch(
    method_id: str,
    param_types: list[TypeStr],
    param_args: list[Any],
) -> None:
    """
    Submits a transaction to all configured watcher URLs.

    Prepares a transaction using the provided method ID and parameters,
    retrieves the current nonce, and sends the transaction data to each watcher URL
    specified in the configuration.

    Args:
        method_id (str): The identifier of the method to be invoked.
        param_types (list[TypeStr]): A list of parameter types corresponding to the method.
        param_args (list[Any]): A list of arguments for the method parameters.

    Raises:
        WatcherApiError: If a network-related error occurs during the POST request.
        ValueError: If the nonce retrieval or transaction preparation fails.
    """
    watchers: list[str] = get_config(field=WATCHERS_FIELD)
    if not watchers:
        get_logger().warning("No watchers configured. Transaction not submitted!")
        return

    try:
        target = get_sdk().portal.address
        safe_nonce = get_nonce()
        tx = prepare_tx(safe_nonce, target, method_id, param_types, param_args)
    except Exception as e:
        get_logger().error(f"Failed to prepare transaction: {e}")
        raise WatcherApiError("Transaction preparation failed.") from e

    data = {"nonce": safe_nonce, "transaction": tx, "merkles": []}
    for url in watchers:
        try:
            res = requests.post(url=f"{url}{SUBMIT_ENDPOINT}", json=data, timeout=10)
            res.raise_for_status()
            get_logger().debug(f"Watcher on {url} responded with: {res.text}")
        except RequestException as e:
            get_logger().error(f"Failed to submit transaction to {url}: {e}")
            raise WatcherApiError(f"Failed to submit transaction watcher {url}: {e}") from e


def get_version(url: str) -> str:
    """
    Retrieve the version information from a specified watcher URL.

    Sends a GET request to the `/v1/version` endpoint of the provided URL
    and returns the version information.

    Args:
        url (str): The base URL of the watcher to retrieve the version from.

    Returns:
        str: The version string retrieved from the watcher.

    Raises:
        WatcherApiError: If a network-related error occurs during the GET request.
        KeyError: If the key is missing in the response data.
        ValueError: If the response data is not in the expected format.
    """
    try:
        res = requests.get(url=f"{url}{VERSION_ENDPOINT}", timeout=10)
        res.raise_for_status()
        info = res.json()
        return info["version"]
    except RequestException as e:
        get_logger().error(f"Failed to retrieve version from watcher {url}: {e}")
        raise WatcherApiError(f"Failed to retrieve version from watcher {url}: {e}") from e
    except (KeyError, ValueError) as e:
        get_logger().error(f"Invalid response format from {url}: {e}")
        raise WatcherApiError(f"Failed to parse version information from {url}: {e}") from e


def get_signers(url: str) -> list[ChecksumAddress]:
    """
    Retrieve the list of signers from a specified watcher URL.

    Sends a GET request to the `/v1/signer` endpoint of the provided URL
    and returns the addresses for signers.

    Args:
        url (str): The base URL of the watcher to retrieve the version from.

    Returns:
        list[ChecksumAddress]: The list of Checksummed Address of watcher signers.

    Raises:
        WatcherApiError: If a network-related error occurs during the GET request.
        KeyError: If the key is missing in the response data.
        ValueError: If the response data is not in the expected format.
    """
    try:
        res = requests.get(url=f"{url}{SIGNERS_ENDPOINT}", timeout=10)
        res.raise_for_status()
        info = res.json()
        return list(map(get_sdk().w3.to_checksum_address, info["signers"]))
    except RequestException as e:
        get_logger().error(f"Failed to retrieve signers from watcher {url}: {e}")
        raise WatcherApiError(f"Failed to retrieve signers from watcher {url}: {e}") from e
    except (KeyError, ValueError) as e:
        get_logger().error(f"Invalid response format from {url}: {e}")
        raise WatcherApiError(f"Failed to parse signers information from {url}: {e}") from e


def get_chain_id(url: str) -> int:
    """
    Retrieve the chain id of watcher with specified URL.

    Sends a GET request to the `/v1/chain-id` endpoint of the provided URL
    and returns the chain-id for the watcher.

    Args:
        url (str): The base URL of the watcher to retrieve the version from.

    Returns:
        int: The chain-id of watcher.

    Raises:
        WatcherApiError: If a network-related error occurs during the GET request.
        KeyError: If the key is missing in the response data.
        ValueError: If the response data is not in the expected format.
    """
    try:
        res = requests.get(url=f"{url}{CHAIN_ID_ENDPOINT}", timeout=10)
        res.raise_for_status()
        info = res.json()
        return int(info["chainId"])
    except RequestException as e:
        get_logger().error(f"Failed to retrieve chain-id from watcher {url}: {e}")
        raise WatcherApiError(f"Failed to retrieve chain-id from watcher {url}: {e}") from e
    except (KeyError, ValueError) as e:
        get_logger().error(f"Invalid response format from {url}: {e}")
        raise WatcherApiError(f"Failed to parse chain-id information from {url}: {e}") from e


def get_contract_address(url: str) -> ChecksumAddress:
    """
    Retrieve the address of the multisig that the watcher is pointing, from a specified watcher URL.

    Sends a GET request to the `/v1/contract-address` endpoint of the provided URL
    and returns the address for the oracle.

    Args:
        url (str): The base URL of the watcher to retrieve the version from.

    Returns:
        ChecksumAddress: The Checksummed Address of watcher.

    Raises:
        WatcherApiError: If a network-related error occurs during the GET request.
        KeyError: If the key is missing in the response data.
        ValueError: If the response data is not in the expected format.
    """
    try:
        res = requests.get(url=f"{url}{CONTRACT_ADDRESS_ENDPOINT}", timeout=10)
        res.raise_for_status()
        info = res.json()
        return get_sdk().w3.to_checksum_address(info["contractAddress"])
    except RequestException as e:
        get_logger().error(f"Failed to retrieve contract address from watcher {url}: {e}")
        raise WatcherApiError(f"Failed to retrieve contract address from watcher {url}: {e}") from e
    except (KeyError, ValueError) as e:
        get_logger().error(f"Invalid response format from {url}: {e}")
        raise WatcherApiError(
            f"Failed to parse contract address information from {url}: {e}"
        ) from e
