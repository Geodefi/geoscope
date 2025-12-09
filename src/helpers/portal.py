"""
Module for interacting with the Portal contract, handling various blockchain ops.

Provides functionalities to fetch and process validator, pool, and portal state information.
& handlers for transactions related to the oracle and multisig operations.
"""

# pylint: disable=invalid-name

from functools import lru_cache
from itertools import repeat
from typing import Any, Iterable

from geodefi import Geode
from geodefi.globals import ID_TYPE, VALIDATOR_STATE, Network
from geodefi.utils import get_contract_abi, to_bytes32
from web3 import Web3
from web3.contract.contract import Contract, ContractEvent
from web3.types import BlockIdentifier, EventData

from src.common import BigInteger
from src.database.pools import (
    insert_pools_batch,
    read_pool_count,
    read_pool_ids,
    read_withdrawal_contract_address,
    update_pool_data_batch,
)
from src.globals import get_logger, get_sdk
from src.globals.constants.database import (
    POOLS_FULFILLED_ETHER_BALANCE_FIELD,
    POOLS_NAME_FIELD,
    POOLS_POOL_ID_FIELD,
    POOLS_PRICE_FIELD,
    POOLS_SECURED_FIELD,
    POOLS_SURPLUS_FIELD,
    POOLS_TOTAL_SUPPLY_FIELD,
    POOLS_WITHDRAWAL_CONTRACT_ADDRESS_FIELD,
    POOLS_WITHDRAWAL_CREDENTIALS_FIELD,
    VALIDATORS_INFRASTRUCTURE_FEE_FIELD,
    VALIDATORS_OPERATOR_FEE_FIELD,
    VALIDATORS_OPERATOR_ID_FIELD,
    VALIDATORS_POOL_FEE_FIELD,
    VALIDATORS_POOL_ID_FIELD,
    VALIDATORS_PORTAL_INDEX_FIELD,
    VALIDATORS_PUBKEY_FIELD,
    VALIDATORS_SIGNATURE31_FIELD,
)
from src.helpers.events import gather_all_events
from src.utils.thread import multithread


# TODO:(sdk) this feels like it should be in sdk
def __get_withdrawal_contract(pool_id: BigInteger) -> Contract:
    """
    Retrieves the WithdrawalContract instance for a given pool ID.

    Args:
        pool_id (BigInteger): The ID of the pool.

    Returns:
        Contract: The WithdrawalContract instance.

    Raises:
        Exception: If retrieval fails.
    """
    sdk: Geode = get_sdk()
    w3: Web3 = sdk.portal.w3
    network: Network = sdk.portal.network

    address = read_withdrawal_contract_address(BigInteger(pool_id))

    _, wp_abi = get_contract_abi(network=network, kind="package", name="WithdrawalPackage")
    contract: Contract = sdk.portal.w3.eth.contract(
        address=w3.to_checksum_address(address), abi=wp_abi
    )

    return contract


@lru_cache(maxsize=64)
def __call_StakeParams(block_identifier: BlockIdentifier) -> list[Any]:
    """
    Calls the StakeParams function of the Portal contract.

    Args:
        block_identifier (BlockIdentifier): The block identifier to call the data from.

    Returns:
        list[Any]: returns for the StakeParams function call:
            address gETH,
            address oraclePosition
            uint256 validatorsIndex
            uint256 verificationIndex
            uint256 monopolyThreshold
            uint256 beaconDelayEntry
            uint256 beaconDelayExit
            uint256 initiationDeposit
            uint256 oracleUpdateTimestamp
            uint256 dailyPriceIncreaseLimit
            uint256 dailyPriceDecreaseLimit

    Raises:
        Exception: If the call to StakeParams fails.
    """
    get_logger().debug("Calling 'StakeParams' from portal")
    return get_sdk().portal.functions.StakeParams().call(block_identifier=block_identifier)


