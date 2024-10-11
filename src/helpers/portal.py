# -*- coding: utf-8 -*-
# pylint: disable=invalid-name


from itertools import repeat
from typing import Iterable
from geodefi import Geode
from geodefi.globals import ID_TYPE
from geodefi.utils import get_contract_abi, to_bytes32
from geodefi.globals import Network

from web3 import Web3
from web3.types import EventData
from web3.contract import Contract
from web3.contract.contract import ContractEvent

from src.utils.thread import multithread
from src.globals import get_logger, get_sdk
from src.helpers.events import get_all_events
from src.database.pools import (
    pool_count,
    insert_many_pools_info,
    get_all_pool_ids,
    update_many_pools_data,
)
from src.database.pools import fetch_withdrawal_contract_address

# TODO: feels like sdk w3 is displaced? There should be a global web3 instance, we should not be moving it around and giving it to self.


def get_StakeParams(block_identifier: str) -> list:
    """Returns the result of portal.StakeParams function.

    Returns:
        list: list of StakeParams
    """
    get_logger().debug("Calling StakeParams() from portal")
    return get_sdk().portal.functions.StakeParams().call(block_identifier=block_identifier)


def get_verification_index(block_identifier: str) -> int:
    """Verification Index points to the last validator that has been approved by the oracle already.

    Args:
        block_identifier (int): block height to call the data from.\
            Can be head, latest, finalized etc as well.

    Returns:
        int: VERIFICATION_INDEX from portal.StakeParams
    """
    return get_StakeParams(block_identifier)[3]


def get_oracle_update_timestamp(block_identifier: str) -> int:
    """Returns the timestamp of the last oracle update.

    Args:
        block_identifier (int): block height to call the data from.\
            Can be head, latest, finalized etc as well.

    Returns:
        int: ORACLE_UPDATE_TIMESTAMP from portal.StakeParams
    """
    return get_StakeParams(block_identifier)[8]


def get_oracle_address(block_identifier: str = "finalized") -> str:
    """Returns the address of the oracle.

    Args:
        block_identifier (int): block height to call the data from.\
            Can be head, latest, finalized etc as well.

    Returns:
        str: ORACLE_ADDRESS from portal.StakeParams
    """
    return get_StakeParams(block_identifier)[1]


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


