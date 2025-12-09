"""
Helper functions for validator related operations, such as 
* gathering validator related information, 
* updating database 
* verifying validator deposits
"""

from itertools import repeat
from typing import Iterator

from eth_typing import BLSPubkey, BLSSignature
from geodefi.globals import DEPOSIT_SIZE, GENESIS_FORK_VERSION
from geodefi.utils import to_bytes32
from py_ecc.bls.ciphersuites import G2ProofOfPossession as bls
from web3.types import BlockIdentifier

from src.common import BigInteger
from src.database.validators import insert_validators_batch, read_validators_by_pool
from src.exceptions import SignatureError
from src.globals import get_config, get_logger, get_sdk
from src.globals.constants.config import (
    CHAIN_INTERVAL_FIELD,
    CHAIN_NAME_FIELD,
    STRATEGY_MAX_PENDING_VALIDATORS_FIELD,
    STRATEGY_MAX_VERIFICATION_DELAY_FIELD,
    STRATEGY_MIN_VERIFICATION_DELAY_FIELD,
)
from src.helpers.beacon import fetch_validators_batch
from src.helpers.portal import fetch_portal_validator_constants_batch, fetch_proposed_pubkeys
from src.utils.bls import DepositMessage, compute_deposit_domain, compute_signing_root
from src.utils.thread import multithread


def should_verify_validators(
    slot: int, validators: list[tuple[str, int, BigInteger, str, str, str, str, int]]
) -> bool:
    """Checks if it is yet the correct time to verify:
    1.  ANY validator have been waiting for > MAX_VERIFICATION_DELAY
    OR
    2.  has been > MAX_PENDING_PROPOSALS validator proposals
        AND
        has been > MIN_VERIFICATION_DELAY since the last proposal

    Args:
        slot (int): The h slot number.
        validators (list[tuple[str, int, BigInteger, str, str, str, str, int]]): List of validators:
            - VALIDATORS_PUBKEY_FIELD (str)
            - VALIDATORS_PORTAL_INDEX_FIELD (int)
            - VALIDATORS_POOL_ID_FIELD (BigInteger)
            - VALIDATORS_SIGNATURE31_FIELD (str)
            - VALIDATORS_WITHDRAWAL_CREDENTIALS_FIELD (str)
            - VALIDATORS_PROPOSAL_SIGNATURE_FIELD (str)
            - VALIDATORS_STAKE_SIGNATURE_FIELD (str)
            - VALIDATORS_PROPOSAL_SLOT_FIELD (int)

    Returns:
        bool: True if verification should proceed, False otherwise.
    """
    chain_interval = get_config(field=CHAIN_INTERVAL_FIELD)

    # 7 corresponds to VALIDATORS_PROPOSAL_SLOT_FIELD
    min_slot: int = min(validators, key=lambda x: x[7])[7]
    min_slot_delay = (slot - min_slot) * chain_interval
    max_verification_delay = get_config(field=STRATEGY_MAX_VERIFICATION_DELAY_FIELD)
    if min_slot_delay > max_verification_delay:
        get_logger().debug(
            f"Slot delay ({min_slot_delay}) exceeds \
                max verification delay strategy ({max_verification_delay})."
        )
        return True

    max_pending_validators = get_config(field=STRATEGY_MAX_PENDING_VALIDATORS_FIELD)
    if len(validators) > max_pending_validators:
        # 7 corresponds to VALIDATORS_PROPOSAL_SLOT_FIELD
        max_slot: int = max(validators, key=lambda x: x[7])[7]
        max_slot_delay = (slot - max_slot) * chain_interval
        min_verification_delay = get_config(field=STRATEGY_MIN_VERIFICATION_DELAY_FIELD)
        if max_slot_delay > min_verification_delay:
            get_logger().debug(
                f"Slot delay ({max_slot_delay}) exceeds \
                    min verification delay strategy ({min_verification_delay})."
            )
            return True

    return False


