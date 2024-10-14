# -*- coding: utf-8 -*-

import os
import json
from hexbytes import HexBytes
from eth_abi import encode, is_encodable


from geodefi.globals.constants import ZERO_ADDRESS
from src.exceptions import EncodingError
from src.globals import get_sdk, get_constants


def get_gnosis_safe(oracle_address: str):
    """
    Gets the Gnosis Safe contract instance.

    Returns:
        Contract: The Gnosis Safe contract instance.
    """

    gnosis_abi_path = os.path.join(
        "src",
        "assets",
        "gnosis.json",
    )

    with open(gnosis_abi_path, encoding="utf8") as gnosis_file:
        gnosis_abi = json.load(gnosis_file)

    return get_sdk().w3.eth.contract(abi=gnosis_abi, address=oracle_address)


def get_nonce() -> int:
    """
    Gets the nonce for the Gnosis Safe contract.

    Args:
        gnosis_contract (Contract): The Gnosis Safe contract instance.

    Returns:
        int: The nonce for the Gnosis Safe contract.
    """
    return int(get_constants().oracle.functions.nonce().call())


def get_hash(target, data, nonce):
    return get_sdk().w3.to_hex(
        get_constants()
        .oracle.functions.getTransactionHash(
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
    param_types: list[str],
    param_args: list[str],
):
    if len(param_types) != len(param_args):
        raise EncodingError("The types and args must have same length.")

    if not is_encodable(param_types, param_args):
        raise EncodingError("The types and args are not encodable.")

    try:
        return method_id + encode(param_types, param_args).hex()
    except Exception as e:
        raise EncodingError("Could not encode parameters during transaction creation") from e


def prepare_tx(safe_nonce, target, method_id, types, values):
    signer = get_constants().signer

    encoded_data = get_encoded_data(method_id, types, values)
    tx_hash = get_hash(target, encoded_data, safe_nonce)

    contract_transaction_hash = HexBytes(tx_hash)

    sig = signer.signHash(contract_transaction_hash)
    signature = sig.signature.hex()

    return {
        "target": target,
        "hash": tx_hash,
        "signature": signature,
        "encodedData": encoded_data,
    }
