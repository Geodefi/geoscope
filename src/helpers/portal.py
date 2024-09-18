# -*- coding: utf-8 -*-
# pylint: disable=invalid-name


from typing import Iterable
from web3.types import EventData
from web3.contract.contract import ContractEvent

from src.utils.thread import multithread
from src.globals import get_logger, get_sdk
from src.helpers.events import get_all_events


def get_StakeParams() -> list:
    """Returns the result of portal.StakeParams function.

    Returns:
        list: list of StakeParams
    """
    get_logger().debug("Calling StakeParams() from portal")
    return get_sdk().portal.functions.StakeParams().call()


def get_proposed_pubkeys(first_block, last_block) -> list[str]:
    """Get the list of proposed pubkeys by checking the event
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


def get_validator(pubkey: str) -> dict:
    """Returns the data for a validator with the given pubkey.
    Only processes the Portal information, leaves the Beacon chain related ones for later.
    Since the deposits might not be processed at the moment.
    Note that the Portal data gathered here, never changes,
    so it is safe to assume the latest is up to date.

    Args:
        pubkey (str): public key of the validator

    Returns:
        dict: dictionary containing the gathered validator info
    """
    # TODO: delete this.
    # Although all of the required data for the validators should be available,
    # the following ones might not yet since the deposit can be still not yet processed.
    # So, instead of not processing them, we will create the indexes
    # but fill them later when deposits are being processed.

    val = get_sdk().portal.validator(pubkey)
    return {
        "pubkey": pubkey,
        "portal_index": val.portal_index,
        "portal_state": val.portal_state,
        "pool_id": val.poolId,
        "operator_id": val.operatorId,
        "pool_fee": val.poolFee,
        "operator_fee": val.operatorFee,
        "infrastructure_fee": val.infrastructureFee,
        "signature31": val.signature31,
        "beacon_index": None,
        "beacon_status": None,
        "withdrawal_credentials": None,
        "exit_epoch": None,
        "beacon_balance": 0,
        "withdrawn_balance": 0,
        "fee_recipient_balance": 0,
    }


def get_validators_batch(pks: list[str]) -> list[dict]:
    """Fetches the data for validators within the given pks list. Returns the gathered data.

    Args:
        pks (list[str]): pubkeys that will be fetched

    Returns:
        list[dict]: list of dictionaries containing the validator info
    """

    return multithread(get_validator, pks)