def verify_signature(
    signature: bytes, pubkey: bytes, withdrawal_credentials: str, fork_version: bytes, amount: int
) -> bool:
    """
    Verifies the BLS signature of a deposit message.

    Args:
        signature (bytes): The BLS signature to verify.
        pubkey (bytes): The BLS public key of the validator.
        withdrawal_credentials (str): The withdrawal credentials.
        fork_version (bytes): The fork version for domain computation.
        amount (int): The amount deposited.

    Returns:
        bool: True if the signature is valid, False otherwise.
    """
    # Verify deposit signature && pubkey
    try:
        deposit_message = DepositMessage(pubkey, withdrawal_credentials, amount)
        domain = compute_deposit_domain(fork_version)
        signing_root = compute_signing_root(deposit_message, domain)
        is_valid = bls.Verify(BLSPubkey(pubkey), signing_root, BLSSignature(signature))
        get_logger().debug(f"({pubkey.decode()}): Signature verification result: {is_valid}")
        return is_valid
    except Exception as e:
        get_logger().error(f"Error verifying signature: {e}")
        raise SignatureError(f"Error verifying signature: {e}") from e
        # return False


def verify_withdrawal_credentials(
    withdrawal_credentials: str, pool_id: BigInteger, block_identifier: BlockIdentifier
) -> bool:
    """
    Verifies if the withdrawal credentials match the expected value from the Portal.

    Args:
        withdrawal_credentials (str): The withdrawal credentials to verify.
        pool_id (str): The pool identifier.
        block_identifier (int): The block number to query.

    Returns:
        bool: True if credentials match, False otherwise.
    """
    expected = (
        "0x"
        + (
            get_sdk()
            .portal.functions.readBytes(pool_id, to_bytes32("withdrawalCredential"))
            .call(block_identifier=block_identifier)
        ).hex()
    )

    return withdrawal_credentials == expected


def verify_validator(
    validator: tuple[str, int, BigInteger, str, str, str, str, int],
    block_identifier: BlockIdentifier,
) -> int | None:
    """Verifies a validator proposal
        1. Validator has only one deposit
            Proven by stake_signature is None:
            Since a second deposit's signature is used to update stake_signature.
            And a third deposit would raise.
            Refer to update_beacon_constants for more explanation on this logic.
        2. Also verifies the withdrawal_credentials although it is provided by Portal
        3. proposal_signature is valid
        4. signature31 is valid
    Args:
        validator: tuple: validator data in the form of a tuple
            (pubkey, portal_index, pool_id, signature31, withdrawal_credentials,
            proposal_signature, stake_signature, proposal_slot)

    Returns:
        int: portal_index if its a faulty proposal, None if verified.
    """
    (
        pubkey,
        portal_index,
        pool_id,
        signature31,
        withdrawal_credentials,
        proposal_signature,
        stake_signature,
        _proposal_slot,
    ) = validator

    fork_version = GENESIS_FORK_VERSION[get_config(field=CHAIN_NAME_FIELD)]

    if stake_signature:
        return portal_index

    if not verify_withdrawal_credentials(withdrawal_credentials, pool_id, block_identifier):
        get_logger().critical(
            f"( {pubkey}) Invalid Withdrawal Credentials: {withdrawal_credentials}"
        )
        return portal_index

    if not verify_signature(
        proposal_signature.encode(),
        pubkey.encode(),
        withdrawal_credentials,
        fork_version,
        DEPOSIT_SIZE.PROPOSAL,
    ):
        get_logger().critical(f"( {pubkey}) Invalid Proposal Signature: {proposal_signature}")
        return portal_index

    if not verify_signature(
        signature31.encode(),
        pubkey.encode(),
        withdrawal_credentials,
        fork_version,
        DEPOSIT_SIZE.STAKE,
    ):
        get_logger().critical(f"( {pubkey}) Invalid Stake Signature: {signature31}")
        return portal_index

    return None


def verify_validators_batch(
    validators: list[tuple[str, int, BigInteger, str, str, str, str, int]],
    block_identifier: BlockIdentifier,
) -> list[str]:
    """_summary_

    Args:
        validators (list[tuple]):  list of validator data in the form of a tuple.
            - VALIDATORS_PUBKEY_FIELD (str)
            - VALIDATORS_PORTAL_INDEX_FIELD (int)
            - VALIDATORS_POOL_ID_FIELD (BigInteger)
            - VALIDATORS_SIGNATURE31_FIELD (str)
            - VALIDATORS_WITHDRAWAL_CREDENTIALS_FIELD (str)
            - VALIDATORS_PROPOSAL_SIGNATURE_FIELD (str)
            - VALIDATORS_STAKE_SIGNATURE_FIELD (str)
            - VALIDATORS_PROPOSAL_SLOT_FIELD (int)

    Returns:
        list[str]: validator_indices that needs to be alienated.
    """

    aliens = multithread(verify_validator, validators, repeat(block_identifier))

    # Note that filter also removes 0, '', etc. But, works fine here.
    return list(filter(None, aliens))