def __call_QueueParams(pool_id: BigInteger, block_identifier: BlockIdentifier) -> list[Any]:
    """
    Calls the QueueParams function of the Portal contract.

    Args:
        block_identifier (BlockIdentifier): The block identifier to call the data from.

    Returns:
        list[Any]: returns for the QueueParams function call:
            uint256 requested
            uint256 realized
            uint256 realizedEtherBalance
            uint256 realizedPrice
            uint256 fulfilled
            uint256 fulfilledEtherBalance
            uint256 commonPoll

    Raises:
        Exception: If the call to QueueParams fails.
    """
    get_logger().debug("Calling QueueParams() from Withdrawal Contract")
    return (
        __get_withdrawal_contract(pool_id)
        .functions.QueueParams()
        .call(block_identifier=block_identifier)
    )


def fetch_verification_index(block_identifier: BlockIdentifier) -> int:
    """
    Fetches the verification index from the Portal contract.
    Verification Index points to the last validator that has been approved by the oracle already.

    Args:
        block_identifier (BlockIdentifier): block height to call the data from.\
            Can be head, latest, finalized etc as well.

    Returns:
        int: VERIFICATION_INDEX from portal.StakeParams

    Raises:
        Exception: If fetching the verification index fails.
    """
    return __call_StakeParams(block_identifier)[3]


def fetch_oracle_update_timestamp(block_identifier: BlockIdentifier) -> int:
    """
    Fetches the timestamp of the last oracle update from the Portal contract.

    Args:
        block_identifier (BlockIdentifier): block height to call the data from.\
            Can be head, latest, finalized etc as well.

    Returns:
        int: ORACLE_UPDATE_TIMESTAMP from portal.StakeParams
        
    Raises:
        Exception: If fetching the verification index fails.
    """
    return __call_StakeParams(block_identifier)[8]


@lru_cache(maxsize=64)
def fetch_oracle_address(block_identifier: BlockIdentifier) -> str:
    """
    Fetches the address of the oracle from the Portal contract.
    
    Args:
        block_identifier (BlockIdentifier): block height to call the data from.\
            Can be head, latest, finalized etc as well.

    Returns:
        str: ORACLE_ADDRESS from portal.StakeParams
    """
    return __call_StakeParams(block_identifier)[1]


def fetch_proposed_pubkeys(first_block: int, last_block: int) -> list[bytes]:
    """
    Retrieves the list of proposed pubkeys between given block range
    by checking the StakeProposal event from Portal.

    Args:
        first_block (int): first block to fetch proposed pubkeys
        last_block (int): last block to fetch proposed pubkeys

    Returns:
        list[bytes]: Gathered Pubkeys
    """
    # First we need to fetch all the ProposeValidator Events
    proposal_event: ContractEvent = get_sdk().portal.contract.events.StakeProposal()  # type:ignore

    detected_events: Iterable[EventData] = gather_all_events(
        event=proposal_event,
        first_block=first_block,
        last_block=last_block,
    )

    flattened_pks = [pubkey for event in detected_events for pubkey in event["args"]["pubkeys"]]
    get_logger().debug(f"Detected {len(flattened_pks)} pubkeys between {first_block}-{last_block}")

    return flattened_pks


