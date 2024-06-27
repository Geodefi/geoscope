# -*- coding: utf-8 -*-

from web3.types import TxReceipt
from web3.exceptions import TimeExhausted

from src.globals import SDK, PRIVATE_KEY
from src.exceptions import CallFailedError
from src.logger import log
from src.utils import get_gas


# pylint: disable-next=invalid-name
def call_updateVerificationIndex(
    validator_verification_index: int,
    alienated_pubkeys: list[str],
) -> bool:
    """Transact on updateVerificationIndex function with given validatorVerificationIndex
    and alienatedPubkeys.

    This function initiates a transaction to update the verification index of a validator.
    It takes the validatorVerificationIndex and a list of alienatedPubkeys as input parameters.
    The function will return True if the transaction is successful, and False otherwise.

    Args:
        validatorVerificationIndex (int): The verification index of the latest verified validator.
        alienatedPubkeys (list[str]): A list of alienated public keys.

    Returns:
        bool: True if the updateVerificationIndex call is successful, False otherwise.

    Raises:
        TimeExhausted: Raised if the transaction takes too long to be mined.
        CallFailedError: Raised if the proposeStake call fails.
    """

    log.debug("Calling updateVerificationIndex() from portal")

    try:
        tx: dict = SDK.portal.contract.functions.updateVerificationIndex(
            validator_verification_index, alienated_pubkeys
        ).build_transaction(get_gas())

        signed_tx = SDK.w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash: bytes = SDK.w3.eth.send_raw_transaction(
            signed_tx.raw_transaction
        )

        log.info(f"updateVerificationIndex tx is created: {tx_hash}")

        # Wait for the transaction to be mined, and get the transaction receipt
        tx_receipt: TxReceipt = SDK.portal.w3.eth.wait_for_transaction_receipt(
            tx_hash
        )
        log.info(f"updateVerificationIndex tx is concluded: {tx_receipt}")

        return True

    except TimeExhausted as e:
        log.error(f"updateVerificationIndex tx could not conclude in time: {e}")
        raise e
    except Exception as e:
        log.error(f"updateVerificationIndex tx failed: {e}")
        raise CallFailedError(
            "Failed to call updateVerificationIndex on portal contract"
        ) from e


# pylint: disable-next=invalid-name
def call_reportBeacon(
    price_merkle_root: str,
    balances_merkle_root: str,
    all_validators_count: int,
) -> bool:
    """
    Transact on reportBeacon function with given priceMerkleRoot, balancesMerkleRoot
    and allValidatorsCount.

    This function initiates a transaction to report the beacon. It takes the priceMerkleRoot,
    balancesMerkleRoot and allValidatorsCount as input parameters.
    The function will return True if the transaction is successful, and False otherwise.

    Args:
        priceMerkleRoot (str): The Merkle root of the price data.
        balancesMerkleRoot (str): The Merkle root of the balances data.
        allValidatorsCount (int): The number of all validators.

    Returns:
        bool: True if the reportBeacon call is successful, False otherwise.

    Raises:
        TimeExhausted: Raised if the transaction takes too long to be mined.
        CallFailedError: Raised if the proposeStake call fails.
    """

    log.debug("Calling reportBeacon() from portal")

    try:
        tx: dict = SDK.portal.contract.functions.reportBeacon(
            price_merkle_root, balances_merkle_root, all_validators_count
        ).build_transaction(get_gas())

        signed_tx = SDK.w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash: bytes = SDK.w3.eth.send_raw_transaction(
            signed_tx.raw_transaction
        )

        log.info(f"reportBeacon tx is created: {tx_hash}")

        # Wait for the transaction to be mined, and get the transaction receipt
        tx_receipt: TxReceipt = SDK.portal.w3.eth.wait_for_transaction_receipt(
            tx_hash
        )
        log.info(f"reportBeacon tx is concluded: {tx_receipt}")

        return True

    except TimeExhausted as e:
        log.error(f"reportBeacon tx could not conclude in time: {e}")
        raise e
    except Exception as e:
        log.error(f"reportBeacon tx failed: {e}")
        raise CallFailedError(
            "Failed to call reportBeacon on portal contract"
        ) from e


# pylint: disable-next=invalid-name
def call_blameProposal(pk: str) -> bool:
    """
    Transact on blameProposal function with given private key.

    This function initiates a transaction to blame a proposal.
    It takes the proposalId and blame as input parameters.
    The function will return True if the transaction is successful, and False otherwise.

    Args:
        proposalId (int): The ID of the proposal to be blamed.
        blame (str): The blame message.

    Returns:
        bool: True if the blameProposal call is successful, False otherwise.

    Raises:
        TimeExhausted: Raised if the transaction takes too long to be mined.
        CallFailedError: Raised if the proposeStake call fails.
    """

    log.debug("Calling blameProposal() from portal")

    try:
        tx: dict = SDK.portal.contract.functions.blameProposal(
            pk
        ).build_transaction(get_gas())

        signed_tx = SDK.w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash: bytes = SDK.w3.eth.send_raw_transaction(
            signed_tx.raw_transaction
        )

        log.info(f"blameProposal tx is created: {tx_hash}")

        # Wait for the transaction to be mined, and get the transaction receipt
        tx_receipt: TxReceipt = SDK.portal.w3.eth.wait_for_transaction_receipt(
            tx_hash
        )
        log.info(f"blameProposal tx is concluded: {tx_receipt}")

        return True

    except TimeExhausted as e:
        log.error(f"blameProposal tx could not conclude in time: {e}")
        raise e
    except Exception as e:
        log.error(f"blameProposal tx failed: {e}")
        raise CallFailedError(
            "Failed to call blameProposal on portal contract"
        ) from e


# pylint: disable-next=invalid-name
def call_blameExit(
    pk: str,
    beacon_balance: int,
    withdrawn_balance: int,
    balance_proof: list[str],
) -> bool:
    """
    Transact on blameExit function with given pk, beaconBalance, withdrawnBalance and balanceProof.

    This function initiates a transaction to blame an exit.
    It takes the pk, beaconBalance, withdrawnBalance and balanceProof as input parameters.
    The function will return True if the transaction is successful, and False otherwise.

    Args:
        pk (str): The public key of the validator to be blamed.
        beaconBalance (int): The balance of the validator in the beacon chain.
        withdrawnBalance (int): The balance of the validator in the withdrawal chain.
        balanceProof (list[str]): The balance proof of the validator.

    Returns:
        bool: True if the blameExit call is successful, False otherwise.

    Raises:
        TimeExhausted: Raised if the transaction takes too long to be mined.
        CallFailedError: Raised if the proposeStake call fails.
    """

    log.debug("Calling blameExit() from portal")

    try:
        tx: dict = SDK.portal.contract.functions.blameExit(
            pk, beacon_balance, withdrawn_balance, balance_proof
        ).build_transaction(get_gas())

        signed_tx = SDK.w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash: bytes = SDK.w3.eth.send_raw_transaction(
            signed_tx.raw_transaction
        )

        log.info(f"blameExit tx is created: {tx_hash}")

        # Wait for the transaction to be mined, and get the transaction receipt
        tx_receipt: TxReceipt = SDK.portal.w3.eth.wait_for_transaction_receipt(
            tx_hash
        )
        log.info(f"blameExit tx is concluded: {tx_receipt}")

        return True

    except TimeExhausted as e:
        log.error(f"blameExit tx could not conclude in time: {e}")
        raise e
    except Exception as e:
        log.error(f"blameExit tx failed: {e}")
        raise CallFailedError(
            "Failed to call blameExit on portal contract"
        ) from e
