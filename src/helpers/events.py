# -*- coding: utf-8 -*-

from typing import Iterable
from itertools import repeat
from web3.types import EventData
from web3.contract.contract import ContractEvent

from geodefi.utils import multiple_attempt

from src.globals import get_logger, get_constants
from src.utils.thread import multithread


@multiple_attempt
def get_batch_events(event: ContractEvent, from_block: int, limit: int) -> Iterable[EventData]:
    """Get events within a range of blocks.

    Args:
        event (ContractEvent): event to be checked.
        from_block (int): starting block number.
        limit (int): last block number to be checked.

    Returns:
        Iterable[EventData]: list of events.
    """
    # if range is like [0,7,3] -> 0, 3, 6
    # get_batch_events would search 0-3, 3-6 and 6-9
    # but we want 0-3, 3-6, 6-7
    max_block_range = int(get_constants().chain.range)
    to_block = min(from_block + max_block_range, limit)

    # @dev do not use filters instead, some providers do not support it.
    logs = event.get_logs(fromBlock=from_block, toBlock=to_block)
    if logs:
        get_logger().info(
            f"Detected {event.event_name:^20} logs between {from_block}-{to_block} => {len(logs)}"
        )
    return logs


def get_all_events(event: ContractEvent, first_block: int, last_block: int) -> Iterable[EventData]:
    """Get all events emitted within given range of blocks. It uses get_batch_events
    to get events in batches within multhithread and then combines them.

    Args:
        event (ContractEvent): event to be checked.
        first_block (int): starting block number.
        last_block (int): last block number to be checked.

    Returns:
        Iterable[EventData]: list of events.
    """
    max_block_range = int(get_constants().chain.range)
    r: range = range(first_block, last_block, max_block_range)
    if first_block == last_block:
        r: range = range(first_block, first_block + 1)

    log_batches: Iterable[EventData] = multithread(
        get_batch_events, repeat(event), r, repeat(last_block)
    )

    # converts list of list into a list
    # NOTE if log_batches[batch] is Iterable then unpack batch[log], else continue
    logs: Iterable[EventData] = [log for batch in log_batches if batch for log in batch]

    # NOTE that the events should be sorted as: blockNumber->transactionIndex->logIndex
    # which persists here, so no need to sort again.
    return logs
