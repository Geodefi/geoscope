"""
Helper functions for fetching and processing beaconchain slots.
"""

from typing import Any, cast

from src.common import BigInteger
from src.globals import get_logger, get_sdk
from src.globals.constants.database import (
    SLOTS_BLOCK_NUMBER_FIELD,
    SLOTS_BURNED_AMOUNT_FIELD,
    SLOTS_FEE_RECIPIENT_FIELD,
    SLOTS_PROPOSER_INDEX_FIELD,
    SLOTS_SLOT_FIELD,
)
from src.utils.thread import multithread


def fetch_slot(slot_number: str) -> dict[str, int | str | BigInteger | list[dict] | None]:
    """
    Fetches the data for the specified slot number.

    Args:
        slot_number (int|str|BigInteger|list[dict]): The slot number to fetch.

    Returns:
        dict[str, Any]: A dictionary containing the slot's information,
            Will return only the slot number if slot is missed by the proposer. Otherwise:
            - slot (int)
            - proposer_index (int)
            - block_number (int)
            - fee_recipient (str)
            - burned_amount (BigInteger)
            - deposits (list[dict])
            - withdrawals (list[dict])
    """

    try:
        slot: dict[Any, Any] = cast(dict[Any, Any], get_sdk().beacon.beacon_blocks(slot_number))
        slot_message: dict = slot["message"]
        execution_payload = slot_message["body"]["execution_payload"]
        return {
            SLOTS_SLOT_FIELD: int(slot_message["slot"]),
            SLOTS_BLOCK_NUMBER_FIELD: int(execution_payload["block_number"]),
            SLOTS_PROPOSER_INDEX_FIELD: int(slot_message["proposer_index"]),
            SLOTS_FEE_RECIPIENT_FIELD: str(execution_payload["fee_recipient"]),
            SLOTS_BURNED_AMOUNT_FIELD: BigInteger(
                int(execution_payload["base_fee_per_gas"]) * int(execution_payload["gas_used"])
            ),
            "deposits": slot_message["body"]["deposits"],
            "withdrawals": execution_payload["withdrawals"],
        }

    # pylint: disable-next=broad-exception-caught
    except Exception:
        get_logger().debug(f"Slot was missed by the proposer: {slot_number}")
        return {
            SLOTS_SLOT_FIELD: slot_number,
            SLOTS_BLOCK_NUMBER_FIELD: None,
            SLOTS_PROPOSER_INDEX_FIELD: None,
            SLOTS_FEE_RECIPIENT_FIELD: None,
            SLOTS_BURNED_AMOUNT_FIELD: None,
            "deposits": [],
            "withdrawals": [],
        }


def fetch_slots_batch(
    first_slot: int, last_slot: int
) -> list[dict[str, int | str | BigInteger | list[dict] | None]]:
    """Fetches the data for slots within the given range of first to last slots.

    Args:
        first_slot (int): first slot to fetch, inclusive
        last_slot (int): last slot to fetch, inclusive

    Returns:
        list[dict[str, int | str | BigInteger | list[dict] | None]]: Gathered slot info:
            - slot (int)
            - proposer_index (int)
            - block_number (int)
            - fee_recipient (str)
            - burned_amount (BigInteger)
            - deposits (list[dict])
            - withdrawals (list[dict])
    """
    if first_slot >= last_slot:
        get_logger().error(f"Invalid slot range: ({first_slot} >= {last_slot})")

    return multithread(fetch_slot, range(first_slot, last_slot + 1))
