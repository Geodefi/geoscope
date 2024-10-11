# -*- coding: utf-8 -*-

from src.globals import get_sdk, get_logger
from src.utils.thread import multithread


def fetch_slot(slot_number: int) -> dict:
    """Fetches the data for the slot with the given block_id . Returns the gathered data.

    Args:
        pubkey (str): public key of the validator

    Returns:
        dict: dictionary containing the slots info
    """

    try:
        slot: dict = get_sdk().beacon.beacon_blocks(slot_number)
        slot_message: dict = slot["message"]
        execution_payload = slot["message"]["body"]["execution_payload"]
        return {
            "slot": slot_message["slot"],
            "proposer_index": slot_message["proposer_index"],
            "block_number": execution_payload["block_number"],
            "fee_recipient": execution_payload["fee_recipient"],
            "burned_amount": int(execution_payload["base_fee_per_gas"])
            * int(execution_payload["gas_used"]),
            "deposits": slot_message["body"]["deposits"],
            "withdrawals": execution_payload["withdrawals"],
        }

    except Exception:
        get_logger().debug(f"Slot was missed by the proposer: {slot_number}")
        return {
            "slot": slot_number,
            "proposer_index": None,
            "block_number": None,
            "fee_recipient": None,
            "burned_amount": None,
            "deposits": [],
            "withdrawals": [],
        }


def fetch_slots_batch(first_slot: int, last_slot: int) -> list[dict]:
    """Fetches the data for slots within the given range of first to last slots.

    Args:
        first_slot (int): first slot to fetch
        last_slot (int): last slot to fetch

    Returns:
        list[dict]: Gathered slot info
    """

    return multithread(fetch_slot, range(first_slot, last_slot))
