# -*- coding: utf-8 -*-

from itertools import repeat
from src.globals import get_sdk
from src.utils.thread import multithread


# @http_request
# def fetch_validators_batch(slot: int, validators: list) -> tuple:
#     # This method improves sdk.beacon.beacon_states_validators, thus beacon_states_validators should be improved in the next version of sdk.
#     # There is a http 429 or 502 error that happens frequently when given slot is too old...
#     # And tbh it is not safe to assume latest/finalized (newer) slots will be processed here (especially with the batches)
#     # This is because, we might be processing an unkown deposit twice!
#     # ! This method is unreliable anyways: validators/? endpoint does not respect the ordering, which we care in this case.
#     url = get_sdk().beacon.api_base + f"/eth/v1/beacon/states/{slot}/validators/?"
#     for v in validators:
#         url += f"id={v}&"
#     return (url, True)


def fetch_validators_batch(slot: int, validators: list) -> list[dict]:
    """Fetch batch info for the validators from beacon chain for a given slot.

    Args:
        slot (int): slot to fetch the validator data from
        validators (list): list of validator indices or pubkeys

    Returns: list of beacon state validators
    """
    return multithread(get_sdk().beacon.beacon_states_validators_id, repeat(slot), validators)
