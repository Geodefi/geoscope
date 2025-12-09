"""
Transaction Module for Geoscope.

Contains functions to interact with the Portal smart contract,
including reporting beacon data, regulating operators, and updating verification indices.
It handles transaction parameters and manages exceptions related to transaction failures.
"""

from eth_typing import HexStr
from web3.exceptions import TimeExhausted
from web3.types import BlockIdentifier

from src.actions.watchers import post_submit_batch
from src.exceptions import CallFailedError, MultiSigError
from src.globals import get_logger, get_sdk
from src.helpers.gnosis import get_gnosis_safe
from src.helpers.portal import fetch_oracle_address
from src.utils.gas import get_gas
from src.utils.log import etherscan


def tx_params() -> dict:
    """
    Retrieve transaction parameters for Ethereum transactions.

    Fetches the current gas fees using the `get_gas` utility function.
    If both `maxPriorityFeePerGas` and `maxFeePerGas` are available, it returns a dictionary
    containing these values. Otherwise, it returns an empty dictionary, allowing the
    Web3 library to use default gas parameters.

    Returns:
        dict: A dictionary with the following keys if available:
            - "maxPriorityFeePerGas" (int or float): The maximum priority fee per gas.
            - "maxFeePerGas" (int or float): The maximum fee per gas.
            Otherwise, an empty dictionary.
    """

    priority_fee, base_fee = get_gas()

    if priority_fee and base_fee:
        return {
            "maxPriorityFeePerGas": priority_fee,
            "maxFeePerGas": base_fee,
        }

    return {}


# pylint: disable-next=invalid-name
def transact_reportBeacon(
    price_merkle_root: bytes,
    balance_merkle_root: bytes,
    all_validators_count: int,
) -> None:
    """
    Execute the `reportBeacon` function on the Portal smart contract.

    Sends a transaction to the `reportBeacon` method of the Portal contract
    with the provided price and balance Merkle roots, along with the total count of validators.
    It handles the transaction process and raises appropriate exceptions if the transaction
    fails or does not conclude within the expected timeframe.

    Contract Function Interface:
    - name: "reportBeacon"
    - inputs:
        - priceMerkleRoot (bytes32)
        - balanceMerkleRoot (bytes32)
        - allValidatorsCount (uint256)
    - stateMutability: "nonpayable"

    Args:
        price_merkle_root (bytes): The Merkle root representing price data.
        balance_merkle_root (bytes): The Merkle root representing balance data.
        all_validators_count (int): The total number of validators in the network.

    Raises:
        TimeExhausted: If the transaction does not conclude within the expected time.
        CallFailedError: If the transaction fails due to a contract call error.
    """
    try:
        get_logger().debug(
            "Calling reportBeacon on Portal."
            f" Roots: {price_merkle_root, balance_merkle_root}."
            f" Validator count: {all_validators_count}."
        )

        tx_hash = (
            get_sdk()
            .portal.functions.reportBeacon(
                price_merkle_root, balance_merkle_root, all_validators_count
            )
            .transact(tx_params())
        )

        etherscan("reportBeacon", tx_hash)

        tx_receipt = get_sdk().w3.eth.wait_for_transaction_receipt(tx_hash)
        if tx_receipt["status"] != 1:
            raise CallFailedError("Transaction failed on the blockchain.")

    except TimeExhausted as e:
        get_logger().error("reportBeacon tx could not conclude in time.")
        raise e
    except Exception as e:
        raise CallFailedError("Failed to call reportBeacon on portal contract") from e


