"""
Helper functions for interacting with a Gnosis Safe contract.

This module provides functionalities to retrieve the Gnosis Safe contract instance,
fetch nonces, generate transaction hashes, encode transaction data, and prepare
transactions for execution.
"""

import json
import os
from functools import lru_cache
from typing import Any

from eth_abi.abi import encode, is_encodable
from eth_typing import ChecksumAddress
from eth_typing.abi import TypeStr
from geodefi.globals.constants import ZERO_ADDRESS
from hexbytes import HexBytes
from web3.contract.contract import Contract

from src.exceptions import EncodingError
from src.globals import get_logger, get_sdk
from src.helpers.portal import fetch_oracle_address


# TODO:(later) you can use this for multiple times calling cache functions! wow:
# Any function that takes block_height etc can take lru_cache:
# we will search for block_identifier and do that later.
# cache size can be dynamic too.
@lru_cache(maxsize=1)
def get_gnosis_safe(oracle_address: ChecksumAddress) -> Contract:
    """
    Retrieves the Gnosis Safe contract instance.

    Args:
        oracle_address (ChecksumAddress): The Ethereum address of the Gnosis Safe contract.
    Returns:
        Contract: An instance of the Gnosis Safe contract.
    """
    try:
        gnosis_abi_path = os.path.join("src", "assets", "gnosis.json")
        with open(gnosis_abi_path, encoding="utf8") as gnosis_file:
            gnosis_abi = json.load(gnosis_file)
        return get_sdk().w3.eth.contract(address=oracle_address, abi=gnosis_abi)
    except FileNotFoundError:
        get_logger().error(f"Gnosis ABI file not found at {gnosis_abi_path}")
        raise
    except json.JSONDecodeError as e:
        get_logger().error(f"Error decoding Gnosis ABI JSON: {e}")
        raise
    except Exception as e:
        get_logger().error(f"Failed to get Gnosis Safe contract: {e}")
        raise


def get_nonce() -> int:
    """
    Retrieves the current nonce for the Gnosis Safe contract.

    Returns:
        int: The current nonce value.
    """
    try:
        return (
            get_gnosis_safe(oracle_address=fetch_oracle_address(block_identifier="latest"))
            .functions.nonce()
            .call()
        )
    except Exception as e:
        get_logger().error(f"Failed to retrieve nonce: {e}")
        raise


def get_hash(target: str, data: str, nonce: int) -> str:
    """
    Generates the transaction hash for a Gnosis Safe transaction.

    Args:
        target (str): The target address for the transaction.
        data (str): The encoded transaction data.
        nonce (int): The current nonce of the Gnosis Safe.

    Returns:
        str: The hexadecimal representation of the transaction hash.
    """
    return get_sdk().w3.to_hex(
        get_gnosis_safe(oracle_address=fetch_oracle_address(block_identifier="latest"))
        .functions.getTransactionHash(
            target,
            0,  # value
            data,
            0,  # operation
            0,  # safeTxGas
            0,  # baseGas
            0,  # gasPrice
            ZERO_ADDRESS,  # gasToken
            ZERO_ADDRESS,  # refundReceiver
            nonce,
        )
        .call()
    )


def get_encoded_data(
    method_id: str,
    param_types: list[TypeStr],
    param_args: list[Any],
) -> str:
    """
    Encodes the method ID and parameters for a contract transaction.

    Args:
        method_id (str): The method identifier (function selector) in hexadecimal.
        param_types (list[TypeStr]): A list of parameter type strings.
        param_args (list[Any]): A list of arguments corresponding to the parameter types.

    Returns:
        str: The concatenated method ID and encoded parameters in hexadecimal.

    Raises:
        EncodingError: If the types and arguments do not match or encoding fails.
    """
    if len(param_types) != len(param_args):
        raise EncodingError("The types and args must have same length.")

    if not all(is_encodable(t, v) for t, v in zip(param_types, param_args)):
        raise EncodingError("One or more types and args are not encodable.")

    try:
        return method_id + encode(param_types, param_args).hex()
    except Exception as e:
        raise EncodingError("Could not encode parameters during transaction creation") from e


def prepare_tx(
    safe_nonce: int,
    target: str,
    method_id: str,
    types: list[TypeStr],
    values: list[Any],
) -> dict[str, str]:
    """
    Prepares a dictionary for Gnosis Safe contract transactions.

    Args:
        safe_nonce (int): The current nonce of the Gnosis Safe.
        target (str): The target address for the transaction.
        method_id (str): The method identifier (function selector) in hexadecimal.
        types (list[TypeStr]): A list of parameter type strings.
        values (list[Any]): A list of arguments corresponding to the parameter types.

    Returns:
        dict: transaction details in the expected form for watchers:
            - target (str)
            - hash (str)
            - signature (str)
            - encoded data (str)
    """
    get_logger().info(f"Preparing transaction with nonce: {safe_nonce}")

    signer = get_sdk().w3.eth.account.from_key(os.getenv("GEOSCOPE_PRIVATE_KEY"))

    encoded_data = get_encoded_data(method_id, types, values)
    tx_hash = get_hash(target, encoded_data, safe_nonce)

    contract_transaction_hash = HexBytes(tx_hash)

    sig = signer.signHash(contract_transaction_hash)
    signature = sig.signature.hex()

    get_logger().debug(
        f"Nonce:{safe_nonce}, Hash:{tx_hash}, Signature: {signature},Encoded data: {encoded_data},"
    )

    return {
        "target": target,
        "hash": tx_hash,
        "signature": signature,
        "encodedData": encoded_data,
    }
