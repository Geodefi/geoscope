"""
Functions for filtering and processing beacon chain withdrawals.
"""

from functools import reduce
from typing import Any

from src.common import BigInteger
from src.database.validators import check_validator_by_beacon_index, increase_withdrawn_balances
from src.database.withdrawals import check_withdrawal_by_slot
from src.globals import get_logger
from src.globals.constants.database import (
    SLOTS_SLOT_FIELD,
    WITHDRAWALS_ADDRESS_FIELD,
    WITHDRAWALS_AMOUNT_FIELD,
    WITHDRAWALS_SLOT_FIELD,
    WITHDRAWALS_VALIDATOR_INDEX_FIELD,
)
from src.utils.list import flatten
from src.utils.thread import multithread


def filter_withdrawals(slot: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Filter withdrawals within a single slot.
        - Keeps withdrawals from pubkeys that are created by Portal
        - Excludes withdrawals that already exist in the database.

    There are consistently 16 withdrawals per block, except the missed slots.

    Args:
        slot dict[str, Any]: Slot dictionary that contains:
            slot (int): The slot number from which withdrawals are gathered.
            withdrawals (list[dict[str, Any]]): List of withdrawal dictionaries to be filtered.

    Returns:
        list[dict[str, Any]]: Filtered list of withdrawals for the given slot.
            Each dictionary contains:
                - slot: (str)
                - index: (str)
                - validator_index: (str)
                - address: (str)
                - amount: (str)
    """
    # filter slots that have no withdrawals
    if not slot["withdrawals"]:
        return []

    # filter slots that have been saved to db, assumed to be processed
    if check_withdrawal_by_slot(slot[SLOTS_SLOT_FIELD]):
        return []

    filtered = []
    for w in slot["withdrawals"]:
        w_data: dict = {}
        # check if pk is available on Portal
        if check_validator_by_beacon_index(w["validator_index"]):
            w_data[WITHDRAWALS_VALIDATOR_INDEX_FIELD] = int(w["validator_index"])
            w_data[WITHDRAWALS_ADDRESS_FIELD] = w["address"]
            w_data[WITHDRAWALS_AMOUNT_FIELD] = BigInteger(w["amount"])
            w_data[WITHDRAWALS_SLOT_FIELD] = slot[SLOTS_SLOT_FIELD]
            filtered.append(w_data)
    return filtered


def filter_withdrawals_batch(
    slots: list[dict[str, Any]]
) -> list[dict[str, int | str | BigInteger]]:
    """
    Filter withdrawals for multiple slots.
    Checks if the pubkey for each withdrawal exists in the Validators database,
    indicating it was created through Portal.

    Args:
        slots (list[dict[str, Any]]): gathered info about the slots.

    Returns:
        list[dict[str, Any]]: Filtered withdrawals belonging to geodefi validators.
            Each dictionary contains:
                - WITHDRAWALS_VALIDATOR_INDEX_FIELD: (int)
                - WITHDRAWALS_ADDRESS_FIELD: (str)
                - WITHDRAWALS_AMOUNT_FIELD: (BigInteger)
                - WITHDRAWALS_SLOT_FIELD: (int)
    """
    get_logger().debug(f"Processing {len(slots)} slots for withdrawals")
    filtered_withdrawals = flatten(multithread(filter_withdrawals, slots))
    get_logger().debug(f"Encountered {len(filtered_withdrawals)} withdrawals.")

    return filtered_withdrawals


def process_withdrawals_batch(withdrawals: list[dict]) -> None:
    """Processes the withdrawal amounts for encountered pubkeys.
    Updates the update the Validators db for:
        - withdrawn_balance

    Args:
        withdrawals (list[dict]): list of withdrawals to process
    """
    # reduces the withdrawals by grouping them by validator_index
    # accumulates the amounts for the index
    # results in dict of {'validator_index': amount,...}
    # which is the expected form for the increase_withdrawn_balances
    get_logger().info(f"Processing {len(withdrawals)} withdrawals")

    indexed_sums: dict = reduce(
        lambda accumulator, withdrawal: (
            accumulator.update(
                {
                    withdrawal[WITHDRAWALS_VALIDATOR_INDEX_FIELD]: accumulator.get(
                        withdrawal[WITHDRAWALS_VALIDATOR_INDEX_FIELD], 0
                    )
                    + int(withdrawal[WITHDRAWALS_AMOUNT_FIELD])
                }
            )
            or accumulator
        ),
        withdrawals,
        {},
    )

    # TODO:(later) this might be faster as {'validator_index':validator_index, 'amount':amount}
    increase_withdrawn_balances(indexed_sums)
