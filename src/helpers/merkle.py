# -*- coding: utf-8 -*-

import os
from itertools import repeat
from multiproof import StandardMerkleTree
from web3.exceptions import ContractLogicError

from geodefi.globals import (
    VALIDATOR_STATE,
    DEPOSIT_SIZE,
    PERCENTAGE_DENOMINATOR,
    # BEACON_DENOMINATOR,
    ETHER_DENOMINATOR,
)
from src.utils.thread import multithread
from src.globals import get_sdk, get_constants
from src.database.pools import fetch_latest_pool_data_batch


from src.helpers.validators import gather_validator_data_by_pool
from src.helpers.portal import fetch_portal_state, get_oracle_update_timestamp
from src.actions.multisig import get_gnosis_safe


def calc_effective_balance(val: tuple, block_number: int):
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


def calc_effective_balances_batch(validators: list[tuple], block_number: int):
    multithread(calc_effective_balance, validators, repeat(block_number))


def calc_price(pool: tuple, block_number: int, slot: int) -> tuple:
    """Calculates the price of a pool.

    Args:
        pool (tuple): _description_
        block_number (int): _description_
    """
    pool_id, current_price, total_supply, surplus, secured, fulfilled_ether_balance = pool

    validators: list[tuple] = gather_validator_data_by_pool(pool_id, slot)

    total_validator_balances: int = sum(calc_effective_balances_batch(validators, block_number))

    total_balance: int = (
        int(total_validator_balances) + int(secured) + int(surplus) - int(fulfilled_ether_balance)
    )

    new_price = total_balance * ETHER_DENOMINATOR / total_supply

    return (
        pool_id,
        new_price,
        # TODO: 1 here should be adjustable, somehow:
        (new_price * 100) >= (current_price * 100 + int(1)),  # %1 increase
        validators,
    )


def calc_prices_batch(pools: list[tuple], block_number: int, slot: int):
    return multithread(calc_price, pools, repeat(block_number), repeat(slot))


def get_merkle_refresh_rate() -> int:
    # if 24 hours has passed since the last update, should update the merkle tree
    # 24 hours in seconds
    # # TODO: dynamic param in config.strategy
    return int(86400)


def is_merkle_old(block_number: int) -> bool:
    last_update_ts: int = get_oracle_update_timestamp(block_number)

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
    pools: list[tuple] = fetch_latest_pool_data_batch(pool_ids)

    prices_data: list[tuple] = calc_prices_batch(pools, block_number, slot)

    if not should_update:
        should_update: bool = any(obj[1] for obj in prices_data)

    if should_update:
        return (True, prices_data)

    return (False, None)


def prepare_report(balances: list, prices: list) -> tuple[str, str, int]:
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
        # TODO: This should return 50k but send an email.
        all_val_count = 50_000  # minimum count for the merkle tree

    return (price_merkle_tree.root, balance_merkle_tree.root, all_val_count)


def report_beacon(
    price_merkle_root: str, balance_merkle_root: str, all_validators_count: int, block_number: int
) -> bool:
    """Reports the beacon.

    Args:
        price_merkle_root (str): The price merkle root.
        balance_merkle_root (str): The balance merkle root.
        all_validators_count (int): The all validators count.
        block_number (int): The block number to report the beacon for.
    """
    # TODO : this function does not belong here.

    ## oracle is the owner's address -> if no multisig -> call portal
    ## oracle is not owner's address -> if one address on multisig -> call multisig
    ##                               -> multiple addresses on multisig -> call watcher

    signer_address = get_constants().signer_address

    oracle_address = get_constants().oracle_address

    if signer_address == oracle_address:
        # # call portal
        # try:
        #     success, tx_receipt = send_tx(
        #         contract_address="0xcA69bA533810ee94b7649c57eF8aB22EBbE0bbf7",  # Portal contract address
        #         method_id="0xdf1ff929",  # reportBeacon function signature
        #         param_types=["bytes32", "bytes32", "uint256"],
        #         param_args=[price_merkle_root, balance_merkle_root, all_validators_count],
        #     )

        #     if success:
        #         get_logger().info(
        #             f"Successfully sent transaction: {dict(tx_receipt)['transactionHash'].hex()}"
        #         )
        #     else:
        #         # TODO: decide how to handle error
        #         get_logger().error(
        #             f"Failed to send transaction (reverted): {dict(tx_receipt)['transactionHash'].hex()}"
        #         )
        # except ContractLogicError as e:
        #     # TODO: decide how to handle exception
        #     get_logger().error(f"Contract logic error: {str(e)}")
        # except Exception as e:
        #     # TODO: decide how to handle exception
        #     get_logger().error(f"Error sending transaction: {str(e)}")
        return

    safe_owners: list = get_gnosis_safe(oracle_address).functions.getOwners().call()

    if len(safe_owners) == 1 and safe_owners[0] == signer_address:
        # TODO: call multisig directly, no watchers.
        pass
    elif len(safe_owners) > 1:
        # TODO: call watchers
        pass
    else:
        # TODO: raise if oracle_address is not in safe_owners
        raise Exception("Some error occurred. Please contact the Geodefi Team.")

    return True
    # if state is active and balance less than 16, it is a problem, raise error and exit (WHAT DOES THIS THING MEAN??)
