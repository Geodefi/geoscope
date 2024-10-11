# -*- coding: utf-8 -*-
from src.exceptions.helpers.deposits import ValidatorMismatchError
from src.utils.thread import multithread
from src.utils.list import flatten
from src.database.validators import check_pubkey, update_beacon_constants
from src.database.deposits import check_deposit_by_slot
from src.helpers.beacon import fetch_validators_batch


def filter_deposits(slot: int, deposits: list[dict]) -> list:
    """Filters deposits within a single slot:
        - pubkeys that are created by Portal
        - events that does not exist on the database
    Deposits are randomly processed.

    Args:
        slot (int): points to a slot that the deposits list is gathered from
        deposits (dict): deposits list to be filtered

    Returns:
        list: filtered list of deposits for given slot
    """
    filtered = []
    # filter slots that have no deposits
    if deposits:
        # filter slots that have been saved to db, assumed to be processed
        if not check_deposit_by_slot(slot):
            for d in deposits:
                # check if pk is available on Portal
                if check_pubkey(d["pubkey"]):
                    d["slot"] = slot
                    filtered.append(d)

    return filtered


def filter_deposits_batch(slots: list[dict]) -> list[dict]:
    """Checks if the given pubkey for the deposit exists in the Validators database,
        for multiple slots worth of deposit data
    Meaning it is created through Portal.
    Does not matter if the deposit is valid or not, it will show up.

    Args:
        slots (list[dict]): gathered info about the slots.

    Returns:
        list[dict]: filtered deposits that belong to geodefi validators.
    """
    # filter slots that have no deposits, turn into a dict that maps slots to deposit_data

    deposits_by_slots: dict = {s["slot"]: [d["data"] for d in s["deposits"]] for s in slots}

    filtered_deposits = multithread(
        filter_deposits, deposits_by_slots.keys(), deposits_by_slots.values()
    )

    return flatten(filtered_deposits)


def __parse_validator_data(deposit, validator) -> list[dict]:
    pk: str = deposit["pubkey"]

    if pk != validator["validator"]["pubkey"]:
        raise ValidatorMismatchError(f"{deposit['pk']} returned a pubkey ")

    return {
        "pubkey": deposit["pubkey"],
        "signature": deposit["signature"],
        "slot": deposit["slot"],
        "beacon_index": validator["index"],
        "withdrawal_credentials": validator["validator"]["withdrawal_credentials"],
        "exit_epoch": validator["validator"]["exit_epoch"],
    }


def process_many_deposits(slot: int, deposits: list[dict]) -> None:
    """When a deposit is encountered, we ensured that the pubkey is reachable on the beaconchain.
        So, we will update the Validators db.

    Args:
        slot (int): slot to process deposits from
        deposits (list[dict]): list of deposits to process
    """
    # fetch_validators_batch respects the indices.
    # TODO: fix this call
    validators: list[dict] = fetch_validators_batch(slot, deposits)

    # Prepare the validators data database:
    parsed_validators: list[dict] = multithread(__parse_validator_data, deposits, validators)

    # Now that we have validators data, update the db:
    update_beacon_constants(parsed_validators)