# pylint: disable-next=invalid-name
def transact_regulateOperators(
    fee_thefts: list[int],
    proofs: list[bytes],
) -> None:
    """
    Execute the `regulateOperators` function on the Portal smart contract.

    Sends a transaction to the `regulateOperators` method of the Portal contract
    with the provided list of fee thefts and corresponding proofs. It handles the transaction
    process and raises appropriate exceptions if the transaction fails or does not conclude
    within the expected timeframe.

    Contract Function Interface:
    - name: "regulateOperators"
    - inputs:
        - feeThefts (uint256[])
        - proofs (bytes[])
    - stateMutability: "nonpayable"

    Args:
        fee_thefts (list[int]): A list of fee theft amounts to regulate.
        proofs (list[bytes]): A list of proofs corresponding to each fee theft.

    Raises:
        TimeExhausted: If the transaction does not conclude within the expected time.
        CallFailedError: If the transaction fails due to a contract call error.
    """

    try:
        get_logger().debug(f"Calling reportBeacon on Portal for {fee_thefts}")

        tx_hash = (
            get_sdk().portal.functions.regulateOperators(fee_thefts, proofs).transact(tx_params())
        )

        etherscan("reportBeacon", tx_hash)

        tx_receipt = get_sdk().w3.eth.wait_for_transaction_receipt(tx_hash)
        if tx_receipt["status"] != 1:
            raise CallFailedError("Transaction failed on the blockchain.")

    except TimeExhausted as e:
        get_logger().error("regulateOperators tx could not conclude in time.")
        raise e
    except Exception as e:
        raise CallFailedError("Failed to call regulateOperators on portal contract") from e


# pylint: disable-next=invalid-name
def transact_updateVerificationIndex(
    validator_verification_index: int,
    alienated_pubkeys: list[str],
) -> None:
    """
    Execute the `updateVerificationIndex` function on the Portal smart contract.

    Sends a transaction to the `updateVerificationIndex` method of the Portal contract
    with the provided validator verification index and a list of alienated public keys. It handles
    the transaction process and raises appropriate exceptions if the transaction fails or does not
    conclude within the expected timeframe.

    Contract Function Interface:
    - name: "validatorVerificationIndex"
    - inputs:
        - alienatedPubkeys (uint256)
        - updateVerificationIndex (bytes[])
    - stateMutability: "nonpayable"


    Args:
        validator_verification_index (int): The current verification index for validators.
        alienated_pubkeys (list[str]): A list of public keys that have been alienated.

    Raises:
        TimeExhausted: If the transaction does not conclude within the expected time.
        CallFailedError: If the transaction fails due to a contract call error.
    """

    try:
        get_logger().debug(
            f"Calling updateVerificationIndex on Portal for {validator_verification_index}"
        )
        if alienated_pubkeys:
            get_logger().info(f"Detected Aliens: {alienated_pubkeys}")

        tx_hash = (
            get_sdk()
            .portal.functions.updateVerificationIndex(
                validator_verification_index, alienated_pubkeys
            )
            .transact(tx_params())
        )

        etherscan("updateVerificationIndex", tx_hash)

        tx_receipt = get_sdk().w3.eth.wait_for_transaction_receipt(tx_hash)
        if tx_receipt["status"] != 1:
            raise CallFailedError("Transaction failed on the blockchain.")

    except TimeExhausted as e:
        get_logger().error("updateVerificationIndex tx could not conclude in time.")
        raise e
    except Exception as e:
        raise CallFailedError(
            "Failed to execute updateVerificationIndex on the Portal contract."
        ) from e


