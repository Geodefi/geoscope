# -*- coding: utf-8 -*-

import os
import json
from typing import List, Any


from web3.contract import Contract
from web3.exceptions import ContractLogicError
from eth_abi import encode, is_encodable
from eth_typing import ChecksumAddress
from hexbytes import HexBytes
from geodefi.globals.constants import ZERO_ADDRESS

from src.globals import get_sdk, get_logger, get_config
from src.exceptions import ContractCreationError

# TODO: Many of these are displaced.
# Check this.


def get_caller_data():
    """
    Gets the caller's private key, address, and nonce.

    Returns:
        Tuple[str, str, int]: A tuple containing the private key, address, and nonce.
    """

    private_key = os.getenv("GEOSCOPE_PRIVATE_KEY")
    if private_key is None:
        raise Exception("GEOSCOPE_PRIVATE_KEY is not set.")

    try:
        address = get_sdk().w3.eth.account.from_key(private_key).address
    except Exception as e:
        raise Exception("Invalid GEOSCOPE_PRIVATE_KEY") from e

    address = get_sdk().w3.to_checksum_address(address)

    nonce = get_sdk().w3.eth.get_transaction_count(address)

    return private_key, address, nonce


def get_gnosis_safe(oracle_address: str) -> Contract:
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

    # TODO: this should be done at the initiation...
    with open(gnosis_abi_path, encoding="utf8") as gnosis_file:
        gnosis_abi = json.load(gnosis_file)

    return get_sdk().w3.eth.contract(abi=gnosis_abi, address=oracle_address)


def get_nonce(gnosis_contract: Contract) -> int:
    """
    Gets the nonce for the Gnosis Safe contract.

    Args:
        gnosis_contract (Contract): The Gnosis Safe contract instance.

    Returns:
        int: The nonce for the Gnosis Safe contract.
    """
    return int(gnosis_contract.functions.nonce().call())


def get_transaction_hash(
    gnosis_contract: Contract, to: ChecksumAddress, data: HexBytes, nonce: int
) -> HexBytes:
    """
    Gets the transaction hash for a Gnosis Safe transaction.

    Args:
        gnosis_contract (Contract): The Gnosis Safe contract instance.
        to (ChecksumAddress): The address of the target contract.
        data (HexBytes): The encoded data for the transaction.
        nonce (int): The nonce for the transaction.

    Returns:
        HexBytes: The transaction hash.
    """

    return get_sdk().w3.to_hex(
        gnosis_contract.functions.getTransactionHash(
            to,
            0,  # value
            data,
            0,  # operation
            0,  # safeTxGas
            0,  # baseGas
            0,  # gasPrice
            ZERO_ADDRESS,  # gasToken
            ZERO_ADDRESS,  # refundReceiver
            nonce,
        ).call()
    )


def sign(tx_hash: HexBytes, private_key: HexBytes) -> HexBytes:
    """
    Signs a transaction hash with the provided private key.

    Args:
        tx_hash (HexBytes): The transaction hash to sign.
        private_key (HexBytes): The private key to sign with.

    Returns:
        str: The hex-encoded signature.
    """
    contract_transaction_hash = HexBytes(tx_hash)
    account = get_sdk().w3.eth.account.from_key(private_key)

    # Sign
    signature = account.signHash(contract_transaction_hash)

    # Return in hex-encoded
    return signature.signature.hex()


def exec_transaction(
    gnosis_contract: Contract,
    to: ChecksumAddress,
    data: HexBytes,
    signatures: str,
    caller_private_key: str,
    caller_address: str,
    caller_nonce: int,
):
    """
    Executes a transaction on the Gnosis Safe.

    Args:
        gnosis_contract (Contract): The Gnosis Safe contract instance.
        to (ChecksumAddress): The address of the target contract.
        data (HexBytes): The encoded data for the transaction.
        signatures (str): The signatures for the transaction.
        caller_private_key (str): The private key of the caller.
        caller_address (str): The address of the caller.
        caller_nonce (int): The nonce of the caller.

    Returns:
        Tuple[int, Any]: A tuple containing the success status and the transaction receipt.
    """
    tx = gnosis_contract.functions.execTransaction(
        to,
        0,  # value
        data,
        0,  # operation
        0,  # safeTxGas
        0,  # baseGas
        0,  # gasPrice
        ZERO_ADDRESS,  # gasToken
        ZERO_ADDRESS,  # refundReceiver
        signatures,
    ).buildTransaction({"from": caller_address})
    tx["nonce"] = caller_nonce

    signed = get_sdk().w3.eth.account.sign_transaction(tx, caller_private_key)
    tx_hash = get_sdk().w3.eth.sendRawTransaction(signed.rawTransaction)

    get_logger().debug("TX has been sent. Waiting for receipt...")
    tx_receipt = get_sdk().w3.eth.waitForTransactionReceipt(tx_hash)

    if tx_receipt.status == 1:
        get_logger().info(f"TX successful: {dict(tx_receipt)['transactionHash'].hex()}")
        return 1, tx_receipt
    else:
        get_logger().error(f"TX reverted: {dict(tx_receipt)['transactionHash'].hex()}")
        return 0, tx_receipt


def get_encoded_data(
    method_id: str,
    param_types: List[str],
    param_args: List[Any],
):
    assert len(param_types) == len(param_args), "The types and args must have same length."
    # assert is_encodable(param_types, param_args), "The types and args are not encodable."

    return method_id + encode(param_types, param_args).hex()


def send_tx(
    contract_address: ChecksumAddress,
    method_id: str,
    param_types: List[str],
    param_args: List[Any],
):
    """
    Sends a transaction to the Gnosis Safe contract.

    Args:
        contract_address (ChecksumAddress): The address of the target contract.
        method_id (str): The method ID of the target function.
        param_types (List[str]): The types of the arguments for the function.
        param_args (List[Any]): The arguments for the function.

    Returns:
        Tuple[int, Any]: A tuple containing the success status and the transaction receipt.
    """
    encoded_data = get_encoded_data(method_id, param_types, param_args)

    gnosis_contract = get_gnosis_safe("lol")
    # get Nonce
    safe_nonce = get_nonce(gnosis_contract)
    get_logger().debug(f"Nonce of Gnosis Safe is {safe_nonce}.")

    # get Tx Hash
    try:
        safe_tx_hash: HexBytes = get_transaction_hash(
            gnosis_contract, contract_address, encoded_data, safe_nonce
        )
    except Exception as e:
        raise Exception("Failed to get the transaction hash.") from e

    caller_private_key, caller_address, caller_nonce = get_caller_data()
    # sign
    signature = sign(safe_tx_hash, caller_private_key)

    # execution
    success: int = 0
    tx_receipt = None
    try:
        success, tx_receipt = exec_transaction(
            gnosis_contract,
            contract_address,
            encoded_data,
            signature,
            caller_private_key,
            caller_address,
            caller_nonce,
        )

    except ContractLogicError as e:
        # This spesific error is related with gnosis gas fees.
        if str(e) == "execution reverted: GS026":
            raise  # TODO: This error should be handled!
        else:
            get_logger().warning(f"This error has been ignored: {e}")

    return success, tx_receipt