def fetch_portal_validator_constants(pubkey: bytes) -> dict[str, str | int | BigInteger]:
    """
    Returns the portal data for a validator with the given pubkey.
    Only processes the Portal information;
    leaves the Beacon chain related ones empty to be processed later.
    Since the deposits might not be processed at the moment.
    Note that the Portal data gathered here, never changes,
    so it is safe to assume the latest is up to date.

    Args:
        pubkey (bytes): public key of the validator

    Returns:
        dict: Contains the gathered validator info :
            - VALIDATORS_PUBKEY_FIELD (str)
            - VALIDATORS_PORTAL_INDEX_FIELD (int)
            - VALIDATORS_POOL_ID_FIELD (BigInteger)
            - VALIDATORS_OPERATOR_ID_FIELD (BigInteger)
            - VALIDATORS_POOL_FEE_FIELD (BigInteger)
            - VALIDATORS_OPERATOR_FEE_FIELD (BigInteger)
            - VALIDATORS_INFRASTRUCTURE_FEE_FIELD (BigInteger)
            - VALIDATORS_SIGNATURE31_FIELD (str)
    """
    # Although all of the required data for the validators should be available,
    # the following ones might not yet since the deposit can be still not yet processed.
    # So, instead of not processing them, we will create the indexes
    # but fill them later when deposits are being processed.

    val = get_sdk().portal.validator(pubkey)
    return {
        VALIDATORS_PUBKEY_FIELD: val.pubkey,  # Converted to str
        VALIDATORS_PORTAL_INDEX_FIELD: val.portal_index,
        VALIDATORS_POOL_ID_FIELD: BigInteger(val.poolId),
        VALIDATORS_OPERATOR_ID_FIELD: BigInteger(val.operatorId),
        VALIDATORS_POOL_FEE_FIELD: BigInteger(val.poolFee),
        VALIDATORS_OPERATOR_FEE_FIELD: BigInteger(val.operatorFee),
        VALIDATORS_INFRASTRUCTURE_FEE_FIELD: BigInteger(val.infrastructureFee),
        VALIDATORS_SIGNATURE31_FIELD: "0x" + val.signature31.hex(),  # Converted to str
    }


def fetch_portal_validator_constants_batch(
    pks: list[bytes],
) -> list[dict[str, str | int | BigInteger]]:
    """Fetches the data for validators within the given pks list. Returns the gathered data.

    Args:
        pks (list[bytes]): pubkeys that will be fetched

    Returns:
        list[dict[str, Any]]: list of dictionaries containing the constant validator info
        gathered from the portal contract
    """

    return multithread(fetch_portal_validator_constants, pks)


def fetch_portal_state(pubkey: str, block_identifier: BlockIdentifier) -> VALIDATOR_STATE:
    """Fetches the portal state of the given pubkey.

    Args:
        pubkey (str): public key of the validator
        block_identifier (BlockIdentifier): block number to fetch the data from

    Returns:
        int: portal state of the pubkey
    """

    validator = (
        get_sdk().portal.functions.getValidator(pubkey).call(block_identifier=block_identifier)
    )

    # [0] is the portal state
    return VALIDATOR_STATE(validator[0])


# TODO:(crash) This function is not used, do we delete or keep it?
def fetch_portal_state_batch(pubkeys: list[str], block_identifier: BlockIdentifier) -> list[int]:
    """
    Fetches the portal state for a batch of pubkeys.

    Args:
        pubkeys (list[str]): public keys of the validators
        block_identifier (BlockIdentifier): block number to fetch the data from

    Returns:
        list[int]: portal state of the pubkeys
    """

    return multithread(fetch_portal_state, pubkeys, repeat(block_identifier))


def fetch_fulfilled_ether_balance(pool_id: BigInteger, block_identifier: BlockIdentifier) -> int:
    """
    Fetches the fulfilled ether balance (as wei) from the WithdrawalContract of a given pool.

    Args:
        pool_id (BigInteger): The ID of the pool.
        block_identifier (BlockIdentifier): The block number to fetch the data from.

    Returns:
        int: The fulfilled ether balance.
    """
    return __call_QueueParams(pool_id=pool_id, block_identifier=block_identifier)[5]


def gather_pool_info(
    pool_index: int, block_identifier: BlockIdentifier
) -> dict[str, BigInteger | str]:
    # TODO:(later) instead of using BlockIdentifier, we can set a constant one on web3.py!
    """
    Retrieves data for a pool with the given pool_index.

    Args:
        pool_index (int): The index of the pool on Portal contract.
        block_identifier (BlockIdentifier): The block number to call the data from.

    Returns:
        dict[str, Any]: A dictionary containing the pool information.
    """
    sdk: Geode = get_sdk()
    pool_id: BigInteger = BigInteger(
        sdk.portal.functions.allIdsByType(ID_TYPE.POOL, pool_index).call(
            block_identifier=block_identifier
        )
    )

    # no need to check for block_identifier, since these data never change.
    pool = sdk.portal.pool(pool_id)

    return {
        POOLS_POOL_ID_FIELD: pool_id,
        POOLS_NAME_FIELD: str(pool.NAME),
        POOLS_WITHDRAWAL_CONTRACT_ADDRESS_FIELD: str(
            get_sdk().portal.functions.readAddress(pool_id, to_bytes32("withdrawalPackage")).call()
        ),
        # TODO:(sdk) HOT FIXED! pool.withdrawalContract is wrong!!! fix it in the sdk.
        # This is unnaccesible as well : pool._read_address("withdrawalPackage")
        POOLS_WITHDRAWAL_CREDENTIALS_FIELD: str(pool.withdrawalCredential),
    }


