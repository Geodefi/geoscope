"""
Helper functions filtering and processing beaconchain deposits.
"""

from itertools import repeat
from typing import Any

from src.common import BigInteger
from src.database.deposits import check_deposit_by_slot
from src.database.validators import check_validator_by_pubkey, update_beacon_constants
from src.globals import get_logger, get_sdk
from src.globals.constants.database import (
    DEPOSITS_AMOUNT_FIELD,
    DEPOSITS_PUBKEY_FIELD,
    DEPOSITS_SIGNATURE_FIELD,
    DEPOSITS_SLOT_FIELD,
    DEPOSITS_WITHDRAWAL_CREDENTIALS_FIELD,
    SLOTS_SLOT_FIELD,
    VALIDATORS_BEACON_INDEX_FIELD,
    VALIDATORS_EXIT_EPOCH_FIELD,
    VALIDATORS_PROPOSAL_SIGNATURE_FIELD,
    VALIDATORS_PROPOSAL_SLOT_FIELD,
    VALIDATORS_PUBKEY_FIELD,
    VALIDATORS_STAKE_SIGNATURE_FIELD,
    VALIDATORS_WITHDRAWAL_CREDENTIALS_FIELD,
)
from src.utils.list import flatten
from src.utils.thread import multithread


def filter_deposits(slot: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Filters deposits within a single slot:
        - Keeps deposits associated with pubkeys that are created by Portal
        - Excludes deposits that already exist in the database.

    Deposits are randomly processed, no presumprion is possible.

    Args:
        slot dict[str, Any]: Slot dictionary that contains:
            deposits (list[dict[str, Any]]): List of deposit dictionaries to be filtered.

    Returns:
        list: filtered list of deposits for given slot
    """
    # filter slots that have no deposits
    if not slot["deposits"]:
        return []

    # filter slots that have been saved to db, assumed to be processed
    if check_deposit_by_slot(
        slot[SLOTS_SLOT_FIELD]
    ):  # True if at least one deposit exists for the slot
        return []

    filtered = []
    for d in slot["deposits"]:
        # check if pk is available on Portal
        d_data: dict = {}
        if check_validator_by_pubkey(d["data"]["pubkey"]):
            d_data[DEPOSITS_PUBKEY_FIELD] = d["data"]["pubkey"]
            d_data[DEPOSITS_SIGNATURE_FIELD] = d["data"]["signature"]
            d_data[DEPOSITS_AMOUNT_FIELD] = BigInteger(d["data"]["amount"])
            d_data[DEPOSITS_WITHDRAWAL_CREDENTIALS_FIELD] = d["data"]["withdrawal_credentials"]
            d_data[DEPOSITS_SLOT_FIELD] = slot[SLOTS_SLOT_FIELD]
            filtered.append(d_data)
    return filtered


def filter_deposits_batch(
    slots: list[dict[str, int | str | BigInteger | list[dict] | None]]
) -> list[dict[str, str | BigInteger | int]]:
    """
    Checks if the given pubkey for the deposit exists in the Validators database,
    for multiple slots of deposit data.
    Meaning it is created through Portal.

    Does not matter if the deposit is valid or not, it will show up.

    Args:
        slots (list[dict[str, int | str | BigInteger | list[dict] | None]]): Gathered slot info:
            - slot (int)
            - proposer_index (int)
            - block_number (int)
            - fee_recipient (str)
            - burned_amount (BigInteger)
            - deposits (list[dict])
            - withdrawals (list[dict])

    Returns:
        list[dict[str, Any]]: Filtered deposits belonging to geodefi validators.
            Each dictionary contains:
                - DEPOSITS_PUBKEY_FIELD: (str)
                - DEPOSITS_SIGNATURE_FIELD: (str)
                - DEPOSITS_AMOUNT_FIELD: (BigInteger)
                - DEPOSITS_WITHDRAWAL_CREDENTIALS_FIELD: (str)
                - DEPOSITS_SLOT_FIELD: (int)

    """
    # filter slots that have no deposits, turn into a dict that maps slots to deposit_data
    get_logger().debug(f"Processing {len(slots)} slots for deposits")
    filtered_deposits = flatten(multithread(filter_deposits, slots))
    get_logger().debug(f"Encountered {len(filtered_deposits)} deposits.")

    return filtered_deposits


def __parse_validator_data(
    deposit: dict[str, str | BigInteger | int], slot_number: int
) -> dict[str, str | int]:
    """
    Parses and validates deposit and validator data.
    Note that it is not necessary or effective to distinguish
    VALIDATORS_PROPOSAL_SIGNATURE_FIELD and VALIDATORS_STAKE_SIGNATURE_FIELD
    here, we will return both and decide what the signature stands for later.

    Args:
        deposit (dict[str, Any]): Deposit data containing pubkey and signature.
        slot_number (int): Slot height to call the data from.

    Returns:
        dict[str, str|int]: Parsed validator data:
            - VALIDATORS_PUBKEY_FIELD (str):
            - VALIDATORS_PROPOSAL_SLOT_FIELD (int):
            - VALIDATORS_BEACON_INDEX_FIELD (int):
            - VALIDATORS_WITHDRAWAL_CREDENTIALS_FIELD (str):
            - VALIDATORS_EXIT_EPOCH_FIELD (int):
            - VALIDATORS_PROPOSAL_SIGNATURE_FIELD (str):
            - VALIDATORS_STAKE_SIGNATURE_FIELD (str):
    """
    pk: str = str(deposit[DEPOSITS_PUBKEY_FIELD])
    validator: dict = get_sdk().beacon.beacon_states_validators_id(slot_number, pk)  # type:ignore
    return {
        VALIDATORS_PUBKEY_FIELD: pk,
        VALIDATORS_PROPOSAL_SLOT_FIELD: slot_number,
        VALIDATORS_BEACON_INDEX_FIELD: validator["index"],
        VALIDATORS_WITHDRAWAL_CREDENTIALS_FIELD: validator["validator"]["withdrawal_credentials"],
        VALIDATORS_EXIT_EPOCH_FIELD: validator["validator"]["exit_epoch"],
        VALIDATORS_PROPOSAL_SIGNATURE_FIELD: deposit["signature"],
        VALIDATORS_STAKE_SIGNATURE_FIELD: deposit["signature"],
    }


def process_deposits_batch(
    slot_number: int, deposits: list[dict[str, str | BigInteger | int]]
) -> None:
    """
    Updates the Validators db for encountered pubkeys.
    When a deposit is encountered, it is ensured that the pubkey is reachable on the beaconchain.

    Args:
        slot_number (int): The slot number to process deposits from.
        deposits (list[dict[str, Any]]): List of deposits to process.
    """
    # Prepare the validators data for database:
    parsed_validators: list[dict[str, str | int]] = multithread(
        __parse_validator_data, deposits, repeat(slot_number)
    )

    # Now that we have validators data, update the db:
    update_beacon_constants(parsed_validators)