def handle_report_beacon(
    price_merkle_root: HexStr,
    balance_merkle_root: HexStr,
    all_validators_count: int,
    block_identifier: BlockIdentifier,
) -> bool:
    """Reports the beacon
     - oracle is the owner's address->  no multisig         ->  portal.reportBeacon
     - oracle is not owner's address->  signer on multisig  ->  watcher.submit
    Args:
        price_merkle_root (str): The price merkle root.
        balance_merkle_root (str): The balance merkle root.
        all_validators_count (int): The all validators count.
        block_identifier (str): The identifier for the block to handle reportBeacon call.
    """
    try:
        signer_address = get_sdk().w3.eth.default_account

        oracle_address = fetch_oracle_address(block_identifier=block_identifier)

        if signer_address == oracle_address:
            transact_reportBeacon(
                bytes.fromhex(price_merkle_root),
                bytes.fromhex(balance_merkle_root),
                all_validators_count,
            )
            return True

        safe_owners: list = (
            get_gnosis_safe(oracle_address=oracle_address).functions.getOwners().call()
        )

        if signer_address in safe_owners:
            method_id = "0xdf1ff929"
            types: list = ["bytes32", "bytes32", "uint256"]

            post_submit_batch(
                method_id=method_id,
                param_types=types,
                param_args=[price_merkle_root, balance_merkle_root, all_validators_count],
            )
        else:
            raise MultiSigError("You are not authorized as a multisig member for Oracle")

        return True

    # pylint: disable-next=broad-exception-caught
    except Exception as e:
        get_logger().error(f"Error while handling reportBeacon call: {e}")
        return False


def handle_regulate_operators(
    fee_thefts: list[int],
    proofs: list[bytes],
    block_identifier: BlockIdentifier,
) -> bool:
    """Reports the beacon
     - oracle is the owner's address->  no multisig         ->  portal.updateVerificationIndex
     - oracle is not owner's address->  signer on multisig  ->  watcher.submit
    Args:
        fee_thefts (list[int]): A list of fee theft amounts to regulate.
         (Fee theft is when an operator steals a block)
        proofs (list[bytes]): A list of proofs corresponding to each fee theft.
        block_identifier (str): The identifier for the block to handle regulateOperators call.
    """
    try:
        signer_address = get_sdk().w3.eth.default_account

        oracle_address = fetch_oracle_address(block_identifier=block_identifier)
        if signer_address == oracle_address:
            transact_regulateOperators(fee_thefts, proofs)
            return True

        safe_owners: list = (
            get_gnosis_safe(oracle_address=oracle_address)
            .functions.getOwners()
            .call(block_identifier="latest")
        )

        if signer_address in safe_owners:
            method_id = "0xaf6561ef"
            types: list = ["uint256[]", "bytes[]"]

            post_submit_batch(
                method_id=method_id,
                param_types=types,
                param_args=[fee_thefts, proofs],
            )
        else:
            raise MultiSigError("You are not authorized as a multisig member for Oracle")

        return True

    # pylint: disable-next=broad-exception-caught
    except Exception as e:
        get_logger().error(f"Error while handling regulateOperators call: {e}")
        return False


def handle_update_verification_index(
    validator_verification_index: int,
    alienated_pubkeys: list[str],
    block_identifier: BlockIdentifier,
) -> bool:
    """Reports the beacon
     - oracle is the owner's address->  no multisig         ->  portal.regulateOperators
     - oracle is not owner's address->  signer on multisig  ->  watcher.submit
    Args:
        validator_verification_index (int): The current verification index for validators.
        alienated_pubkeys (list[str]): A list of public keys that have been alienated.
        block_identifier (str): The identifier for the block to handle updateVerificationIndex call.
    """
    try:

        signer_address = get_sdk().w3.eth.default_account

        oracle_address = fetch_oracle_address(block_identifier=block_identifier)

        if signer_address == oracle_address:
            transact_updateVerificationIndex(validator_verification_index, alienated_pubkeys)
            return True

        safe_owners: list = (
            get_gnosis_safe(oracle_address=oracle_address)
            .functions.getOwners()
            .call(block_identifier="latest")
        )

        if signer_address in safe_owners:
            method_id = "0x26eef2c0"
            types: list = ["uint256", "bytes[]"]

            post_submit_batch(
                method_id=method_id,
                param_types=types,
                param_args=[validator_verification_index, alienated_pubkeys],
            )
        else:
            raise MultiSigError("You are not authorized as a multisig member for Oracle")

        return True

    # pylint: disable-next=broad-exception-caught
    except Exception as e:
        get_logger().error(f"Error while handling updateVerificationIndex call: {e}")
        return False
