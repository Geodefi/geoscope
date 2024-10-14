# -*- coding: utf-8 -*-

from web3.exceptions import TimeExhausted
from src.exceptions import (
    CallFailedError,
)
from src.globals import get_sdk, get_logger
from src.utils.gas import get_gas


def tx_params() -> dict:

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
):
    # {
    #   "inputs": [
    #     {
    #       "internalType": "bytes32",
    #       "name": "priceMerkleRoot",
    #       "type": "bytes32"
    #     },
    #     {
    #       "internalType": "bytes32",
    #       "name": "balanceMerkleRoot",
    #       "type": "bytes32"
    #     },
    #     {
    #       "internalType": "uint256",
    #       "name": "allValidatorsCount",
    #       "type": "uint256"
    #     }
    #   ],
    #   "name": "reportBeacon",
    #   "outputs": [],
    #   "stateMutability": "nonpayable",
    #   "type": "function"
    # }
    try:
        get_logger().debug(
            "Calling reportBeacon on Portal.",
            f" Roots: {price_merkle_root, balance_merkle_root}.",
            f" Validator count: {all_validators_count}.",
        )

        tx_hash = (
            get_sdk()
            .portal.functions.reportBeacon(
                price_merkle_root, balance_merkle_root, all_validators_count
            )
            .transact(tx_params())
        )

        get_logger().etherscan("reportBeacon", tx_hash)

    except TimeExhausted as e:
        get_logger().error(f"proposeStake tx could not conclude in time.")
        raise e
    except Exception as e:
        raise CallFailedError("Failed to call proposeStake on portal contract") from e


# pylint: disable-next=invalid-name
def transact_regulateOperators(
    fee_thefts: list[int],
    proofs: list[bytes],
):
    #   {
    #   "inputs": [
    #     {
    #       "internalType": "uint256[]",
    #       "name": "feeThefts",
    #       "type": "uint256[]"
    #     },
    #     {
    #       "internalType": "bytes[]",
    #       "name": "proofs",
    #       "type": "bytes[]"
    #     }
    #   ],
    #   "name": "regulateOperators",
    #   "outputs": [],
    #   "stateMutability": "nonpayable",
    #   "type": "function"
    # }
    try:
        get_logger().debug(f"Calling reportBeacon on Portal for {fee_thefts}")

        tx_hash = (
            get_sdk().portal.functions.regulateOperators(fee_thefts, proofs).transact(tx_params())
        )

        get_logger().etherscan("reportBeacon", tx_hash)

    except TimeExhausted as e:
        get_logger().error(f"regulateOperators tx could not conclude in time.")
        raise e
    except Exception as e:
        raise CallFailedError("Failed to call regulateOperators on portal contract") from e


# pylint: disable-next=invalid-name
def transact_updateVerificationIndex(
    validator_verification_index: int,
    alienated_pubkeys: list[str],
):
    # {
    #     "inputs": [
    #         {"internalType": "uint256", "name": "validatorVerificationIndex", "type": "uint256"},
    #         {"internalType": "bytes[]", "name": "alienatedPubkeys", "type": "bytes[]"},
    #     ],
    #     "name": "updateVerificationIndex",
    #     "outputs": [],
    #     "stateMutability": "nonpayable",
    #     "type": "function",
    # }
    try:
        get_logger().debug(f"Calling reportBeacon on Portal for {validator_verification_index}")
        if alienated_pubkeys:
            get_logger().debug(f"Detected Aliens: {alienated_pubkeys}")

        tx_hash = (
            get_sdk()
            .portal.functions.updateVerificationIndex(
                validator_verification_index, alienated_pubkeys
            )
            .transact(tx_params())
        )

        get_logger().etherscan("reportBeacon", tx_hash)

    except TimeExhausted as e:
        get_logger().error(f"updateVerificationIndex tx could not conclude in time.")
        raise e
    except Exception as e:
        raise CallFailedError("Failed to call updateVerificationIndex on portal contract") from e
