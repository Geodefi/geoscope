# -*- coding: utf-8 -*-
from py_ecc.bls import G2ProofOfPossession as bls
from itertools import repeat

from geodefi.globals import DEPOSIT_SIZE, GENESIS_FORK_VERSION
from geodefi.utils import to_bytes32

from src.utils.thread import multithread
from src.globals import get_constants, get_config, get_sdk

from src.utils.bls import DepositMessage, compute_deposit_domain, compute_signing_root


def should_verify_validators(slot: int, validators: list[tuple]) -> bool:
    """Checks if it is yet the correct time to verify:
    1.  ANY validator have been waiting for > MAX_VERIFICATION_DELAY
    OR
    2.  has been > MAX_PENDING_PROPOSALS validator proposals
        AND
        has been > MIN_VERIFICATION_DELAY since the last proposal
    """
    config = get_config()
    chain_interval = int(get_constants().chain.interval)

    min_slot = min(validators, key=lambda x: x[7])  # 7 corresponds to proposal_slot
    min_slot_delay = (slot - min_slot) * chain_interval
    max_verification_delay = int(config.strategy.max_verification_delay)
    if min_slot_delay > max_verification_delay:
        return True

    max_proposals = int(config.strategy.max_pending_validators)
    if len(validators) > max_proposals:
        max_slot = max(validators, key=lambda x: x[7])  # 7 corresponds to proposal_slot
        max_slot_delay = (slot - max_slot) * chain_interval
        min_verification_delay = int(config.strategy.min_verification_delay)
        if max_slot_delay > min_verification_delay:
            return True

    return False


def validate_signature(signature, pubkey, withdrawal_credentials, fork_version, amount) -> bool:
    # Verify deposit signature && pubkey
    deposit_message = DepositMessage(pubkey, withdrawal_credentials, amount)
    domain = compute_deposit_domain(fork_version)
    signing_root = compute_signing_root(deposit_message, domain)

    if bls.Verify(pubkey, signing_root, signature):
        return True
    else:
        return False


def validate_withdrawal_credentials(
    withdrawal_credentials: str, pool_id: str, block_identifier: int
) -> bool:
    expected = (
        "0x"
        + (
            get_sdk()
            .portal.functions.readBytes(pool_id, to_bytes32("withdrawalCredential"))
            .call(block_identifier=block_identifier)
        ).hex()
    )
    return withdrawal_credentials == expected


def verify_validator(validator: tuple, block_identifier: int) -> int:
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
        validator: tuple: validator data in the form of a tuple.
            (pubkey, portal_index, pool_id, signature31, withdrawal_credentials, proposal_signature, stake_signature, proposal_slot)

    Returns:
        int: portal_index if its a faulty proposal, None if verified.
    """
    pubkey = validator[0]
    portal_index = validator[1]
    pool_id = validator[2]
    signature31 = validator[3]
    withdrawal_credentials = validator[4]
    proposal_signature = validator[5]
    stake_signature = validator[6]
    # proposal_slot = validator[7]
    fork_version = GENESIS_FORK_VERSION[get_config().chain_name]

    if stake_signature is None:
        if validate_withdrawal_credentials(withdrawal_credentials, pool_id, block_identifier):
            if validate_signature(
                proposal_signature,
                pubkey,
                withdrawal_credentials,
                fork_version,
                DEPOSIT_SIZE.PROPOSAL,
            ):
                if validate_signature(
                    signature31,
                    pubkey,
                    withdrawal_credentials,
                    fork_version,
                    DEPOSIT_SIZE.STAKE,
                ):
                    return None
    return portal_index


def verify_validators_batch(validators: list[tuple], block_identifier: int) -> list[str]:
    """_summary_

    Args:
        validators (list[tuple]):  list of validator data in the form of a tuple.
            (pubkey, portal_index, pool_id, signature31, withdrawal_credentials, proposal_signature, stake_signature, proposal_slot)

    Returns:
        list[str]: validator_indices that needs to be alienated.
    """

    aliens = multithread(verify_validator, validators, repeat(block_identifier))

    # Note that filter also removes 0, '', etc. But, works fine here.
    return filter(None, aliens)
