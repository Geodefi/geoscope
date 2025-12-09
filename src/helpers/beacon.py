from itertools import repeat
from typing import Iterator

from src.exceptions import SDKError
from src.globals import get_logger, get_sdk
from src.utils.thread import multithread


def fetch_validators_batch(slot: int, validators: Iterator[int | str]) -> list[dict]:
    """
    Fetch batch information for validators from the Beacon Chain for a given slot.

    Retrieves detailed validator information concurrently by leveraging
    multithreading. It uses the provided slot number and an iterator of validator indices
    or public keys to fetch their respective states from the Beacon Chain.

    Args:
        slot (int): The slot number to fetch validator data from.
        validators (Iterator[int | str]): An iterator of validator indices(int) or public keys(str).

    Returns:
        list[dict]: A list of dictionaries containing beacon state information for each validator.

    Raises:
        SDKError: If an error occurs while fetching validator data from the SDK.
    """
    logger = get_logger()
    validators_list = list(validators)  # Convert iterator to list to log the count
    logger.debug(f"Fetching {len(validators_list)} validators from slot {slot}.")
    try:
        return multithread(
            get_sdk().beacon.beacon_states_validators_id, repeat(slot), validators_list
        )
    except Exception as e:
        logger.error(f"Failed to fetch validators batch for slot {slot}: {e}")
        raise SDKError(f"Error fetching validators batch: {e}") from e