def fetch_latest_beacon_data(
    pubkey_iterator: Iterator[str], slot: int
) -> Iterator[tuple[int, int]]:
    """
    Fetches beacon data for a given iterator of pubkeys and slot.

    Args:
        pubkey_iterator (Iterator[str]): Iterator of validator pubkeys.
        slot (int): The slot number to fetch data for.

    Returns:
        Iterator[tuple[int, int]]: Iterator of tuples containing (beacon_balance, beacon_status).
    """

    vals = fetch_validators_batch(slot, pubkey_iterator)
    get_logger().debug(f"Fetched beacon data for {len(vals)} validators.")

    return ((int(val["balance"]), int(val["status"])) for val in vals)


def gather_validator_data_by_pool(
    pool_id: BigInteger, slot: int
) -> list[
    tuple[str, BigInteger, BigInteger, BigInteger, BigInteger, BigInteger, BigInteger, int, int]
]:
    """
    Gathers validator data by pool ID and slot.

    Args:
        pool_id (BigInteger): The pool identifier.
        slot (int): The slot number to fetch data for.

    Returns:
        list[tuple[str, BigInteger, BigInteger, BigInteger,
        BigInteger, BigInteger, BigInteger, str, str]]:
         List of merged validator data tuples:
         - pubkey (str)
         - pool_fee (BigInteger)
         - operator_fee (BigInteger)
         - infrastructure_fee (BigInteger)
         - withdrawn_balance (BigInteger)
         - last_withdrawn (BigInteger)
         - fee_recipient_balance (BigInteger)
         - beacon_balance (int)
         - beacon_status (int)
    """
    try:
        validators_db_data: list[
            tuple[str, BigInteger, BigInteger, BigInteger, BigInteger, BigInteger, BigInteger]
        ] = read_validators_by_pool(pool_id)

        pubkey_iterator: Iterator = (val[0] for val in validators_db_data)
        validators_beacon_data: Iterator[tuple[int, int]] = fetch_latest_beacon_data(
            pubkey_iterator, slot
        )

        merged_validator_data = [
            db_tuple + beacon_tuple
            for db_tuple, beacon_tuple in zip(validators_db_data, validators_beacon_data)
        ]

        return merged_validator_data
    except Exception as e:
        get_logger().error(f"Error gathering validator data by pool {pool_id}")
        raise e


def fill_validators_table(pks: list[bytes]) -> None:
    """
    Populates the Validators table with data for the given list of public keys (`pks`)

    Args:
        pks (list[bytes]): A list of public keys for which validator data will be populated.

    Raises:
        DatabaseError: If an error occurs during the insertion of validator records.
        ValueError: If the provided `pks` list is empty.
    """
    if not pks:
        get_logger().debug("Public keys list is empty for fill_validators_table. Nothing to do.")
        return

    insert_validators_batch(fetch_portal_validator_constants_batch(pks))
    get_logger().debug(f"Filled Validators table with {len(pks)} records.")


def update_portal_validators(first_block: int, last_block: int) -> None:
    """
    Updates the Validators table with validator pubkeys proposed between a specified block range.
    Then, populates the Validators table with the corresponding validator data.

    Args:
        first_block (int): The starting block number for fetching proposed validators.
        last_block (int): The ending block number for fetching proposed validators.

    Raises:
        ValueError: If `first_block` is greater than `last_block`.
        DatabaseError: If an error occurs during the update of validator records.
    """
    if first_block > last_block:
        raise ValueError("`first_block` must be less than or equal to `last_block`.")

    pks: list[bytes] = fetch_proposed_pubkeys(first_block, last_block)
    fill_validators_table(pks)