def get_validator_proper(pubkey: str) -> dict:
    """Returns the portal data for a validator with the given pubkey.
    Only processes the Portal information, leaves the Beacon chain related ones for later.
    Since the deposits might not be processed at the moment.
    Note that the Portal data gathered here, never changes,
    so it is safe to assume the latest is up to date.

    Args:
        pubkey (str): public key of the validator

    Returns:
        dict: dictionary containing the gathered validator info \
            with the keys appropriated according to the database structure.
    """
    # Although all of the required data for the validators should be available,
    # the following ones might not yet since the deposit can be still not yet processed.
    # So, instead of not processing them, we will create the indexes
    # but fill them later when deposits are being processed.
    val = get_sdk().portal.validator(pubkey)
    return {
        "pubkey": pubkey,
        "portal_index": val.portal_index,
        "pool_id": val.poolId,
        "operator_id": val.operatorId,
        "pool_fee": val.poolFee,
        "operator_fee": val.operatorFee,
        "infrastructure_fee": val.infrastructureFee,
        "signature31": val.signature31,
        "beacon_index": None,
        "withdrawal_credentials": None,
        "exit_epoch": None,
        "proposal_signature": None,
        "stake_signature": None,
        "proposal_slot": None,
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

    return multithread(get_validator_proper, pks)


def get_pool_info(pool_index: int, block_number: int) -> dict:
    """Returns the data for a pool with the given id.

    Args:
        pool_id (int): id of the pool

    Returns:
        dict: dictionary containing the gathered pool info
    """
    sdk: Geode = get_sdk()
    pool_id: int = sdk.portal.functions.allIdsByType(ID_TYPE.POOL, pool_index).call(
        block_identifier=block_number
    )

    # no need to check for block_number, since these data never change.
    pool = sdk.portal.pool(pool_id)

    return {
        "id": str(pool_id),
        "name": pool.NAME,
        "withdrawal_contract_address": pool.withdrawalContract,
        "withdrawal_credentials": pool.withdrawalCredential,
    }


def update_pool_ids(block_number: int) -> None:
    """Updates the pool ids with the given block number.

    Args:
        block_number (int): block number to update the pool ids
    """
    number_of_pools: int = pool_count()
    portal_pool_count: int = (
        get_sdk()
        .portal.functions.allIdsByTypeLength(ID_TYPE.POOL)
        .call(block_identifier=block_number)
    )

    if portal_pool_count > number_of_pools:
        get_logger().info(f"Updating pool ids from {number_of_pools} to {portal_pool_count}")
        pools: list[dict] = multithread(
            get_pool_info, range(number_of_pools, portal_pool_count), repeat(block_number)
        )
        insert_many_pools_info(pools)


# TODO: this feels like it should be in sdk...
def get_withdrawal_contract(pool_id: int) -> Contract:
    sdk: Geode = get_sdk()
    w3: Web3 = sdk.portal.w3
    network: Network = sdk.portal.network

    address = fetch_withdrawal_contract_address(pool_id)

    _, wp_abi = get_contract_abi(network=network, kind="package", name="WithdrawalPackage")
    contract: Contract = sdk.portal.w3.eth.contract(
        address=w3.to_checksum_address(address), abi=wp_abi
    )

    return contract


def get_fulfilled_ether_balance(pool_id: int, block_number: int) -> int:
    return int(
        get_withdrawal_contract(pool_id)
        .functions.QueueParams()
        .call(block_identifier=block_number)["fulfilledEtherBalance"]
    )


def get_pool_data(pool_id: int, block_number: int) -> dict:
    """Returns the data for a pool with the given id.

    Args:
        pool_id (int): id of the pool

    Returns:
        dict: dictionary containing the gathered pool info
    """
    sdk: Geode = get_sdk()

    # get data from portal
    surplus: int = sdk.portal.functions.readUint(pool_id, to_bytes32("surplus")).call(
        block_identifier=block_number
    )
    secured: int = sdk.portal.functions.readUint(pool_id, to_bytes32("secured")).call(
        block_identifier=block_number
    )

    # get data from withdrawal contract
    # TODO: What is this_?
    fulfilled_ether_balance: int = get_fulfilled_ether_balance(pool_id, block_number)

    # get data from gETH
    total_supply: int = sdk.gETH.totalSupply(pool_id).call(block_identifier=block_number)
    price: int = sdk.gETH.pricePerShare(pool_id).call(block_identifier=block_number)
    return {
        "id": str(pool_id),
        "surplus": str(surplus),
        "secured": str(secured),
        "fulfilled_ether_balance": str(fulfilled_ether_balance),
        "total_supply": str(total_supply),
        "price": str(price),
    }


def update_all_pools(block_number: int) -> None:
    """Updates all the pools with the given block number.

    Args:
        block_number (int): block number to update the pools
    """
    pool_ids: list[int] = get_all_pool_ids()  # from db
    pools: list[dict] = multithread(get_pool_data, pool_ids, repeat(block_number))
    update_many_pools_data(pools)


def update_portal_pools(block_number: int) -> None:
    """Updates the portal pools with the given block number.

    Args:
        block_number (int): block number to update the pools
    """
    update_pool_ids(block_number)
    update_all_pools(block_number)


def fetch_portal_state(pubkey: str, block_number: int) -> int:
    """Fetches the portal state of the given pubkey.

    Args:
        pubkey (str): public key of the validator
        block_number (int): block number to fetch the data from

    Returns:
        int: portal state of the pubkey
    """

    # [0] is the portal state
    return get_sdk().portal.functions.getValidator(pubkey).call(block_identifier=block_number)[0]


def fetch_batch_portal_state(pubkeys: list[str], block_number: int) -> list[int]:
    """Fetches the portal state of the given pubkeys.

    Args:
        pubkeys (list[str]): public keys of the validators
        block_number (int): block number to fetch the data from

    Returns:
        list[int]: portal state of the pubkeys
    """

    return multithread(fetch_portal_state, pubkeys, repeat(block_number))