def gather_pool_data(
    pool_id: BigInteger, block_identifier: BlockIdentifier
) -> dict[str, BigInteger]:
    """
    Retrieves data for a pool, including surplus & secured ETH amounts,
    and total_supply & price data from corresponding gETH token.

    Args:
        pool_id (BigInteger): The ID of the pool.
        block_identifier (BlockIdentifier): The block number to fetch the data from.

    Returns:
        dict[str, BigInteger]: A dictionary containing the pool data:
            id: (BigInteger)
            surplus: (BigInteger)
            secured: (BigInteger)
            fulfilled_ether_balance: (BigInteger)
            total_supply: (BigInteger)
            price: (BigInteger)
    """
    get_logger().debug("Gathering pool data from portal. ")
    sdk: Geode = get_sdk()

    # get data from portal
    surplus: int = sdk.portal.functions.readUint(pool_id, to_bytes32("surplus")).call(
        block_identifier=block_identifier
    )
    secured: int = sdk.portal.functions.readUint(pool_id, to_bytes32("secured")).call(
        block_identifier=block_identifier
    )

    # get data from withdrawal contract
    fulfilled_ether_balance: int = fetch_fulfilled_ether_balance(pool_id, block_identifier)

    # get data from gETH
    total_supply: int = sdk.token.functions.totalSupply(pool_id).call(
        block_identifier=block_identifier
    )
    price: int = sdk.token.functions.pricePerShare(pool_id).call(block_identifier=block_identifier)

    return {
        POOLS_POOL_ID_FIELD: pool_id,
        POOLS_PRICE_FIELD: BigInteger(price),
        POOLS_TOTAL_SUPPLY_FIELD: BigInteger(total_supply),
        POOLS_SURPLUS_FIELD: BigInteger(surplus),
        POOLS_SECURED_FIELD: BigInteger(secured),
        POOLS_FULFILLED_ETHER_BALANCE_FIELD: BigInteger(fulfilled_ether_balance),
    }


def update_pool_ids(block_identifier: BlockIdentifier) -> None:
    """
    Updates the pool IDs based on the state of the Portal contract on given block number.

    Args:
        block_identifier (BlockIdentifier): block number to update the pool ids
    """
    number_of_pools: int = read_pool_count()

    portal_pool_count: int = (
        get_sdk()
        .portal.functions.allIdsByTypeLength(ID_TYPE.POOL)
        .call(block_identifier=block_identifier)
    )

    if portal_pool_count > number_of_pools:
        get_logger().info(f"Updating pool ids from {number_of_pools} to {portal_pool_count}")
        pools: list[dict[str, BigInteger | str]] = multithread(
            gather_pool_info, range(number_of_pools, portal_pool_count), repeat(block_identifier)
        )
        insert_pools_batch(pools)


def fill_pools_table(block_identifier: BlockIdentifier) -> None:
    """
    Updates all pools in the database with the latest data.

    Args:
        block_identifier (BlockIdentifier): block number to update the pools
    """
    pool_ids: list[BigInteger] = read_pool_ids()  # from db
    pool_data: list[dict[str, BigInteger]] = multithread(
        gather_pool_data, pool_ids, repeat(block_identifier)
    )
    update_pool_data_batch(pool_data)


def update_portal_pools(block_identifier: BlockIdentifier) -> None:
    """
    Updates the portal pools, including pool IDs and pool data for new pools.

    Args:
        block_identifier (BlockIdentifier): block number to update the pools
    """
    update_pool_ids(block_identifier)
    fill_pools_table(block_identifier)
