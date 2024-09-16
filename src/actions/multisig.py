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


def get_caller_data():
    private_key = os.getenv("GEOSCOPE_PRIVATE_KEY")
    if private_key is None:
        raise Exception("GEOSCOPE_PRIVATE_KEY is not set.")

    try:
        address = get_sdk().w3.eth.account.from_key(private_key).address
    except Exception as e:
        raise Exception("Invalid GEOSCOPE_PRIVATE_KEY") from e

    if not get_sdk().w3.is_checksum_address(address):
        address = get_sdk().w3.to_checksum_address(address)

    nonce = get_sdk().w3.eth.get_transaction_count(address)

    return private_key, address, nonce


def get_gnosis() -> Contract:
    gnosis_abi_path = os.path.join(
        get_config().abi_directory.folder_name,
        get_config().abi_directory.files.gnosis,
    )

    # Get ABI
    with open(gnosis_abi_path, "r") as file:
        a = file.read()
    abi = json.loads(a)

    try:
        address = abi["address"]
        if not get_sdk().w3.is_checksum_address(address):
            address = get_sdk().w3.to_checksum_address(address)

        safe_address: ChecksumAddress = address
        abi = abi["abi"]

    except KeyError as e:
        raise ContractCreationError(
            "GeodeFinance: Please provide correct Gnosis abi and contract address in abi/.json"
        ) from e

    try:
        return get_sdk().w3.eth.contract(abi=abi, address=safe_address)
    except Exception as e:
        raise ContractCreationError("GeodeFinance: Gnosis- Invalid ABI or Contract Address") from e


def get_nonce(gnosis_contract: Contract) -> int:
    """
    :returns nonce: the nonce value of safe-contract
    """
    return int(gnosis_contract.functions.nonce().call())


def get_transaction_hash(
    gnosis_contract: Contract, to: ChecksumAddress, data: HexBytes, nonce: int
) -> HexBytes:
    """
    :param to: address of target contract (portal)
    :param data: hex-encoded input data
    :param nonce: the nonce value of safe-contract

    :returns: hex-encoded transaction hash
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
    :param tx_hash: hex-encoded safe transaction to sign
    :param private_key: hex-encoded private key
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
    :param to: address of target contract (portal)
    :param data: hex-encoded input data
    :param signatures: the results of sign by each owner concatted.
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


def send_tx(
    contract_address: ChecksumAddress,
    method_id: str,
    param_types: List[str],
    param_args: List[Any],
):
    """
    :param contract_address: The address of target contract. (Not Safe contract)
    :param PLANET_ID: The registered Planet ID
    :param OPERATOR_ID: The list of target opearators.
    :param balanceIncrease: The list of how much avax has been gained by staking per operator.
    """

    assert len(param_types) == len(param_args), "The types and args must have same length."
    assert is_encodable(param_types, param_args), "The types and args are not encodable."

    encoded_data = method_id + encode(param_types, param_args).hex()

    gnosis_contract = get_gnosis()
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
