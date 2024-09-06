# -*- coding: utf-8 -*-
from functools import reduce

from src.utils.thread import multithread
from src.utils.list import flatten
from src.database.validators import check_beacon_index, increase_withdrawn_balances
from src.database.withdrawals import check_withdrawal_by_slot


def filter_withdrawals(slot: int, withdrawals: list[dict]) -> list:
    """Filters withdrawals within a single slot:
        - pubkeys that are created by Portal
        - events that does not exist on the database
    There are consistently 16 withdrawals per block, except the missed slots.

    Args:
        slot (int): points to a slot that the withdrawals list is gathered from
        withdrawals (dict): withdrawals list to be filtered

    Returns:
        list: filtered list of withdrawals for given slot
    """
    filtered = []
    # filter slots that have no withdrawals
    if withdrawals:
        # filter slots that have been saved to db, assumed to be processed
        if check_withdrawal_by_slot(slot):
            for w in withdrawals:
                # check if pk is available on Portal
                if check_beacon_index(w["validator_index"]):
                    w["slot"] = slot
                    filtered.append(w)

    return filtered


def filter_withdrawals_batch(slots: list[dict]) -> list[dict]:
    """Checks if the given pubkey for the withdrawal exists in the Validators database,
        for multiple slots worth of withdrawal data
    Meaning it is created through Portal.

    Args:
        slots (list[dict]): gathered info about the slots.

    Returns:
        list[dict]: filtered withdrawals that belong to geodefi validators.
    """
    # turn into a dict that maps slots to withdrawal_data
    withdrawals_by_slots: dict = {s["slot"]: s["withdrawals"] for s in slots}

    filtered_withdrawals = multithread(
        filter_withdrawals, withdrawals_by_slots.keys(), withdrawals_by_slots.values()
    )

    return flatten(filtered_withdrawals)


def process_many_withdrawals(withdrawals: list[dict]):
    """Processes the withdrawal amounts for encontered pubkeys.
    Updates the update the Validators db for:
        - withdrawn_balance

    Args:
        withdrawals (list[dict]): list of withdrawals to process
    """
    # reduces the withdrawals by grouping them by validator_index
    # accumulates the amounts for the index
    # results in dict of {'validator_index': amount,...}
    # which is the expected form for the increase_withdrawn_balances

    indexed_sums: dict = reduce(
        lambda accumulator, withdrawal: (
            accumulator.update(
                {
                    withdrawal["validator_index"]: accumulator.get(withdrawal["validator_index"], 0)
                    + int(withdrawal["amount"])
                }
            )
            or accumulator
        ),
        withdrawals,
        {},
    )
    increase_withdrawn_balances(indexed_sums)
