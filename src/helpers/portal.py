# -*- coding: utf-8 -*-

from typing import Any
from itertools import repeat
from geodefi.globals import ID_TYPE
from geodefi.utils import to_bytes32, get_key

from src.globals.sdk import SDK

# TODO: get operator_id from config
from src.globals.config import OPERATOR_ID
from src.utils.thread import multithread
from src.logger import log


# pylint: disable-next=invalid-name
def get_StakeParams() -> list[Any]:
    """Returns the result of portal.StakeParams function.

    Returns:
        list: list of StakeParams
    """
    log.debug("Calling StakeParams() from portal")
    return SDK.portal.functions.StakeParams().call()


# pylint: disable-next=invalid-name
def get_allIdsByType(type: ID_TYPE, index: int) -> int:
    """A helper function to call allIdsByType on Portal. Returns the ID of the given type and index.

    Args:
        type (ID_TYPE): type of the ID to be fetched.
        index (int): index of the ID to be fetched.

    Returns:
        int: ID of the given type and index.
    """

    log.debug("Calling allIdsByType() from portal")
    return SDK.portal.functions.allIdsByType(type, index).call()


# related to pools >


def get_name(pool_id: int) -> str:
    """Returns the name of the pool with given ID.

    Args:
        pool_id (int): ID of the pool to fetch name for.

    Returns:
        str: Name of the pool.
    """

    log.debug("Fetching the name of a pool: {pool_id}")
    return SDK.portal.functions.readBytes(pool_id, to_bytes32("NAME")).call()


def get_withdrawal_address(pool_id: int) -> str:
    """Returns the withdrawal address for given pool.

    Args:
        pool_id (int): ID of the pool to fetch withdrawal address for.

    Returns:
        str: Withdrawal address of the pool.
    """

    log.debug("Fetching the withdrawal address of a pool: {pool_id}")
    res = SDK.portal.functions.readAddress(
        pool_id, to_bytes32("withdrawalPackage")
    ).call()

    return res


def get_surplus(pool_id: int) -> int:
    """Returns the Ether amount that can be used to create validators for given pool, as wei.

    Args:
        pool_id (int): ID of the pool to fetch surplus for.

    Returns:
        int: Surplus of the pool in wei.
    """

    log.debug(f"Fetching the surplus of a pool: {pool_id}")
    return SDK.portal.functions.readUint(pool_id, to_bytes32("surplus")).call()


def get_fallback_operator(pool_id: int) -> int:
    """Returns the fallbackOperator for given pool.
    Fallback Operators can create validators without approval.

    Args:
        pool_id (int): ID of the pool to fetch fallback operator for.

    Returns:
        int: Fallback operator ID of the pool.
    """
    log.debug("Fetching the fallbackOperator of a pool: {pool_id}")
    return SDK.portal.functions.readUint(
        pool_id, to_bytes32("fallbackOperator")
    ).call()


def get_pools_count() -> int:
    """Returns the number of current pools from Portal

    Returns:
        int: Number of pools.
    """

    log.debug("Fetching the pools count of a pool: {pool_id}")
    return SDK.portal.functions.allIdsByTypeLength(ID_TYPE.POOL).call()


def get_all_pool_ids(start_index: int = 0) -> list[int]:
    """Returns the all current pool IDs from async Portal calls. It uses multithread to get all pool IDs.

    Args:
        start_index (int, optional): Index to start fetching pool IDs from. Default is 0.

    Returns:
        list[int]: list of pool IDs.
    """
    return multithread(
        get_allIdsByType,
        repeat(ID_TYPE.POOL),
        range(start_index, get_pools_count(), 1),
    )


# validators


def get_owned_pubkeys_count() -> int:
    """Returns the number of all validators that is owned by the operator.

    Returns:
        int: Number of validators owned by the operator.
    """
    log.debug(
        "Fetching the number of pools owned pubkeys from a validator: {pool_id}"
    )
    return SDK.portal.functions.readUint(
        OPERATOR_ID, to_bytes32("validators")
    ).call()


def get_owned_pubkey(index: int) -> str:
    """Returns the pubkey of given index for the operator's validator list.

    Args:
        index (int): index to look for pubkey in validators array

    Returns:
        str: Pubkey of the validator.
    """
    pk: str = SDK.portal.functions.readBytes(
        index, get_key(OPERATOR_ID, "validators")
    ).call()
    log.debug("Fetching an owned pubkey. index:{index} : pubkey:{pk}")
    return pk


def get_all_owned_pubkeys(start_index: int = 0) -> list[str]:
    """Returns all of the validator pubkeys that is owned by the operator.

    Args:
        start_index (int, optional): Index to start fetching pubkeys from. Default is 0.

    Returns:
        list[str]: list of validator pubkeys.
    """
    return multithread(
        get_owned_pubkey,
        range(start_index, get_owned_pubkeys_count(), 1),
    )


def get_operatorAllowance(pool_id: int) -> int:
    """Returns the result of portal.operatorAllowance function.

    Args:
        pool_id (int): ID of the pool to fetch operator allowance for.

    Returns:
        int: Operator allowance for the given pool.
    """
    return SDK.portal.functions.operatorAllowance(pool_id, OPERATOR_ID).call()
