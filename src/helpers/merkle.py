# -*- coding: utf-8 -*-

from itertools import repeat
from multiproof import StandardMerkleTree
from typing import Iterator

from geodefi.globals import (
    VALIDATOR_STATE,
    DEPOSIT_SIZE,
    PERCENTAGE_DENOMINATOR,
    # BEACON_DENOMINATOR,
    ETHER_DENOMINATOR,
)
from src.utils.thread import multithread
from src.globals import get_sdk, get_config
from src.database.pools import read_latest_pool_data_batch
from src.utils.notify import send_email
from src.helpers.validators import gather_validator_data_by_pool
from src.helpers.portal import fetch_portal_state, fetch_oracle_update_timestamp


def compute_effective_balance(val: tuple, block_number: int):
    """
        withdrawn_balance
        + fee_recipient_balance
        + beacon_balance
        + pending_balance
        - fees

    Args:
        val (tuple): _description_
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

    if beacon_status == "withdrawal_done":
        fees = (
            (withdrawn_balance - last_withdrawn)
            * (pool_fee + operator_fee + infrastructure_fee)
            / PERCENTAGE_DENOMINATOR
        )
    elif beacon_status == "pending_initialized":
        if fetch_portal_state(pubkey, block_number) == VALIDATOR_STATE.ACTIVE:
            pending = DEPOSIT_SIZE.STAKE
    else:
        fees = (
            withdrawn_balance * (pool_fee + operator_fee + infrastructure_fee)
        ) / PERCENTAGE_DENOMINATOR

    return (
        int(withdrawn_balance) + int(beacon_balance) + int(fee_recipient_balance) + pending - fees
    )


def compute_effective_balances_batch(validators: list[tuple], block_number: int):
    multithread(compute_effective_balance, validators, repeat(block_number))


def compute_price(pool: tuple, block_number: int, slot: int) -> tuple:
    """Calculates the price of a pool.

    Args:
        pool (tuple): _description_
        block_number (int): _description_
    """
    pool_id, current_price, total_supply, surplus, secured, fulfilled_ether_balance = pool

    validators: list[tuple] = gather_validator_data_by_pool(pool_id, slot)

    total_validator_balances: int = sum(compute_effective_balances_batch(validators, block_number))

    total_balance: int = (
        int(total_validator_balances) + int(secured) + int(surplus) - int(fulfilled_ether_balance)
    )

    new_price = total_balance * ETHER_DENOMINATOR / total_supply
    price_change_threshold = int(
        get_config().strategy.price_change_threshold
    )  # todo: do this convergion once! and check
    return (
        pool_id,
        new_price,
        (new_price * 100) >= (current_price * (100 + price_change_threshold)),  # %1 increase
        validators,
    )


def compute_prices_batch(pools: list[tuple], block_number: int, slot: int):
    return multithread(compute_price, pools, repeat(block_number), repeat(slot))


def get_merkle_refresh_rate() -> int:
    # if 24 hours has passed since the last update, should update the merkle tree
    # 24 hours in seconds
    merkle_refresh_rate = int(get_config().strategy.merkle_refresh_rate)
    return merkle_refresh_rate


def is_merkle_old(block_number: int) -> bool:
    last_update_ts: int = fetch_oracle_update_timestamp(block_number)

    current_ts: int = get_sdk().w3.eth.get_block(block_number).timestamp
    merkle_refresh_rate: int = get_merkle_refresh_rate()
    return current_ts > (last_update_ts + merkle_refresh_rate)


def gather_merkle_data(pool_ids: list[int], block_number: int, slot: int) -> tuple[bool, tuple]:
    """
    Checks the last update on merkle, if a configured! x(24h) amount has surpassed, update.
    Compares every pool for an increase of a configured! y(1) % change.
    Returns false otherwise.
    """
    should_update: bool = is_merkle_old(block_number)

    # Calculates the new price and then checks if there are any increase that exceeds 1%
    pools: list[tuple] = read_latest_pool_data_batch(pool_ids)

    prices_data: list[tuple] = compute_prices_batch(pools, block_number, slot)

    if not should_update:
        should_update: bool = any(obj[2] for obj in prices_data)

    if should_update:
        return (True, prices_data)

    return (False, None)


def prepare_report(balances: Iterator, prices: Iterator) -> tuple[str, str, int]:
    """Prepares the report for the balances and prices.

    Args:
        balances (list): The balances to prepare the report for.
        prices (list): The prices to prepare the report for.

    Returns:
        tuple: The report for the balances and prices.
    """

    # ----- pool price related calculations -----
    # create merkle tree for pool prices
    # prices --> [[pool_id, price]...]
    price_merkle_tree = StandardMerkleTree.of(prices, ["uint256", "uint256"])

    # ----- validator balances related calculations -----
    # create merkle tree for validator balances
    # balances --> [[pubkey, balance, withdrawn_balance]...]
    # TODO: check if pubkeys is str here, wants bytes instead.
    balance_merkle_tree = StandardMerkleTree.of(balances, ["bytes", "uint256", "uint256"])

    # ----- all validators on chain related calculations -----

    # NOTE: for now we will send a fixed number. TODO: find a way to do this later.
    all_val_count = 1_000_000_000
    if all_val_count < 50_000:  # This can be parametrized.
        send_email(
            "Unexpected Validator Count",
            f" Validator count on chain is under 50k: {all_val_count}",
            " Will continue operations as usual, but an investigation is suggested.",
        )
        all_val_count = 50_000  # minimum count for the merkle tree

    return (price_merkle_tree.root, balance_merkle_tree.root, all_val_count)
