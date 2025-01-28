""" 
Helper functions for computing and managing pool and validator data in the Portal contract.
"""

from itertools import repeat

from eth_typing import HexStr
from geodefi.globals import DEPOSIT_SIZE  # BEACON_DENOMINATOR,
from geodefi.globals import ETHER_DENOMINATOR, PERCENTAGE_DENOMINATOR, VALIDATOR_STATE
from multiproof.standard import StandardMerkleTree

from src.common import BigInteger
from src.database.pools import read_latest_pool_data_batch
from src.globals import get_config, get_sdk
from src.globals.constants.config import (
    STRATEGY_MERKLE_REFRESH_RATE_FIELD,
    STRATEGY_PRICE_CHANGE_THRESHOLD_FIELD,
)
from src.helpers.portal import fetch_oracle_update_timestamp, fetch_portal_state
from src.helpers.validators import gather_validator_data_by_pool
from src.utils.notify import send_email
from src.utils.thread import multithread


def compute_effective_balance(
    val: tuple[
        str, BigInteger, BigInteger, BigInteger, BigInteger, BigInteger, BigInteger, int, int
    ],
    block_number: int,
) -> int:
    """
    Computes the effective balance of a validator.

    Formula:
        withdrawn_balance
        + fee_recipient_balance
        + beacon_balance
        + pending_balance
        - fees

    Args:
        val (tuple[Any, ...]): A tuple containing validator data:
            - pubkey
            - pool_fee
            - operator_fee
            - infrastructure_fee
            - withdrawn_balance
            - last_withdrawn
            - fee_recipient_balance
            - beacon_balance
            - beacon_status
        block_number (int): The block number for fetching portal state.

    Returns:
        int: The calculated effective balance or None if an error occurs.
    """
    (
        pubkey,
        pool_fee,
        operator_fee,
        infrastructure_fee,
        withdrawn_balance,
        last_withdrawn,
        fee_recipient_balance,
        beacon_balance,
        beacon_status,
    ) = val
    fees: int = 0
    pending: int = 0

    if beacon_status == "pending_initialized":
        # If it is not activated yet but active on portal:
        # it is proposed AND 31 eth has not yet showed up on beaconchain.
        # pending is 31 ETH.
        # Also, there are no possibility to withdraw any funds thus fees stay 0.
        if fetch_portal_state(pubkey, block_number) == VALIDATOR_STATE.ACTIVE:
            pending = DEPOSIT_SIZE.STAKE

    elif beacon_status == "withdrawal_done":
        # If exited, last_withdrawn is the remaining beacon_balance, included in withdrawn_balance
        # beacon_balance is not included in the fee calculation according to withdrawalPackage
        fees = (
            (withdrawn_balance - last_withdrawn)
            * (pool_fee + operator_fee + infrastructure_fee)
            // PERCENTAGE_DENOMINATOR
        )
    else:
        # In any other case, portal has sent 32 eth in total which shows up on beacon_balance.
        # Also, no pending.
        fees = (
            withdrawn_balance * (pool_fee + operator_fee + infrastructure_fee)
        ) // PERCENTAGE_DENOMINATOR

    #
    return int(withdrawn_balance + beacon_balance + fee_recipient_balance + pending - fees)


def compute_effective_balances_batch(
    validators: list[
        tuple[str, BigInteger, BigInteger, BigInteger, BigInteger, BigInteger, BigInteger, int, int]
    ],
    block_number: int,
) -> list[int]:
    """
    Computes effective balances for a batch of validators.

    Args:
        validators (list[tuple]): A list of validator data tuples.
        block_number (int): The block number for fetching portal state.

    Returns:
        list[int]: A list of effective balances.
    """
    return multithread(compute_effective_balance, validators, repeat(block_number))


def compute_price(
    pool: tuple[
        BigInteger,
        BigInteger,
        BigInteger,
        BigInteger,
        BigInteger,
        BigInteger,
    ],
    block_number: int,
    slot: int,
) -> tuple[
    BigInteger,  # pool_id
    int,  # new_price
    bool,  # price_increased
    list[  # validators
        tuple[str, BigInteger, BigInteger, BigInteger, BigInteger, BigInteger, BigInteger, int, int]
    ],
]:
    """
    Calculates the price of a pool.

    Args:
        pool (tuple): A tuple containing pool data:
            - pool_id (BigInteger)
            - current_price (BigInteger)
            - total_supply (BigInteger)
            - surplus (BigInteger)
            - secured (BigInteger)
            - fulfilled_ether_balance (BigInteger)
        block_number (int): The block number for data fetching.
        slot (int): The slot number associated with the pool.

    Returns:
        tuple: A tuple containing:
            - pool_id (BigInteger)
            - new_price (int)
            - price_increased (bool)
            - validators (list[tuple[str, BigInteger, BigInteger, BigInteger,
                BigInteger, BigInteger, BigInteger, int, int]])
    """
    pool_id, current_price, total_supply, surplus, secured, fulfilled_ether_balance = pool

    validators: list[
        tuple[str, BigInteger, BigInteger, BigInteger, BigInteger, BigInteger, BigInteger, int, int]
    ] = gather_validator_data_by_pool(pool_id, slot)

    total_validator_balances: int = sum(compute_effective_balances_batch(validators, block_number))

    total_balance: int = total_validator_balances + secured + surplus - fulfilled_ether_balance

    # this should be ok without floor division, but returns float then:
    new_price = total_balance * ETHER_DENOMINATOR // total_supply

    price_change_threshold = get_config(field=STRATEGY_PRICE_CHANGE_THRESHOLD_FIELD)

    return (
        pool_id,
        new_price,
        (new_price * 100)
        >= (current_price * (100 + price_change_threshold)),  # True if >%x(float) increase
        validators,
    )


