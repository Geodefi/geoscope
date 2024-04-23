from eth_abi import abi
from itertools import repeat

from geode.utils.wrappers import multipleAttempt

from .multithread import multithread
from ..globals.constants import EVENT_STEP
from ..globals.sdk import SDK


def get_batch_events(address: str, signature: str, fromBlock: int, limit: int) -> dict:
    """
    returns the conntract events for the given address within the range of fromBlock to limit

    """
    # if range is like [0,7,3] -> 0, 3, 6
    # get_batch_events would search 0-3, 3-6 and 6-9
    # but we want 0-3, 3-6, 6-7
    toBlock: int = fromBlock + EVENT_STEP
    if toBlock > limit:
        toBlock = limit

    filterer: dict = {
        "fromBlock": fromBlock,
        "toBlock": toBlock,
        "address": address,
        "topics": [signature],
    }

    filter = SDK.w3.eth.filter(filterer)
    return multipleAttempt(filter.get_all_entries)()


def get_all_events(
    address: str, signature: str, first_block: int, last_block: int
) -> list[dict]:
    """
    returns all events within the range of first_block to last_block
    while making use of multithreads
    """

    r = range(first_block, last_block, EVENT_STEP)

    if first_block == last_block:
        r = range(first_block, first_block + 1)

    logs = multithread(
        get_batch_events, repeat(address), repeat(signature), r, repeat(last_block)
    )

    return logs


def decode_abi(types: list, data) -> tuple:
    """
    decode given data with list of solidity types
    """
    try:
        decoded: tuple = abi.decode(types, bytes.fromhex(str(data.hex())[2:]))
        return decoded
    except:
        raise
