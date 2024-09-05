# -*- coding: utf-8 -*-
# pylint: disable=invalid-name


from typing import Iterable
from web3.types import EventData
from web3.contract.contract import ContractEvent

from src.globals import get_logger, get_sdk
from src.helpers.events import get_all_events


def get_StakeParams() -> list:
    """Returns the result of portal.StakeParams function.

    Returns:
        list: list of StakeParams
    """
    get_logger().debug("Calling StakeParams() from portal")
    return get_sdk().portal.functions.StakeParams().call()


def fetch_proposed_pubkeys(first_block, last_block) -> list[str]:
    """Fetches the list of proposed pubkeys by checking the event
        named StakeProposal from Portal, between given block range.

    Args:
        first_block (int): first block to fetch proposed pubkeys
        last_block (int): last block to fetch proposed pubkeys

    Returns:
        list[str]: Gathered Pubkeys
    """
    # First we need to fetch all the ProposeValidator Events
    proposal_event: ContractEvent = get_sdk().portal.contract.events.StakeProposal()

    detected_events: Iterable[EventData] = get_all_events(
        event=proposal_event,
        first_block=first_block,
        last_block=last_block,
    )

    flattened_pks = [pubkey for event in detected_events for pubkey in event.args.pubkeys]

    return flattened_pks