def compute_prices_batch(
    pools: list[
        tuple[
            BigInteger,
            BigInteger,
            BigInteger,
            BigInteger,
            BigInteger,
            BigInteger,
        ]
    ],
    block_number: int,
    slot: int,
) -> list[
    tuple[
        BigInteger,  # pool_id
        int,  # new_price
        bool,  # price_increased
        list[  # validators
            tuple[
                str,
                BigInteger,
                BigInteger,
                BigInteger,
                BigInteger,
                BigInteger,
                BigInteger,
                int,
                int,
            ]
        ],
    ]
]:
    """
    Computes prices for a batch of pools.

    Args:
        pools (list[tuple]): A list of pool data tuples.
        block_number (int): The block number for data fetching.
        slot (int): The slot number associated with the pools.

    Returns:
        list[tuple]: A list of price data tuples or None for failed computations.
    """
    return multithread(compute_price, pools, repeat(block_number), repeat(slot))


def is_merkle_old(block_number: int) -> bool:
    """
    Determines if the merkle tree needs to be updated based on the last oracle update timestamp.

    Args:
        block_number (int): The block number to fetch the timestamp from.

    Returns:
        bool: True if the merkle tree is outdated, False otherwise.
    """
    last_update_ts: int = fetch_oracle_update_timestamp(block_number)

    current_ts: int = get_sdk().w3.eth.get_block(block_number).get("timestamp", 0)
    merkle_refresh_rate: int = get_config(field=STRATEGY_MERKLE_REFRESH_RATE_FIELD)
    return current_ts > (last_update_ts + merkle_refresh_rate)


def gather_merkle_data(pool_ids: list[BigInteger], block_number: int, slot: int) -> tuple[
    bool,
    list[
        tuple[
            BigInteger,
            int,
            bool,
            list[
                tuple[
                    str,
                    BigInteger,
                    BigInteger,
                    BigInteger,
                    BigInteger,
                    BigInteger,
                    BigInteger,
                    int,
                    int,
                ]
            ],
        ]
    ]
    | None,
]:
    """
    Checks the last update on merkle, if a configured! x(24h) amount has surpassed, update.
    Compares every pool for an increase of a configured! y(1) % change.
    Returns false otherwise.

    Args:
        pool_ids (list[BigInteger]): List of pool IDs to gather data for.
        block_number (int): The block number for data fetching.
        slot (int): The slot number associated with the pools.

    Returns:
        tuple[bool, list[tuple]]:
            - False and None if no update is needed.
            - True and prices_data tuple if an update is needed.
    """
    should_update: bool = is_merkle_old(block_number)

    pools: list[
        tuple[
            BigInteger,
            BigInteger,
            BigInteger,
            BigInteger,
            BigInteger,
            BigInteger,
        ]
    ] = read_latest_pool_data_batch(pool_ids)

    # Calculates the new price and then checks if there are any increase that exceeds 1%
    prices_data: list[
        tuple[
            BigInteger,  # pool_id
            int,  # new_price
            bool,  # price_increased
            list[  # validators
                tuple[
                    str,
                    BigInteger,
                    BigInteger,
                    BigInteger,
                    BigInteger,
                    BigInteger,
                    BigInteger,
                    int,
                    int,
                ]
            ],
        ]
    ] = compute_prices_batch(pools, block_number, slot)

    if not should_update:
        # Check if need an update according to prices_data[2] which represents
        # price_increased: price increased more than threshold for pool.
        should_update = any(obj[2] for obj in prices_data)

    if should_update:
        return (True, prices_data)

    return (False, None)


def prepare_report(
    prices: list[tuple[int, int]], balances: list[tuple[str, int, int]]
) -> tuple[HexStr, HexStr, int]:
    """
    Prepares the report for balances and prices merkle roots.

    Args:
        balances (list[tuple[int, int]]): Iterator of balance tuples.
        prices (list[tuple[str, int, int]]: Iterator of price tuples.

    Returns:
        tuple[str, str, int]: validator balances merkle tree root hash,
            pool derivative prices merkle tree root hash,
            and the total validator count on the beacon chain.
    """

    # ----- pool price related calculations -----
    # create merkle tree for pool prices
    # prices --> [(pool_id, new_price)...]
    price_merkle_tree: StandardMerkleTree = StandardMerkleTree.of(prices, ["uint256", "uint256"])

    # ----- validator balances related calculations -----
    # create merkle tree for validator balances
    # balances --> [(pubkey, balance, withdrawn_balance)...]
    # TODO:(crash) check if pubkeys is correct type here
    balance_merkle_tree: StandardMerkleTree = StandardMerkleTree.of(
        balances, ["bytes", "uint256", "uint256"]
    )

    # ----- all validators on chain related calculations -----

    # TODO:(later) find a way to do this later.
    # NOTE: for now we will send a fixed number.
    all_val_count = 1_000_000_000
    if all_val_count < 50_000:  # TODO:(later) This can be parametrized.
        send_email(
            subject="Unexpected Validator Count",
            body=f" Validator count on chain is under 50k: {all_val_count}"
            f" Will continue operations as usual, but an investigation is suggested.",
        )
        all_val_count = 50_000  # minimum count for the merkle tree

    return price_merkle_tree.root, balance_merkle_tree.root, all_val_count
